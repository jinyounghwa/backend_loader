# SKILL.md — AWS Guardian SaaS

> 멀티테넌트 전환을 위한 핵심 구현 명세

---

## 1. Supabase DB 스키마

```sql
-- 사용자 (Supabase Auth 연동)
create table users (
  id            uuid primary key references auth.users,
  email         text unique not null,
  telegram_chat_id text,
  telegram_verified boolean default false,
  plan          text default 'free',  -- free | pro | team
  created_at    timestamptz default now()
);

-- AWS 연동 정보
create table aws_connections (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references users(id) on delete cascade,
  name          text not null,               -- 별칭 (예: "메인 계정")
  method        text not null,               -- 'role' | 'key'
  role_arn      text,                        -- Cross-Account Role ARN
  external_id   text,                        -- Confusion Deputy 방지
  access_key_enc text,                       -- AES 암호화된 Access Key
  secret_key_enc text,                       -- AES 암호화된 Secret Key
  aws_account_id text,                       -- 감지된 계정 ID
  is_active     boolean default true,
  last_verified timestamptz,
  created_at    timestamptz default now()
);

-- 감시 설정
create table watch_settings (
  id              uuid primary key default gen_random_uuid(),
  connection_id   uuid references aws_connections(id) on delete cascade,
  cost_enabled    boolean default true,
  cost_threshold  numeric default 10,        -- $/일
  ec2_enabled     boolean default true,
  ec2_auto_stop   boolean default false,     -- 자동 중지 여부
  allowed_regions text[] default array['ap-northeast-2'],
  s3_enabled      boolean default true,
  s3_auto_block   boolean default false,
  updated_at      timestamptz default now()
);

-- 이벤트 로그
create table guardian_events (
  id            uuid primary key default gen_random_uuid(),
  connection_id uuid references aws_connections(id),
  user_id       uuid references users(id),
  event_type    text not null,   -- COST_ALERT | EC2_ALERT | S3_ALERT | AUTO_STOP | AUTO_BLOCK
  severity      text default 'warning',  -- info | warning | critical
  message       text,
  data          jsonb,
  resolved      boolean default false,
  created_at    timestamptz default now()
);

-- RLS 정책
alter table aws_connections enable row level security;
alter table watch_settings enable row level security;
alter table guardian_events enable row level security;

create policy "본인 데이터만" on aws_connections
  for all using (auth.uid() = user_id);
create policy "본인 데이터만" on guardian_events
  for all using (auth.uid() = user_id);
```

---

## 2. NestJS API — AWS 연동 모듈

### connections/connections.service.ts

```typescript
import { Injectable, BadRequestException } from '@nestjs/common'
import { createClient } from '@supabase/supabase-js'
import { STSClient, AssumeRoleCommand, GetCallerIdentityCommand } from '@aws-sdk/client-sts'
import { STSClient as STS } from '@aws-sdk/client-sts'
import * as crypto from 'crypto'

@Injectable()
export class ConnectionsService {
  private readonly encKey = process.env.ENCRYPTION_KEY // 32바이트 AES-256

  // Cross-Account Role 연동 검증
  async verifyRoleArn(userId: string, roleArn: string): Promise<string> {
    const externalId = crypto.randomUUID()
    const sts = new STSClient({ region: 'ap-northeast-2' })

    try {
      const assumed = await sts.send(new AssumeRoleCommand({
        RoleArn: roleArn,
        RoleSessionName: `guardian-verify-${userId}`,
        ExternalId: externalId,
        DurationSeconds: 900,
      }))

      // 계정 ID 확인
      const tmpSts = new STSClient({
        region: 'ap-northeast-2',
        credentials: {
          accessKeyId: assumed.Credentials!.AccessKeyId!,
          secretAccessKey: assumed.Credentials!.SecretAccessKey!,
          sessionToken: assumed.Credentials!.SessionToken!,
        }
      })
      const identity = await tmpSts.send(new GetCallerIdentityCommand({}))
      return identity.Account! // 검증 성공 → 계정 ID 반환

    } catch (e) {
      throw new BadRequestException(`IAM Role 연동 실패: ${e.message}`)
    }
  }

  // Access Key 암호화 저장
  encrypt(plaintext: string): string {
    const iv = crypto.randomBytes(16)
    const cipher = crypto.createCipheriv('aes-256-cbc',
      Buffer.from(this.encKey, 'hex'), iv)
    const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()])
    return `${iv.toString('hex')}:${encrypted.toString('hex')}`
  }

  decrypt(ciphertext: string): string {
    const [ivHex, encHex] = ciphertext.split(':')
    const decipher = crypto.createDecipheriv('aes-256-cbc',
      Buffer.from(this.encKey, 'hex'), Buffer.from(ivHex, 'hex'))
    return Buffer.concat([
      decipher.update(Buffer.from(encHex, 'hex')),
      decipher.final()
    ]).toString()
  }

  // Access Key 방식 검증
  async verifyAccessKey(accessKey: string, secretKey: string): Promise<string> {
    const sts = new STSClient({
      region: 'ap-northeast-2',
      credentials: { accessKeyId: accessKey, secretAccessKey: secretKey }
    })
    try {
      const identity = await sts.send(new GetCallerIdentityCommand({}))
      return identity.Account!
    } catch (e) {
      throw new BadRequestException(`Access Key 검증 실패: ${e.message}`)
    }
  }
}
```

---

## 3. Telegram 온보딩 Bot

### telegram-bot/index.ts

```typescript
import TelegramBot from 'node-telegram-bot-api'
import { createClient } from '@supabase/supabase-js'
import crypto from 'crypto'

const bot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN!, { polling: true })
const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!)

// 임시 코드 저장 (Redis or Supabase)
const pendingCodes = new Map<string, { userId: string; expires: number }>()

// /connect 명령어 → 웹에서 호출
export async function generateConnectCode(userId: string): Promise<string> {
  const code = crypto.randomInt(100000, 999999).toString()
  pendingCodes.set(code, { userId, expires: Date.now() + 10 * 60 * 1000 }) // 10분 유효
  return code
}

bot.onText(/\/start (.+)/, async (msg, match) => {
  // 딥링크: t.me/BotName?start=CODE
  const code = match![1]
  const pending = pendingCodes.get(code)

  if (!pending || Date.now() > pending.expires) {
    bot.sendMessage(msg.chat.id, '❌ 코드가 만료되었거나 유효하지 않아요.\n웹에서 다시 시도해주세요.')
    return
  }

  // chat_id 저장
  await supabase.from('users').update({
    telegram_chat_id: msg.chat.id.toString(),
    telegram_verified: true
  }).eq('id', pending.userId)

  pendingCodes.delete(code)

  bot.sendMessage(msg.chat.id,
    `✅ *Telegram 연동 완료!*\n\n` +
    `이제 AWS 이상 감지 시 이 채팅으로 알림이 도착해요.\n` +
    `웹으로 돌아가서 AWS 계정 연동을 완료해주세요. 🛡️`,
    { parse_mode: 'Markdown' }
  )
})

bot.onText(/\/status/, async (msg) => {
  const { data: user } = await supabase
    .from('users')
    .select('*, aws_connections(*)')
    .eq('telegram_chat_id', msg.chat.id.toString())
    .single()

  if (!user) {
    bot.sendMessage(msg.chat.id, '먼저 웹에서 가입 후 연동해주세요.')
    return
  }

  const connections = user.aws_connections?.length ?? 0
  bot.sendMessage(msg.chat.id,
    `🛡️ *AWS Guardian 상태*\n\n연동된 계정: ${connections}개\n플랜: ${user.plan}`,
    { parse_mode: 'Markdown' }
  )
})
```

---

## 4. Lambda Dispatcher (멀티테넌트 핵심)

```python
# lambda/dispatcher/handler.py
import boto3, json, os
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
lambda_client = boto3.client("lambda")

def lambda_handler(event, context):
    # 활성 연동 전체 조회
    resp = supabase.table("aws_connections")\
        .select("*, users(telegram_chat_id, plan), watch_settings(*)")\
        .eq("is_active", True)\
        .execute()

    connections = resp.data
    print(f"[Dispatcher] 활성 연동 {len(connections)}개 처리 시작")

    results = []
    for conn in connections:
        try:
            # 사용자별 guardian Lambda 비동기 호출
            lambda_client.invoke(
                FunctionName=os.environ["GUARDIAN_FUNCTION_NAME"],
                InvocationType="Event",  # 비동기 (fire-and-forget)
                Payload=json.dumps({
                    "connection_id": conn["id"],
                    "user_id": conn["user_id"],
                    "method": conn["method"],
                    "role_arn": conn.get("role_arn"),
                    "external_id": conn.get("external_id"),
                    "access_key_enc": conn.get("access_key_enc"),
                    "secret_key_enc": conn.get("secret_key_enc"),
                    "telegram_chat_id": conn["users"]["telegram_chat_id"],
                    "settings": conn.get("watch_settings", [{}])[0]
                })
            )
            results.append({"connection_id": conn["id"], "status": "dispatched"})
        except Exception as e:
            print(f"[Dispatcher] 오류 {conn['id']}: {e}")
            results.append({"connection_id": conn["id"], "status": "error", "error": str(e)})

    return {"statusCode": 200, "dispatched": len(results)}
```

---

## 5. Guardian Lambda (멀티테넌트 대응)

```python
# lambda/guardian/handler.py
import boto3, json, os
from checkers.cost import CostChecker
from checkers.ec2 import EC2Checker
from checkers.s3 import S3Checker
from responders.telegram import TelegramNotifier
from storage.supabase_logger import SupabaseLogger
from utils.credentials import get_boto3_session

def lambda_handler(event, context):
    conn_id    = event["connection_id"]
    user_id    = event["user_id"]
    chat_id    = event["telegram_chat_id"]
    settings   = event.get("settings", {})

    # AWS 자격증명 획득 (Role or Key)
    try:
        session = get_boto3_session(event)
    except Exception as e:
        TelegramNotifier(chat_id).send(f"⚠️ AWS 연동 오류\n{str(e)}")
        return {"error": str(e)}

    telegram = TelegramNotifier(chat_id)
    logger   = SupabaseLogger(conn_id, user_id)
    alerts   = []

    if settings.get("cost_enabled", True):
        cost = CostChecker(session, settings.get("cost_threshold", 10))
        result = cost.check()
        if result["alert"]:
            telegram.send(cost.format_alert(result))
            logger.log("COST_ALERT", result)
            alerts.append(result)

    if settings.get("ec2_enabled", True):
        ec2 = EC2Checker(session,
                         settings.get("allowed_regions", ["ap-northeast-2"]),
                         auto_stop=settings.get("ec2_auto_stop", False))
        for issue in ec2.check():
            telegram.send(ec2.format_alert(issue))
            logger.log("EC2_ALERT", issue)
            alerts.append(issue)

    if settings.get("s3_enabled", True):
        s3 = S3Checker(session, auto_block=settings.get("s3_auto_block", False))
        for issue in s3.check():
            telegram.send(s3.format_alert(issue))
            logger.log("S3_ALERT", issue)
            alerts.append(issue)

    return {"connection_id": conn_id, "alerts": len(alerts)}
```

### utils/credentials.py

```python
import boto3, os, json, base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

ENC_KEY = bytes.fromhex(os.environ["ENCRYPTION_KEY"])

def decrypt(ciphertext: str) -> str:
    iv_hex, enc_hex = ciphertext.split(":")
    iv  = bytes.fromhex(iv_hex)
    enc = bytes.fromhex(enc_hex)
    cipher = Cipher(algorithms.AES(ENC_KEY), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(enc) + dec.finalize()
    pad_len = padded[-1]
    return padded[:-pad_len].decode()

def get_boto3_session(event: dict) -> boto3.Session:
    method = event["method"]

    if method == "role":
        sts = boto3.client("sts")
        assumed = sts.assume_role(
            RoleArn=event["role_arn"],
            RoleSessionName=f"guardian-{event['connection_id'][:8]}",
            ExternalId=event["external_id"],
            DurationSeconds=900
        )
        creds = assumed["Credentials"]
        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        )

    elif method == "key":
        return boto3.Session(
            aws_access_key_id=decrypt(event["access_key_enc"]),
            aws_secret_access_key=decrypt(event["secret_key_enc"])
        )

    raise ValueError(f"알 수 없는 연동 방식: {method}")
```

### storage/supabase_logger.py

```python
import os, requests
from datetime import datetime

class SupabaseLogger:
    def __init__(self, connection_id: str, user_id: str):
        self.conn_id = connection_id
        self.user_id = user_id
        self.url = os.environ["SUPABASE_URL"]
        self.key = os.environ["SUPABASE_SERVICE_KEY"]

    def log(self, event_type: str, data: dict):
        requests.post(
            f"{self.url}/rest/v1/guardian_events",
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"
            },
            json={
                "connection_id": self.conn_id,
                "user_id": self.user_id,
                "event_type": event_type,
                "message": data.get("message", ""),
                "data": data,
                "created_at": datetime.utcnow().isoformat()
            }
        )
```

---

## 6. Next.js 온보딩 — 5단계 위저드

```typescript
// app/onboarding/page.tsx
'use client'
import { useState } from 'react'
import StepTelegram from './steps/StepTelegram'
import StepAWSMethod from './steps/StepAWSMethod'
import StepAWSConnect from './steps/StepAWSConnect'
import StepSettings from './steps/StepSettings'
import StepVerify from './steps/StepVerify'

const STEPS = ['Telegram 연동', 'AWS 방식 선택', 'AWS 연결', '감시 설정', '검증']

export default function OnboardingPage() {
  const [step, setStep] = useState(0)
  const [data, setData] = useState<Record<string, any>>({})

  const next = (payload: Record<string, any>) => {
    setData(prev => ({ ...prev, ...payload }))
    setStep(prev => prev + 1)
  }

  return (
    <div className="max-w-lg mx-auto p-8">
      {/* 진행 바 */}
      <div className="flex gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className={`flex-1 h-2 rounded-full transition-all
            ${i <= step ? 'bg-amber-500' : 'bg-gray-200'}`} />
        ))}
      </div>

      <h2 className="text-xl font-bold mb-6">{STEPS[step]}</h2>

      {step === 0 && <StepTelegram onNext={next} />}
      {step === 1 && <StepAWSMethod onNext={next} />}
      {step === 2 && <StepAWSConnect method={data.method} onNext={next} />}
      {step === 3 && <StepSettings onNext={next} />}
      {step === 4 && <StepVerify data={data} />}
    </div>
  )
}
```

```typescript
// app/onboarding/steps/StepTelegram.tsx
'use client'
import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'

export default function StepTelegram({ onNext }: { onNext: (d: any) => void }) {
  const [code, setCode] = useState<string | null>(null)
  const [verified, setVerified] = useState(false)

  useEffect(() => {
    // 6자리 코드 발급
    fetch('/api/telegram/generate-code')
      .then(r => r.json())
      .then(d => setCode(d.code))
  }, [])

  useEffect(() => {
    if (!code) return
    // Supabase Realtime으로 telegram_verified 폴링
    const supabase = createClient()
    const channel = supabase.channel('telegram-verify')
      .on('postgres_changes', {
        event: 'UPDATE', schema: 'public', table: 'users'
      }, payload => {
        if (payload.new.telegram_verified) {
          setVerified(true)
          setTimeout(() => onNext({ telegram: true }), 1000)
        }
      })
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [code])

  const botName = process.env.NEXT_PUBLIC_TELEGRAM_BOT_NAME

  return (
    <div className="space-y-4">
      <p className="text-gray-600">Telegram 봇과 연동하면 이상 감지 시 즉시 알림을 받을 수 있어요.</p>

      {code && (
        <div className="bg-gray-50 rounded-xl p-6 text-center space-y-3">
          <p className="text-sm text-gray-500">아래 버튼을 눌러 봇을 열고</p>
          <a
            href={`https://t.me/${botName}?start=${code}`}
            target="_blank"
            className="inline-block bg-blue-500 text-white px-6 py-3 rounded-lg font-medium"
          >
            📱 Telegram 봇 열기
          </a>
          <p className="text-xs text-gray-400">봇에서 /start 를 보내면 자동 연동됩니다</p>
        </div>
      )}

      {verified && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center text-green-700">
          ✅ Telegram 연동 완료!
        </div>
      )}
    </div>
  )
}
```

---

## 7. Cross-Account IAM Policy (사용자 가이드용)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GuardianReadOnly",
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ec2:DescribeInstances",
        "ec2:DescribeRegions",
        "ec2:DescribeSecurityGroups",
        "s3:ListAllMyBuckets",
        "s3:GetBucketAcl",
        "s3:GetBucketPolicyStatus",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "GuardianAutoResponse",
      "Effect": "Allow",
      "Action": [
        "ec2:StopInstances",
        "s3:PutPublicAccessBlock"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["ap-northeast-2", "us-east-1"]
        }
      }
    }
  ]
}
```

**Trust Policy (사용자 계정에서 설정)**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::GUARDIAN_ACCOUNT_ID:root" },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": { "sts:ExternalId": "GUARDIAN_EXTERNAL_ID" }
    }
  }]
}
```

---

## 8. 환경변수 목록

```bash
# NestJS API
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ENCRYPTION_KEY=          # 64자 hex (32바이트 AES-256)
TELEGRAM_BOT_TOKEN=
NEXT_PUBLIC_TELEGRAM_BOT_NAME=

# Lambda (Dispatcher + Guardian)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ENCRYPTION_KEY=
TELEGRAM_BOT_TOKEN=
DISCORD_WEBHOOK_URL=
GUARDIAN_FUNCTION_NAME=aws-guardian-worker
GUARDIAN_ACCOUNT_ID=     # 서비스 운영 AWS 계정 ID

# 암호화 키 생성
openssl rand -hex 32
```

---

## 9. 배포 순서

```bash
# 1. Supabase 마이그레이션
supabase db push

# 2. Lambda 패키징
cd lambda/dispatcher && pip install -r requirements.txt -t . && zip -r ../dispatcher.zip .
cd lambda/guardian   && pip install -r requirements.txt -t . && zip -r ../guardian.zip .

# 3. Terraform
cd terraform && terraform init && terraform apply

# 4. NestJS API 배포 (Railway / EC2)
cd apps/api && npm run build && npm run start:prod

# 5. Next.js 배포
cd apps/web && vercel deploy

# 6. Telegram Bot 실행 (Railway or EC2)
cd telegram-bot && npm run start
```

---

## 10. 예상 인프라 비용 (100명 기준)

| 서비스 | 사용량 | 비용/월 |
|--------|--------|---------|
| Lambda Dispatcher | 720회 | 무료 |
| Lambda Guardian | 72,000회 × 10초 | ~$1.50 |
| Supabase | Free tier | $0 |
| Vercel | Hobby | $0 |
| NestJS API (Railway) | Starter | $5 |
| **합계** | | **~$6.50/월** |

> 1,000명 기준 Lambda ~$15, Railway $10 → 합계 ~$25/월
> Pro 플랜 $9 × 50명 = $450 수익 vs $25 인프라 비용
