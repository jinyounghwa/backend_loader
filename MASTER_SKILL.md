# AWS Guardian SaaS — 마스터 SKILL.md

> 구현에 필요한 모든 코드 명세를 하나로 통합.
> 세부 파일: SKILL_SECURITY.md (보안), SKILL_ORCHESTRA.md (개발환경)

---

## 목차

1. [DB 스키마 (Supabase)](#1-db-스키마)
2. [Lambda — 자격증명 / AWS 클라이언트](#2-lambda--자격증명--aws-클라이언트)
3. [Lambda — 감시 체커](#3-lambda--감시-체커)
4. [Lambda — 응답 / 로거](#4-lambda--응답--로거)
5. [Lambda — Dispatcher](#5-lambda--dispatcher)
6. [Lambda — Discord Webhook](#6-lambda--discord-webhook)
7. [NestJS — AWS 연동 모듈](#7-nestjs--aws-연동-모듈)
8. [NestJS — 보안 미들웨어](#8-nestjs--보안-미들웨어)
9. [Next.js — 온보딩 위저드](#9-nextjs--온보딩-위저드)
10. [Telegram Bot](#10-telegram-bot)
11. [Terraform](#11-terraform)
12. [LocalStack 환경](#12-localstack-환경)
13. [GLM 프록시](#13-glm-프록시)
14. [orchestra.sh](#14-orchestrash)
15. [테스트 스크립트](#15-테스트-스크립트)
16. [환경변수 / 배포](#16-환경변수--배포)

---

## 1. DB 스키마

```sql
-- supabase/migrations/001_init.sql

create table users (
  id               uuid primary key references auth.users,
  email            text unique not null,
  telegram_chat_id text,
  telegram_verified boolean default false,
  plan             text default 'free',
  created_at       timestamptz default now()
);

create table aws_connections (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references users(id) on delete cascade,
  name            text not null,
  method          text not null,          -- 'role' | 'key'
  role_arn        text,
  external_id     text,
  access_key_enc  text,
  secret_key_enc  text,
  aws_account_id  text,
  is_active       boolean default true,
  last_verified   timestamptz,
  created_at      timestamptz default now()
);

create table watch_settings (
  id              uuid primary key default gen_random_uuid(),
  connection_id   uuid references aws_connections(id) on delete cascade,
  cost_enabled    boolean default true,
  cost_threshold  numeric default 10,
  ec2_enabled     boolean default true,
  ec2_auto_stop   boolean default false,
  allowed_regions text[] default array['ap-northeast-2'],
  s3_enabled      boolean default true,
  s3_auto_block   boolean default false,
  updated_at      timestamptz default now()
);

create table guardian_events (
  id            uuid primary key default gen_random_uuid(),
  connection_id uuid references aws_connections(id),
  user_id       uuid references users(id),
  event_type    text not null,
  severity      text default 'warning',
  message       text,
  data          jsonb,
  resolved      boolean default false,
  created_at    timestamptz default now()
);

create table audit_logs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references users(id),
  action      text not null,
  ip_address  text,
  user_agent  text,
  before_data jsonb,
  after_data  jsonb,
  created_at  timestamptz default now()
);

-- RLS
alter table aws_connections enable row level security;
alter table watch_settings   enable row level security;
alter table guardian_events  enable row level security;

create policy "own" on aws_connections
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own_read" on guardian_events
  for select using (auth.uid() = user_id);
create policy "service_insert" on guardian_events
  for insert with check (auth.role() = 'service_role');

create policy "via_connection" on watch_settings
  for all using (
    exists (
      select 1 from aws_connections
      where id = watch_settings.connection_id and user_id = auth.uid()
    )
  );

create policy "audit_insert" on audit_logs for insert with check (true);
```

---

## 2. Lambda — 자격증명 / AWS 클라이언트

```python
# lambda/guardian/utils/aws_client.py
import os, boto3
from botocore.config import Config

ENDPOINT = os.environ.get("AWS_ENDPOINT_URL")  # LocalStack 자동 전환

def get_client(service: str, region: str = "ap-northeast-2", **kwargs):
    config = Config(retries={"max_attempts": 3, "mode": "standard"})
    return boto3.client(
        service, region_name=region,
        endpoint_url=ENDPOINT, config=config, **kwargs
    )

def get_session_client(session: boto3.Session, service: str,
                       region: str = "ap-northeast-2"):
    return session.client(service, region_name=region, endpoint_url=ENDPOINT)
```

```python
# lambda/guardian/utils/credentials.py
import os, boto3
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from utils.aws_client import get_client

ENC_KEY = bytes.fromhex(os.environ["ENCRYPTION_KEY"])

def _decrypt(ciphertext: str) -> str:
    iv_hex, enc_hex = ciphertext.split(":")
    iv, enc = bytes.fromhex(iv_hex), bytes.fromhex(enc_hex)
    cipher = Cipher(algorithms.AES(ENC_KEY), modes.CBC(iv),
                    backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(enc) + dec.finalize()
    return padded[:-padded[-1]].decode()

def get_boto3_session(event: dict) -> boto3.Session:
    method = event["method"]
    if method == "role":
        sts = get_client("sts")
        assumed = sts.assume_role(
            RoleArn=event["role_arn"],
            RoleSessionName=f"guardian-{event['connection_id'][:8]}",
            ExternalId=event["external_id"],
            DurationSeconds=900
        )
        c = assumed["Credentials"]
        return boto3.Session(
            aws_access_key_id=c["AccessKeyId"],
            aws_secret_access_key=c["SecretAccessKey"],
            aws_session_token=c["SessionToken"]
        )
    elif method == "key":
        return boto3.Session(
            aws_access_key_id=_decrypt(event["access_key_enc"]),
            aws_secret_access_key=_decrypt(event["secret_key_enc"])
        )
    raise ValueError(f"Unknown method: {method}")
```

```python
# lambda/guardian/utils/security.py
import re

VALID_REGIONS = {
    'ap-northeast-2','ap-northeast-1','ap-southeast-1',
    'us-east-1','us-east-2','us-west-2','eu-west-1','eu-central-1'
}

def validate_regions(regions: list) -> list:
    return [r for r in regions if r in VALID_REGIONS]

def validate_instance_id(v: str) -> bool:
    return bool(re.match(r'^i-[0-9a-f]{8,17}$', v))

def validate_bucket_name(v: str) -> bool:
    return bool(re.match(r'^[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9]$', v))
```

---

## 3. Lambda — 감시 체커

```python
# lambda/guardian/checkers/cost.py
import os
from datetime import datetime, timedelta
from utils.aws_client import get_client

class CostChecker:
    def __init__(self, session, threshold: float = 10.0):
        # CE API는 LocalStack 미지원 → 환경변수로 Mock 엔드포인트 분기
        ce_endpoint = os.environ.get("CE_MOCK_ENDPOINT")
        self.client = session.client(
            "ce", region_name="us-east-1",
            **({"endpoint_url": ce_endpoint} if ce_endpoint else {})
        )
        self.threshold = threshold

    def check(self) -> dict:
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        resp = self.client.get_cost_and_usage(
            TimePeriod={"Start": str(yesterday), "End": str(today)},
            Granularity="DAILY", Metrics=["UnblendedCost"]
        )
        amount = float(
            resp["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"]
        )
        return {
            "type": "cost", "amount": amount,
            "threshold": self.threshold,
            "alert": amount >= self.threshold,
            "date": str(yesterday),
            "message": f"일일 비용 ${amount:.2f} / 임계값 ${self.threshold:.2f}"
        }

    def format_alert(self, r: dict) -> str:
        return (
            f"🚨 *AWS 비용 경보*\n"
            f"📅 {r['date']}\n"
            f"💰 ${r['amount']:.2f} / 임계값 ${r['threshold']:.2f}\n"
            f"초과액: ${r['amount'] - r['threshold']:.2f}"
        )
```

```python
# lambda/guardian/checkers/ec2.py
from utils.aws_client import get_session_client
from utils.security import validate_regions, validate_instance_id

DANGEROUS_PORTS = [22, 3389, 3306, 5432]

class EC2Checker:
    def __init__(self, session, allowed_regions: list, auto_stop: bool = False):
        self.session = session
        self.allowed = set(validate_regions(allowed_regions))
        self.auto_stop = auto_stop
        self.issues = []

    def check(self) -> list:
        for region in self._all_regions():
            ec2 = get_session_client(self.session, "ec2", region)
            self._check_instances(ec2, region)
            self._check_security_groups(ec2, region)
        return self.issues

    def _check_instances(self, ec2, region):
        resp = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        for r in resp["Reservations"]:
            for inst in r["Instances"]:
                if region not in self.allowed:
                    self.issues.append({
                        "type": "ec2_unknown_region",
                        "instance_id": inst["InstanceId"],
                        "region": region,
                        "auto_stop": self.auto_stop,
                        "message": f"비인가 리전({region}) EC2 실행: {inst['InstanceId']}"
                    })

    def _check_security_groups(self, ec2, region):
        for sg in ec2.describe_security_groups()["SecurityGroups"]:
            for perm in sg.get("IpPermissions", []):
                for ip in perm.get("IpRanges", []):
                    if ip.get("CidrIp") == "0.0.0.0/0":
                        port = perm.get("FromPort", 0)
                        if port in DANGEROUS_PORTS:
                            self.issues.append({
                                "type": "ec2_open_port",
                                "sg_id": sg["GroupId"],
                                "port": port, "region": region,
                                "auto_stop": False,
                                "message": f"위험 포트 {port} 전체 오픈 ({sg['GroupId']})"
                            })

    def stop_instance(self, instance_id: str, region: str):
        if not validate_instance_id(instance_id):
            raise ValueError(f"Invalid instance_id: {instance_id}")
        ec2 = get_session_client(self.session, "ec2", region)
        ec2.stop_instances(InstanceIds=[instance_id])

    def format_alert(self, issue: dict) -> str:
        emoji = "🛑" if issue["auto_stop"] else "⚠️"
        action = "자동 중지 실행" if issue["auto_stop"] else "수동 확인 필요"
        return (
            f"{emoji} *EC2 보안 경보*\n"
            f"리전: {issue.get('region')}\n"
            f"내용: {issue['message']}\n조치: {action}"
        )

    def _all_regions(self) -> list:
        ec2 = get_session_client(self.session, "ec2", "us-east-1")
        return [r["RegionName"] for r in
                ec2.describe_regions(
                    Filters=[{"Name": "opt-in-status",
                              "Values": ["opt-in-not-required","opted-in"]}]
                )["Regions"]]
```

```python
# lambda/guardian/checkers/s3.py
from utils.aws_client import get_session_client
from utils.security import validate_bucket_name

PUBLIC_URIS = [
    "http://acs.amazonaws.com/groups/global/AllUsers",
    "http://acs.amazonaws.com/groups/global/AuthenticatedUsers"
]

class S3Checker:
    def __init__(self, session, auto_block: bool = False):
        self.s3 = get_session_client(session, "s3")
        self.auto_block = auto_block
        self.issues = []

    def check(self) -> list:
        for b in self.s3.list_buckets()["Buckets"]:
            if self._is_public(b["Name"]):
                self.issues.append({
                    "type": "s3_public_bucket",
                    "bucket_name": b["Name"],
                    "auto_block": self.auto_block,
                    "message": f"퍼블릭 버킷 감지: {b['Name']}"
                })
        return self.issues

    def _is_public(self, name: str) -> bool:
        try:
            if self.s3.get_bucket_policy_status(
                    Bucket=name)["PolicyStatus"]["IsPublic"]:
                return True
        except: pass
        try:
            acl = self.s3.get_bucket_acl(Bucket=name)
            for g in acl["Grants"]:
                if g.get("Grantee", {}).get("URI") in PUBLIC_URIS:
                    return True
        except: pass
        return False

    def block_public(self, name: str):
        if not validate_bucket_name(name):
            raise ValueError(f"Invalid bucket name: {name}")
        self.s3.put_public_access_block(
            Bucket=name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True,
                "BlockPublicPolicy": True, "RestrictPublicBuckets": True
            }
        )

    def format_alert(self, issue: dict) -> str:
        action = "퍼블릭 액세스 자동 차단 완료" if issue["auto_block"] else "수동 확인 필요"
        return f"🪣 *S3 보안 경보*\n버킷: {issue['bucket_name']}\n조치: {action}"
```

---

## 4. Lambda — 응답 / 로거

```python
# lambda/guardian/responders/telegram.py
import os, json, urllib.request

class TelegramNotifier:
    def __init__(self, chat_id: str):
        self.token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.chat_id = chat_id

    def send(self, message: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = json.dumps({
            "chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(url, data=data,
              headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
```

```python
# lambda/guardian/storage/supabase_logger.py
import os, json, urllib.request
from datetime import datetime

class SupabaseLogger:
    def __init__(self, connection_id: str, user_id: str):
        self.conn_id = connection_id
        self.user_id = user_id
        self.url = os.environ["SUPABASE_URL"]
        self.key = os.environ["SUPABASE_SERVICE_KEY"]

    def log(self, event_type: str, data: dict):
        payload = json.dumps({
            "connection_id": self.conn_id, "user_id": self.user_id,
            "event_type": event_type, "message": data.get("message", ""),
            "data": data, "created_at": datetime.utcnow().isoformat()
        }).encode()
        req = urllib.request.Request(
            f"{self.url}/rest/v1/guardian_events",
            data=payload,
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"
            }
        )
        urllib.request.urlopen(req, timeout=10)
```

```python
# lambda/guardian/handler.py
import json
from checkers.cost import CostChecker
from checkers.ec2 import EC2Checker
from checkers.s3 import S3Checker
from responders.telegram import TelegramNotifier
from storage.supabase_logger import SupabaseLogger
from utils.credentials import get_boto3_session

def lambda_handler(event, context):
    chat_id  = event["telegram_chat_id"]
    settings = event.get("settings", {})
    telegram = TelegramNotifier(chat_id)
    logger   = SupabaseLogger(event["connection_id"], event["user_id"])
    alerts   = []

    try:
        session = get_boto3_session(event)
    except Exception as e:
        telegram.send(f"⚠️ AWS 연동 오류\n{e}")
        return {"error": str(e)}

    if settings.get("cost_enabled", True):
        cost = CostChecker(session, settings.get("cost_threshold", 10))
        r = cost.check()
        if r["alert"]:
            telegram.send(cost.format_alert(r))
            logger.log("COST_ALERT", r)
            alerts.append(r)

    if settings.get("ec2_enabled", True):
        ec2 = EC2Checker(session,
                         settings.get("allowed_regions", ["ap-northeast-2"]),
                         auto_stop=settings.get("ec2_auto_stop", False))
        for issue in ec2.check():
            telegram.send(ec2.format_alert(issue))
            if issue["auto_stop"]:
                ec2.stop_instance(issue["instance_id"], issue["region"])
                logger.log("AUTO_STOP", issue)
            else:
                logger.log("EC2_ALERT", issue)
            alerts.append(issue)

    if settings.get("s3_enabled", True):
        s3 = S3Checker(session, auto_block=settings.get("s3_auto_block", False))
        for issue in s3.check():
            telegram.send(s3.format_alert(issue))
            if issue["auto_block"]:
                s3.block_public(issue["bucket_name"])
                logger.log("AUTO_BLOCK", issue)
            else:
                logger.log("S3_ALERT", issue)
            alerts.append(issue)

    return {"connection_id": event["connection_id"], "alerts": len(alerts)}
```

---

## 5. Lambda — Dispatcher

```python
# lambda/dispatcher/handler.py
import boto3, json, os
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"],
                         os.environ["SUPABASE_SERVICE_KEY"])
lambda_client = boto3.client(
    "lambda",
    endpoint_url=os.environ.get("AWS_ENDPOINT_URL")
)

def lambda_handler(event, context):
    resp = supabase.table("aws_connections")\
        .select("*, users(telegram_chat_id), watch_settings(*)")\
        .eq("is_active", True).execute()

    results = []
    for conn in resp.data:
        try:
            lambda_client.invoke(
                FunctionName=os.environ["GUARDIAN_FUNCTION_NAME"],
                InvocationType="Event",
                Payload=json.dumps({
                    "connection_id": conn["id"],
                    "user_id":       conn["user_id"],
                    "method":        conn["method"],
                    "role_arn":      conn.get("role_arn"),
                    "external_id":   conn.get("external_id"),
                    "access_key_enc": conn.get("access_key_enc"),
                    "secret_key_enc": conn.get("secret_key_enc"),
                    "telegram_chat_id": conn["users"]["telegram_chat_id"],
                    "settings": (conn.get("watch_settings") or [{}])[0]
                })
            )
            results.append({"id": conn["id"], "status": "dispatched"})
        except Exception as e:
            results.append({"id": conn["id"], "status": "error", "error": str(e)})

    return {"dispatched": len(results)}
```

---

## 6. Lambda — Discord Webhook

```python
# lambda/discord_webhook/handler.py
import json, boto3, os
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]

def lambda_handler(event, context):
    sig = event["headers"].get("x-signature-ed25519", "")
    ts  = event["headers"].get("x-signature-timestamp", "")
    try:
        VerifyKey(bytes.fromhex(PUBLIC_KEY)).verify(
            f"{ts}{event['body']}".encode(), bytes.fromhex(sig)
        )
    except BadSignatureError:
        return {"statusCode": 401, "body": "Invalid signature"}

    body = json.loads(event["body"])
    if body["type"] == 1:
        return _resp({"type": 1})

    cmd  = body["data"]["name"]
    opts = {o["name"]: o["value"] for o in body["data"].get("options", [])}

    if cmd == "status":   return _status()
    if cmd == "stop":     return _stop(opts["instance_id"])
    if cmd == "budget":   return _budget(opts["amount"])
    return {"statusCode": 400}

def _resp(data):
    return {"statusCode": 200, "body": json.dumps(data)}

def _status():
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"],
                       os.environ["SUPABASE_SERVICE_KEY"])
    items = sb.table("guardian_events").select("*")\
        .order("created_at", desc=True).limit(5).execute().data
    lines = "\n".join(f"• [{i['event_type']}] {i.get('message','')}"
                      for i in items)
    return _resp({"type": 4, "data": {"content": lines or "✅ 이상 없음"}})

def _stop(instance_id: str):
    import re
    if not re.match(r'^i-[0-9a-f]{8,17}$', instance_id):
        return _resp({"type": 4, "data": {"content": "❌ 유효하지 않은 인스턴스 ID"}})
    boto3.client("ec2", region_name="ap-northeast-2").stop_instances(
        InstanceIds=[instance_id]
    )
    return _resp({"type": 4, "data": {"content": f"✅ `{instance_id}` 중지 완료"}})

def _budget(amount: float):
    boto3.client("ssm").put_parameter(
        Name="/guardian/cost_threshold", Value=str(amount),
        Type="String", Overwrite=True
    )
    return _resp({"type": 4, "data": {"content": f"✅ 임계값 ${amount}/일 설정"}})
```

---

## 7. NestJS — AWS 연동 모듈

```typescript
// apps/api/src/connections/connections.service.ts
import { Injectable, BadRequestException } from '@nestjs/common'
import { STSClient, AssumeRoleCommand, GetCallerIdentityCommand } from '@aws-sdk/client-sts'
import { KMSClient, EncryptCommand, DecryptCommand } from '@aws-sdk/client-kms'
import * as crypto from 'crypto'

@Injectable()
export class ConnectionsService {
  private sts = new STSClient({ region: 'ap-northeast-2' })
  private kms = new KMSClient({ region: 'ap-northeast-2' })
  private readonly keyId = process.env.KMS_KEY_ID!

  async verifyRoleArn(userId: string, roleArn: string) {
    const externalId = `guardian-${userId}-${crypto.randomUUID()}`
    try {
      const assumed = await this.sts.send(new AssumeRoleCommand({
        RoleArn: roleArn,
        RoleSessionName: `guardian-verify-${userId.slice(0,8)}`,
        ExternalId: externalId, DurationSeconds: 900,
      }))
      const tmpSts = new STSClient({
        region: 'ap-northeast-2',
        credentials: {
          accessKeyId:     assumed.Credentials!.AccessKeyId!,
          secretAccessKey: assumed.Credentials!.SecretAccessKey!,
          sessionToken:    assumed.Credentials!.SessionToken!,
        }
      })
      const id = await tmpSts.send(new GetCallerIdentityCommand({}))
      return { accountId: id.Account!, externalId }
    } catch (e: any) {
      throw new BadRequestException(`IAM Role 연동 실패: ${e.message}`)
    }
  }

  async kmsEncrypt(plain: string): Promise<string> {
    const { CiphertextBlob } = await this.kms.send(new EncryptCommand({
      KeyId: this.keyId, Plaintext: Buffer.from(plain),
      EncryptionContext: { service: 'aws-guardian' }
    }))
    return Buffer.from(CiphertextBlob!).toString('base64')
  }

  async kmsDecrypt(cipher: string): Promise<string> {
    const { Plaintext } = await this.kms.send(new DecryptCommand({
      CiphertextBlob: Buffer.from(cipher, 'base64'),
      EncryptionContext: { service: 'aws-guardian' }
    }))
    return Buffer.from(Plaintext!).toString('utf-8')
  }
}
```

```typescript
// apps/api/src/connections/dto/create-connection.dto.ts
import { IsString, IsEnum, IsOptional, Matches, MaxLength } from 'class-validator'
import { Transform } from 'class-transformer'

export class CreateConnectionDto {
  @IsString() @MaxLength(50)
  @Transform(({ value }) => value.trim())
  name: string

  @IsEnum(['role', 'key'])
  method: 'role' | 'key'

  @IsOptional()
  @Matches(/^arn:aws:iam::\d{12}:role\/[\w+=,.@\-/]{1,512}$/)
  roleArn?: string

  @IsOptional()
  @Matches(/^AKIA[0-9A-Z]{16}$/)
  accessKey?: string

  @IsOptional()
  @IsString() @MaxLength(60)
  secretKey?: string
}
```

---

## 8. NestJS — 보안 미들웨어

```typescript
// apps/api/src/lib/security/ssrf-guard.ts
import { BadRequestException } from '@nestjs/common'
import * as dns from 'dns/promises'
import * as net from 'net'

const BLOCKED = [
  ['10.0.0.0','10.255.255.255'], ['172.16.0.0','172.31.255.255'],
  ['192.168.0.0','192.168.255.255'], ['127.0.0.0','127.255.255.255'],
  ['169.254.0.0','169.254.255.255'],
]
const ip2long = (ip: string) =>
  ip.split('.').reduce((a, o) => (a << 8) + parseInt(o), 0) >>> 0

const isBlocked = (ip: string) => {
  if (!net.isIPv4(ip)) return ip === '::1' || /^f[cd]/i.test(ip)
  const l = ip2long(ip)
  return BLOCKED.some(([s, e]) => l >= ip2long(s) && l <= ip2long(e))
}

export function assertValidRoleArn(arn: string) {
  if (!/^arn:aws:iam::\d{12}:role\/[\w+=,.@\-/]{1,512}$/.test(arn))
    throw new BadRequestException('유효하지 않은 Role ARN')
}

export async function assertSafeWebhook(url: string) {
  const ALLOWED = ['discord.com','discordapp.com','hooks.slack.com','api.telegram.org']
  let p: URL
  try { p = new URL(url) } catch { throw new BadRequestException('유효하지 않은 URL') }
  if (!ALLOWED.some(h => p.hostname === h || p.hostname.endsWith(`.${h}`)))
    throw new BadRequestException('허용되지 않는 Webhook 호스트')
  const ips = [...await dns.resolve4(p.hostname).catch(() => []),
               ...await dns.resolve6(p.hostname).catch(() => [])]
  for (const ip of ips)
    if (isBlocked(ip)) throw new BadRequestException('내부 네트워크 접근 불가')
}
```

```typescript
// apps/api/src/guards/ownership.guard.ts
import { Injectable, CanActivate, ExecutionContext, ForbiddenException } from '@nestjs/common'
import { createClient } from '@supabase/supabase-js'

@Injectable()
export class OwnershipGuard implements CanActivate {
  private sb = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!)
  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const req = ctx.switchToHttp().getRequest()
    const { data } = await this.sb
      .from('aws_connections').select('user_id')
      .eq('id', req.params.id).single()
    if (!data || data.user_id !== req.user.id)
      throw new ForbiddenException('접근 권한 없음')
    return true
  }
}
```

```typescript
// apps/api/src/interceptors/credential-mask.interceptor.ts
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common'
import { Observable } from 'rxjs'
import { map } from 'rxjs/operators'

const SENSITIVE = ['access_key_enc','secret_key_enc','external_id',
                   'accessKey','secretKey','password','token']
const mask = (o: any): any =>
  typeof o !== 'object' || !o ? o :
  Object.fromEntries(Object.entries(o).map(([k, v]) =>
    [k, SENSITIVE.includes(k) ? '***' : mask(v)]))

@Injectable()
export class CredentialMaskInterceptor implements NestInterceptor {
  intercept(_: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(map(mask))
  }
}
```

---

## 9. Next.js — 온보딩 위저드

```typescript
// apps/web/app/onboarding/page.tsx
'use client'
import { useState } from 'react'
import StepTelegram  from './steps/StepTelegram'
import StepAWSMethod from './steps/StepAWSMethod'
import StepAWSConnect from './steps/StepAWSConnect'
import StepSettings  from './steps/StepSettings'
import StepVerify    from './steps/StepVerify'

const STEPS = ['Telegram 연동','AWS 방식 선택','AWS 연결','감시 설정','검증']

export default function OnboardingPage() {
  const [step, setStep] = useState(0)
  const [data, setData] = useState<Record<string, any>>({})
  const next = (payload: Record<string, any>) => {
    setData(p => ({ ...p, ...payload }))
    setStep(p => p + 1)
  }
  return (
    <div className="max-w-lg mx-auto p-8">
      <div className="flex gap-2 mb-8">
        {STEPS.map((_, i) => (
          <div key={i} className={`flex-1 h-2 rounded-full transition-all
            ${i <= step ? 'bg-amber-500' : 'bg-gray-200'}`} />
        ))}
      </div>
      <h2 className="text-xl font-semibold mb-6">{STEPS[step]}</h2>
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
// apps/web/app/onboarding/steps/StepTelegram.tsx
'use client'
import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'

export default function StepTelegram({ onNext }: { onNext: (d: any) => void }) {
  const [code, setCode]     = useState<string | null>(null)
  const [verified, setVerified] = useState(false)

  useEffect(() => {
    fetch('/api/telegram/generate-code')
      .then(r => r.json()).then(d => setCode(d.code))
  }, [])

  useEffect(() => {
    if (!code) return
    const sb = createClient()
    const ch = sb.channel('tg-verify')
      .on('postgres_changes',
          { event: 'UPDATE', schema: 'public', table: 'users' },
          p => { if (p.new.telegram_verified) { setVerified(true); setTimeout(() => onNext({ telegram: true }), 800) } })
      .subscribe()
    return () => { sb.removeChannel(ch) }
  }, [code])

  return (
    <div className="space-y-4">
      <p className="text-gray-600">Telegram 봇과 연동하면 이상 감지 시 즉시 알림을 받을 수 있어요.</p>
      {code && (
        <div className="bg-gray-50 rounded-xl p-6 text-center space-y-3">
          <a href={`https://t.me/${process.env.NEXT_PUBLIC_TELEGRAM_BOT_NAME}?start=${code}`}
             target="_blank"
             className="inline-block bg-blue-500 text-white px-6 py-3 rounded-lg font-medium">
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

## 10. Telegram Bot

```typescript
// telegram-bot/index.ts
import TelegramBot from 'node-telegram-bot-api'
import { createClient } from '@supabase/supabase-js'
import crypto from 'crypto'

const bot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN!, { polling: true })
const sb  = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!)
const pending = new Map<string, { userId: string; expires: number }>()

export async function generateConnectCode(userId: string): Promise<string> {
  const code = crypto.randomInt(100000, 999999).toString()
  pending.set(code, { userId, expires: Date.now() + 10 * 60 * 1000 })
  return code
}

bot.onText(/\/start (.+)/, async (msg, match) => {
  const p = pending.get(match![1])
  if (!p || Date.now() > p.expires) {
    bot.sendMessage(msg.chat.id, '❌ 코드가 만료되었습니다. 웹에서 다시 시도해주세요.')
    return
  }
  await sb.from('users').update({
    telegram_chat_id: msg.chat.id.toString(), telegram_verified: true
  }).eq('id', p.userId)
  pending.delete(match![1])
  bot.sendMessage(msg.chat.id,
    `✅ *Telegram 연동 완료!*\n\nAWS 이상 감지 시 이 채팅으로 알림이 도착해요. 🛡️`,
    { parse_mode: 'Markdown' })
})

bot.onText(/\/status/, async (msg) => {
  const { data } = await sb.from('users')
    .select('plan, aws_connections(id)')
    .eq('telegram_chat_id', msg.chat.id.toString()).single()
  if (!data) { bot.sendMessage(msg.chat.id, '먼저 웹에서 가입해주세요.'); return }
  bot.sendMessage(msg.chat.id,
    `🛡️ *AWS Guardian*\n연동 계정: ${data.aws_connections?.length ?? 0}개\n플랜: ${data.plan}`,
    { parse_mode: 'Markdown' })
})
```

---

## 11. Terraform

```hcl
# terraform/main.tf
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
provider "aws" { region = var.aws_region }

variable "aws_region"          { default = "ap-northeast-2" }
variable "telegram_bot_token"  {}
variable "discord_webhook_url" {}
variable "discord_public_key"  {}
variable "supabase_url"        {}
variable "supabase_service_key"{}
variable "encryption_key"      {}
```

```hcl
# terraform/lambda.tf
data "archive_file" "dispatcher" {
  type = "zip"; source_dir = "../lambda/dispatcher"; output_path = "dispatcher.zip"
}
data "archive_file" "guardian" {
  type = "zip"; source_dir = "../lambda/guardian"; output_path = "guardian.zip"
}

resource "aws_lambda_function" "dispatcher" {
  filename      = data.archive_file.dispatcher.output_path
  function_name = "aws-guardian-dispatcher"
  role          = aws_iam_role.guardian.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60; memory_size = 128
  environment {
    variables = {
      SUPABASE_URL          = var.supabase_url
      SUPABASE_SERVICE_KEY  = var.supabase_service_key
      GUARDIAN_FUNCTION_NAME = aws_lambda_function.guardian.function_name
    }
  }
}

resource "aws_lambda_function" "guardian" {
  filename      = data.archive_file.guardian.output_path
  function_name = "aws-guardian-worker"
  role          = aws_iam_role.guardian.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300; memory_size = 256
  environment {
    variables = {
      TELEGRAM_BOT_TOKEN   = var.telegram_bot_token
      DISCORD_WEBHOOK_URL  = var.discord_webhook_url
      SUPABASE_URL         = var.supabase_url
      SUPABASE_SERVICE_KEY = var.supabase_service_key
      ENCRYPTION_KEY       = var.encryption_key
    }
  }
}

resource "aws_lambda_function_url" "discord" {
  function_name      = aws_lambda_function.discord_webhook.function_name
  authorization_type = "NONE"
}
```

```hcl
# terraform/eventbridge.tf
resource "aws_cloudwatch_event_rule" "hourly" {
  name                = "guardian-hourly"
  schedule_expression = "rate(1 hour)"
}
resource "aws_cloudwatch_event_target" "dispatcher" {
  rule = aws_cloudwatch_event_rule.hourly.name
  arn  = aws_lambda_function.dispatcher.arn
}
resource "aws_lambda_permission" "eventbridge" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly.arn
}
```

```hcl
# terraform/iam.tf
resource "aws_iam_role" "guardian" {
  name = "guardian-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" },
                   Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy" "guardian" {
  role = aws_iam_role.guardian.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow",
        Action = ["ce:GetCostAndUsage","ec2:Describe*","ec2:StopInstances",
                  "s3:ListAllMyBuckets","s3:GetBucketAcl","s3:GetBucketPolicyStatus",
                  "s3:PutPublicAccessBlock","sts:AssumeRole","ssm:GetParameter",
                  "ssm:PutParameter","kms:Encrypt","kms:Decrypt","lambda:InvokeFunction"],
        Resource = "*" },
      { Effect = "Allow",
        Action = ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
        Resource = "arn:aws:logs:*:*:*" }
    ]
  })
}
```

---

## 12. LocalStack 환경

```yaml
# localstack/docker-compose.yml
version: "3.9"
services:
  localstack:
    image: localstack/localstack:3.5
    ports: ["4566:4566"]
    environment:
      - SERVICES=lambda,dynamodb,s3,ssm,sts,events,logs,kms,iam
      - LAMBDA_EXECUTOR=docker
      - AWS_DEFAULT_REGION=ap-northeast-2
      - PERSISTENCE=1
    volumes:
      - "./init:/etc/localstack/init/ready.d"
      - "/var/run/docker.sock:/var/run/docker.sock"
      - "localstack-data:/var/lib/localstack"

  ce-mock:
    image: node:20-alpine
    working_dir: /app
    volumes: ["./mocks:/app"]
    command: sh -c "npm install && node cost-explorer-mock.js"
    ports: ["4580:4580"]
    environment:
      - MOCK_COST_AMOUNT=8.50

volumes:
  localstack-data:
```

```bash
# localstack/init/01-setup.sh (핵심 요약)
awslocal dynamodb create-table --table-name guardian-events \
  --attribute-definitions AttributeName=event_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema AttributeName=event_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST --region ap-northeast-2

awslocal s3 mb s3://guardian-test-bucket
awslocal s3 mb s3://guardian-public-test
awslocal s3api put-bucket-acl --bucket guardian-public-test --acl public-read

awslocal kms create-alias --alias-name alias/guardian-key \
  --target-key-id $(awslocal kms create-key --query 'KeyMetadata.KeyId' --output text)

awslocal ssm put-parameter --name "/guardian/prod/cost_threshold" \
  --value "10" --type String
```

---

## 13. GLM 프록시

```python
# .ai-orchestra/glm-proxy.py
import os, httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()
GLM_BASE    = os.environ["GLM_API_BASE"]
GLM_KEY     = os.environ["GLM_API_KEY"]
AUTH_HEADER = os.environ.get("GLM_AUTH_HEADER", "Authorization")
AUTH_PREFIX = os.environ.get("GLM_AUTH_PREFIX", "Bearer")

@app.api_route("/v1/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def proxy(path: str, request: Request):
    body = await request.body()
    auth_val = f"{AUTH_PREFIX} {GLM_KEY}".strip() if AUTH_PREFIX else GLM_KEY
    headers = {"Content-Type": "application/json", AUTH_HEADER: auth_val}

    async def stream():
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream(request.method,
                                f"{GLM_BASE}/v1/{path}",
                                headers=headers, content=body) as r:
                async for chunk in r.aiter_bytes():
                    yield chunk

    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.request(request.method, f"{GLM_BASE}/v1/{path}",
                            headers=headers, content=body)
        if "text/event-stream" in r.headers.get("content-type",""):
            return StreamingResponse(stream(), media_type="text/event-stream",
                                     headers={"X-Accel-Buffering":"no"})
        return r

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
```

---

## 14. orchestra.sh

```bash
#!/usr/bin/env bash
# .ai-orchestra/orchestra.sh
set -e
PROJECT_ROOT="${1:-$(pwd)}"
SESSION="guardian-dev"
source "$PROJECT_ROOT/.env.glm"

# GLM 프록시 시작
mkdir -p "$PROJECT_ROOT/.ai-orchestra/logs"
python "$PROJECT_ROOT/.ai-orchestra/glm-proxy.py" \
  > "$PROJECT_ROOT/.ai-orchestra/logs/glm-proxy.log" 2>&1 &
GLM_PROXY_PID=$!
sleep 2
echo "✅ GLM 프록시 PID: $GLM_PROXY_PID"

tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" -x 220 -y 50
tmux split-window -v -p 60 -t "$SESSION:0"
tmux split-window -v -p 50 -t "$SESSION:0.1"
tmux split-window -h -p 50 -t "$SESSION:0.1"

for pane in 0 1 2 3; do
  tmux send-keys -t "$SESSION:0.$pane" "cd $PROJECT_ROOT" Enter
done

# pane 0: Claude Code (구독 CLI)
tmux send-keys -t "$SESSION:0.0" "claude" Enter

# pane 1: GLM (구독 API → 프록시 → aider)
tmux send-keys -t "$SESSION:0.1" \
  "aider --model openai/$GLM_MODEL \
    --openai-api-base http://127.0.0.1:8765 \
    --openai-api-key dummy \
    --read .ai-orchestra/prompts/glm.md \
    --watch-files --auto-commits \
    --commit-prompt 'feat: GLM implementation'" Enter

# pane 2: Gemini (구독 CLI)
tmux send-keys -t "$SESSION:0.2" "gemini" Enter

# pane 3: LocalStack
tmux send-keys -t "$SESSION:0.3" \
  "docker compose -f localstack/docker-compose.yml up" Enter

tmux select-pane -t "$SESSION:0.0" -T "🧠 Claude Code"
tmux select-pane -t "$SESSION:0.1" -T "⚡ GLM 5.1"
tmux select-pane -t "$SESSION:0.2" -T "📄 Gemini"
tmux select-pane -t "$SESSION:0.3" -T "🐳 LocalStack"

trap "kill $GLM_PROXY_PID 2>/dev/null" EXIT
tmux attach-session -t "$SESSION"
```

---

## 15. 테스트 스크립트

```bash
#!/usr/bin/env bash
# scripts/test-localstack.sh
source localstack/.env.localstack
echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 LocalStack E2E 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━"

echo "[1/4] Lambda 직접 호출..."
awslocal lambda invoke --function-name aws-guardian-worker \
  --payload '{}' --cli-binary-format raw-in-base64-out /tmp/r.json
cat /tmp/r.json | python3 -m json.tool

echo "[2/4] DynamoDB 이벤트 확인..."
awslocal dynamodb scan --table-name guardian-events | python3 -m json.tool

echo "[3/4] S3 퍼블릭 버킷 감지 테스트..."
awslocal s3api put-bucket-acl --bucket guardian-public-test --acl public-read
awslocal lambda invoke --function-name aws-guardian-worker \
  --payload '{"test_s3":true}' --cli-binary-format raw-in-base64-out /tmp/s3.json
cat /tmp/s3.json | python3 -m json.tool

echo "[4/4] STS AssumeRole 테스트..."
awslocal sts assume-role \
  --role-arn "arn:aws:iam::000000000000:role/guardian-test-role" \
  --role-session-name test --external-id test-external-id | python3 -m json.tool

echo "✅ 완료!"
```

---

## 16. 환경변수 / 배포

```bash
# 암호화 키 생성
openssl rand -hex 32

# .env.glm
GLM_API_BASE=https://your-glm-endpoint.com/v1
GLM_API_KEY=your-subscription-key
GLM_MODEL=glm-4-plus
GLM_AUTH_HEADER=Authorization
GLM_AUTH_PREFIX=Bearer

# 배포 순서
# 1. Supabase 마이그레이션
supabase db push

# 2. Lambda 패키징
cd lambda/dispatcher && pip install -r requirements.txt -t . && zip -r ../dispatcher.zip .
cd lambda/guardian   && pip install -r requirements.txt -t . && zip -r ../guardian.zip .

# 3. Terraform
cd terraform && terraform init && terraform apply

# 4. NestJS API (Railway)
cd apps/api && npm run build && railway up

# 5. Next.js (Vercel)
cd apps/web && vercel deploy

# 6. Telegram Bot (Railway)
cd telegram-bot && railway up
```

---

## requirements.txt

```
# lambda/guardian/requirements.txt
boto3>=1.34.0
supabase>=2.0.0
PyNaCl>=1.5.0
cryptography>=42.0.0
requests>=2.31.0

# lambda/dispatcher/requirements.txt
boto3>=1.34.0
supabase>=2.0.0

# .ai-orchestra/glm-proxy requirements
fastapi>=0.110.0
uvicorn>=0.29.0
httpx>=0.27.0
```
