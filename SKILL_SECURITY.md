# SKILL_SECURITY.md — AWS Guardian SaaS 보안 강화

> SSRF, Injection, 자격증명 탈취 등 SaaS 서비스 운영 시 반드시 대응해야 할 보안 항목 전체 명세

---

## 보안 위협 맵

```
[외부 공격자]
    │
    ├── SSRF              → Lambda/API가 내부 메타데이터 노출
    ├── Injection         → NoSQL/SQL Injection, Command Injection
    ├── 자격증명 탈취      → 암호화 키 유출, IAM 키 노출
    ├── 혼동된 대리인      → Cross-Account Role 오용
    ├── Rate Limit 우회   → API 남용, 비용 폭탄
    ├── IDOR              → 다른 사용자 데이터 접근
    ├── XSS / CSRF        → 웹 대시보드 공격
    ├── 공급망 공격        → 의존성 패키지 탈취
    └── 내부자 위협        → 서비스 키 유출
```

---

## 1. SSRF (Server-Side Request Forgery)

### 위협 시나리오
사용자가 Role ARN 대신 `http://169.254.169.254/latest/meta-data/` 같은 내부 URL을 입력해서
Lambda가 실행 중인 EC2/컨테이너의 IAM 자격증명을 탈취하는 공격.

### 대응 — NestJS API

```typescript
// lib/security/ssrf-guard.ts
import { BadRequestException } from '@nestjs/common'
import * as dns from 'dns/promises'
import * as net from 'net'

// 차단할 IP 대역 (RFC 1918 + 링크로컬 + 루프백)
const BLOCKED_RANGES = [
  { start: '10.0.0.0',     end: '10.255.255.255'  },
  { start: '172.16.0.0',   end: '172.31.255.255'  },
  { start: '192.168.0.0',  end: '192.168.255.255' },
  { start: '127.0.0.0',    end: '127.255.255.255' },
  { start: '169.254.0.0',  end: '169.254.255.255' }, // EC2 메타데이터
  { start: '0.0.0.0',      end: '0.255.255.255'   },
  { start: '::1',          end: '::1'              }, // IPv6 루프백
  { start: 'fc00::',       end: 'fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff' },
]

function ipToLong(ip: string): number {
  return ip.split('.').reduce((acc, oct) => (acc << 8) + parseInt(oct), 0) >>> 0
}

function isBlockedIp(ip: string): boolean {
  if (net.isIPv6(ip)) {
    // IPv6 내부 대역 간단 체크
    return ip === '::1' || ip.startsWith('fc') || ip.startsWith('fd')
  }
  const long = ipToLong(ip)
  return BLOCKED_RANGES.some(r => {
    if (!net.isIPv4(r.start)) return false
    return long >= ipToLong(r.start) && long <= ipToLong(r.end)
  })
}

export async function assertSafeUrl(input: string): Promise<void> {
  let parsed: URL
  try {
    parsed = new URL(input)
  } catch {
    throw new BadRequestException('유효하지 않은 URL 형식입니다')
  }

  // 허용 스킴만 통과 (http/https만)
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new BadRequestException('허용되지 않는 프로토콜입니다')
  }

  // DNS 해석 후 IP 검사 (DNS rebinding 대응)
  const addresses = await dns.resolve4(parsed.hostname).catch(() => [])
  const v6addresses = await dns.resolve6(parsed.hostname).catch(() => [])
  const allIps = [...addresses, ...v6addresses]

  if (allIps.length === 0) {
    throw new BadRequestException('도메인 해석에 실패했습니다')
  }

  for (const ip of allIps) {
    if (isBlockedIp(ip)) {
      throw new BadRequestException('내부 네트워크 접근은 허용되지 않습니다')
    }
  }
}

// Role ARN 형식 강제 검증 (SSRF 진입점 원천 차단)
export function assertValidRoleArn(arn: string): void {
  const ARN_PATTERN = /^arn:aws:iam::\d{12}:role\/[\w+=,.@\-/]{1,512}$/
  if (!ARN_PATTERN.test(arn)) {
    throw new BadRequestException('유효하지 않은 IAM Role ARN 형식입니다')
  }
}

// Webhook URL 검증 (Discord/Telegram webhook 등록 시)
export async function assertSafeWebhook(url: string): Promise<void> {
  const ALLOWED_WEBHOOK_HOSTS = [
    'discord.com', 'discordapp.com',
    'hooks.slack.com',
    'api.telegram.org'
  ]
  let parsed: URL
  try { parsed = new URL(url) } catch {
    throw new BadRequestException('유효하지 않은 Webhook URL입니다')
  }
  if (!ALLOWED_WEBHOOK_HOSTS.some(h => parsed.hostname === h || parsed.hostname.endsWith(`.${h}`))) {
    throw new BadRequestException('허용되지 않는 Webhook 호스트입니다')
  }
  await assertSafeUrl(url)
}
```

### 대응 — Lambda IMDSv2 강제

```python
# terraform/lambda.tf 에 추가
resource "aws_lambda_function" "guardian" {
  # ... 기존 설정 ...

  # IMDSv2 강제 (메타데이터 서비스 토큰 필수)
  # Lambda는 기본적으로 IMDS 접근 불가이나 VPC 내 배포 시 명시적 차단
}

# EC2에 Lambda 연결된 경우 IMDSv2 강제
resource "aws_instance" "bastion" {
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # IMDSv2 강제
    http_put_response_hop_limit = 1           # 컨테이너 탈취 방지
  }
}
```

---

## 2. IDOR (Insecure Direct Object Reference)

### 위협 시나리오
`GET /api/connections/OTHER_USER_UUID` 로 다른 사용자의 AWS 자격증명 조회.

### 대응 — NestJS Guard

```typescript
// guards/ownership.guard.ts
import { Injectable, CanActivate, ExecutionContext, ForbiddenException } from '@nestjs/common'
import { createClient } from '@supabase/supabase-js'

@Injectable()
export class OwnershipGuard implements CanActivate {
  private supabase = createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_KEY!
  )

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const req = context.switchToHttp().getRequest()
    const userId = req.user.id  // JWT에서 추출
    const resourceId = req.params.id

    const table = this.inferTable(req.path)
    const { data, error } = await this.supabase
      .from(table)
      .select('user_id')
      .eq('id', resourceId)
      .single()

    if (error || !data) throw new ForbiddenException('리소스를 찾을 수 없습니다')
    if (data.user_id !== userId) throw new ForbiddenException('접근 권한이 없습니다')

    return true
  }

  private inferTable(path: string): string {
    if (path.includes('connections')) return 'aws_connections'
    if (path.includes('events')) return 'guardian_events'
    if (path.includes('settings')) return 'watch_settings'
    throw new ForbiddenException('알 수 없는 리소스')
  }
}

// 사용 예시
@Get(':id')
@UseGuards(JwtAuthGuard, OwnershipGuard)
findOne(@Param('id') id: string) { ... }
```

### Supabase RLS (DB 레벨 2중 방어)

```sql
-- 모든 테이블에 RLS 적용 (이미 SKILL.md에 있으나 강화)

-- aws_connections: 본인 것만
create policy "connections_isolation" on aws_connections
  for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- guardian_events: 읽기만 허용, 쓰기는 service_role만
create policy "events_read_own" on guardian_events
  for select using (auth.uid() = user_id);

create policy "events_insert_service" on guardian_events
  for insert with check (auth.role() = 'service_role');

-- watch_settings: connection 소유자만
create policy "settings_via_connection" on watch_settings
  for all using (
    exists (
      select 1 from aws_connections
      where id = watch_settings.connection_id
      and user_id = auth.uid()
    )
  );
```

---

## 3. 자격증명 보안 강화

### AWS KMS 이중 암호화

```typescript
// lib/security/kms-crypto.ts
import { KMSClient, EncryptCommand, DecryptCommand } from '@aws-sdk/client-kms'

const kms = new KMSClient({ region: 'ap-northeast-2' })
const KEY_ID = process.env.KMS_KEY_ID!

export async function kmsEncrypt(plaintext: string): Promise<string> {
  const cmd = new EncryptCommand({
    KeyId: KEY_ID,
    Plaintext: Buffer.from(plaintext),
    EncryptionContext: { service: 'aws-guardian', version: '1' }
  })
  const { CiphertextBlob } = await kms.send(cmd)
  return Buffer.from(CiphertextBlob!).toString('base64')
}

export async function kmsDecrypt(ciphertext: string): Promise<string> {
  const cmd = new DecryptCommand({
    CiphertextBlob: Buffer.from(ciphertext, 'base64'),
    EncryptionContext: { service: 'aws-guardian', version: '1' }
  })
  const { Plaintext } = await kms.send(cmd)
  return Buffer.from(Plaintext!).toString('utf-8')
}

// Lambda에서 복호화 시
export async function getDecryptedCredential(encrypted: string): Promise<string> {
  // KMS 키 접근 권한이 있는 Lambda Role만 복호화 가능
  return kmsDecrypt(encrypted)
}
```

### 자격증명 마스킹 — 응답 필터

```typescript
// interceptors/credential-mask.interceptor.ts
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common'
import { Observable } from 'rxjs'
import { map } from 'rxjs/operators'

const SENSITIVE_FIELDS = [
  'access_key_enc', 'secret_key_enc', 'external_id',
  'accessKey', 'secretKey', 'password', 'token'
]

function maskObject(obj: any): any {
  if (typeof obj !== 'object' || obj === null) return obj
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => [
      k,
      SENSITIVE_FIELDS.includes(k) ? '***REDACTED***' : maskObject(v)
    ])
  )
}

@Injectable()
export class CredentialMaskInterceptor implements NestInterceptor {
  intercept(ctx: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(map(data => maskObject(data)))
  }
}
```

---

## 4. Rate Limiting & DDoS 방어

```typescript
// main.ts
import { NestFactory } from '@nestjs/core'
import { ThrottlerGuard } from '@nestjs/throttler'
import { APP_GUARD } from '@nestjs/core'
import helmet from 'helmet'
import * as compression from 'compression'

async function bootstrap() {
  const app = await NestFactory.create(AppModule)

  // 기본 보안 헤더
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", 'data:', 'https:'],
        connectSrc: ["'self'", process.env.SUPABASE_URL!],
      }
    },
    hsts: { maxAge: 31536000, includeSubDomains: true, preload: true }
  }))

  // CORS 엄격 설정
  app.enableCors({
    origin: [process.env.WEB_URL!, 'https://aws-guardian.io'],
    methods: ['GET', 'POST', 'PATCH', 'DELETE'],
    credentials: true,
  })

  await app.listen(3000)
}
```

```typescript
// app.module.ts — ThrottlerModule 설정
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler'

@Module({
  imports: [
    ThrottlerModule.forRoot([
      { name: 'global',  ttl: 60000, limit: 60   }, // 1분 60회
      { name: 'auth',    ttl: 60000, limit: 10   }, // 로그인 1분 10회
      { name: 'verify',  ttl: 60000, limit: 5    }, // AWS 연동 검증 1분 5회
    ]),
  ],
  providers: [{ provide: APP_GUARD, useClass: ThrottlerGuard }],
})

// 특정 엔드포인트 개별 설정
@Post('verify-role')
@Throttle({ verify: { ttl: 300000, limit: 3 } })  // 5분 3회
async verifyRole(@Body() dto: VerifyRoleDto) { ... }
```

---

## 5. Input Validation & Injection 방어

```typescript
// dto/connection.dto.ts
import { IsString, IsEnum, IsOptional, Matches, MaxLength, IsUUID } from 'class-validator'
import { Transform } from 'class-transformer'

export class CreateConnectionDto {
  @IsString()
  @MaxLength(50)
  @Transform(({ value }) => value.trim())
  name: string

  @IsEnum(['role', 'key'])
  method: 'role' | 'key'

  @IsOptional()
  @Matches(/^arn:aws:iam::\d{12}:role\/[\w+=,.@\-/]{1,512}$/, {
    message: '유효하지 않은 Role ARN 형식'
  })
  roleArn?: string

  @IsOptional()
  @Matches(/^AKIA[0-9A-Z]{16}$/, {
    message: '유효하지 않은 Access Key 형식'
  })
  accessKey?: string

  @IsOptional()
  @IsString()
  @MaxLength(60)  // Secret Key 최대 길이
  secretKey?: string
}

export class UpdateSettingsDto {
  @IsOptional()
  costThreshold?: number  // class-validator가 숫자 강제

  @IsOptional()
  @IsString({ each: true })
  @Matches(/^[a-z]{2}-[a-z]+-\d$/, { each: true, message: '유효하지 않은 AWS 리전' })
  allowedRegions?: string[]
}
```

```typescript
// main.ts — 전역 ValidationPipe
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,           // 정의되지 않은 필드 자동 제거
  forbidNonWhitelisted: true, // 미정의 필드 있으면 400 반환
  transform: true,
  disableErrorMessages: process.env.NODE_ENV === 'production', // prod에서 상세 오류 숨김
}))
```

---

## 6. Confused Deputy (혼동된 대리인) 방어

```typescript
// connections/connections.service.ts 강화
import { assertValidRoleArn } from '../lib/security/ssrf-guard'

async createRoleConnection(userId: string, dto: CreateConnectionDto) {
  // 1. ARN 형식 검증
  assertValidRoleArn(dto.roleArn!)

  // 2. ExternalId 서버에서 생성 (클라이언트 제공 금지)
  const externalId = `guardian-${userId}-${crypto.randomUUID()}`

  // 3. AssumeRole 시 ExternalId 필수 포함
  const accountId = await this.verifyRoleArn(dto.roleArn!, externalId)

  // 4. 계정 ID 중복 등록 방지 (한 AWS 계정당 1개 연동)
  const existing = await this.supabase
    .from('aws_connections')
    .select('id')
    .eq('user_id', userId)
    .eq('aws_account_id', accountId)
    .single()

  if (existing.data) {
    throw new BadRequestException('이미 등록된 AWS 계정입니다')
  }

  // 5. ExternalId와 함께 저장
  return this.supabase.from('aws_connections').insert({
    user_id: userId,
    method: 'role',
    role_arn: dto.roleArn,
    external_id: externalId,  // 변경 불가 (이후 업데이트 금지)
    aws_account_id: accountId,
  })
}
```

---

## 7. Telegram Bot 보안

```typescript
// telegram-bot/security.ts
import * as crypto from 'crypto'

// Telegram Webhook 서명 검증 (봇 토큰 기반)
export function verifyTelegramWebhook(
  body: string,
  secretToken: string,
  headerToken: string
): boolean {
  const expected = crypto
    .createHmac('sha256', secretToken)
    .update(body)
    .digest('hex')
  return crypto.timingSafeEqual(
    Buffer.from(expected),
    Buffer.from(headerToken)
  )
}

// 명령어 입력 Sanitize (Command Injection 방지)
export function sanitizeInput(input: string): string {
  // 허용 문자: 영문, 숫자, 일부 특수문자만
  return input.replace(/[^a-zA-Z0-9\-_.:@/\s]/g, '').trim().slice(0, 200)
}

// 사용자 바인딩 검증 (등록된 chat_id만 명령어 처리)
export async function assertRegisteredUser(chatId: number, supabase: any) {
  const { data } = await supabase
    .from('users')
    .select('id, plan')
    .eq('telegram_chat_id', chatId.toString())
    .single()

  if (!data) {
    throw new Error('등록되지 않은 사용자입니다. 웹에서 먼저 가입해주세요.')
  }
  return data
}
```

---

## 8. Lambda 보안 강화

```python
# lambda/guardian/security.py

import re, ipaddress

# 허용 AWS 리전 화이트리스트 (사용자 설정값 검증용)
VALID_REGIONS = {
    'ap-northeast-2', 'ap-northeast-1', 'ap-southeast-1',
    'us-east-1', 'us-east-2', 'us-west-2', 'eu-west-1', 'eu-central-1'
}

def validate_regions(regions: list) -> list:
    """사용자 설정 리전 값 화이트리스트 검증"""
    return [r for r in regions if r in VALID_REGIONS]

def validate_instance_id(instance_id: str) -> bool:
    """EC2 인스턴스 ID 형식 검증 (Command Injection 방지)"""
    return bool(re.match(r'^i-[0-9a-f]{8,17}$', instance_id))

def validate_bucket_name(name: str) -> bool:
    """S3 버킷 이름 형식 검증"""
    return bool(re.match(r'^[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9]$', name))

def safe_stop_instance(session, instance_id: str, region: str):
    """검증 후 EC2 중지 실행"""
    if not validate_instance_id(instance_id):
        raise ValueError(f"유효하지 않은 인스턴스 ID: {instance_id}")
    if region not in VALID_REGIONS:
        raise ValueError(f"허용되지 않는 리전: {region}")

    ec2 = session.client('ec2', region_name=region)
    ec2.stop_instances(InstanceIds=[instance_id])

def safe_block_s3(session, bucket_name: str):
    """검증 후 S3 퍼블릭 차단"""
    if not validate_bucket_name(bucket_name):
        raise ValueError(f"유효하지 않은 버킷 이름: {bucket_name}")

    s3 = session.client('s3')
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
    )
```

---

## 9. 감사 로그 (Audit Log)

```sql
-- 민감 작업 전용 감사 테이블
create table audit_logs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references users(id),
  action      text not null,   -- CONNECTION_CREATED | CONNECTION_DELETED | SETTING_CHANGED | AUTO_STOP | AUTO_BLOCK
  ip_address  text,
  user_agent  text,
  before_data jsonb,           -- 변경 전 (민감 필드 마스킹)
  after_data  jsonb,           -- 변경 후 (민감 필드 마스킹)
  created_at  timestamptz default now()
);

-- 감사 로그는 삭제/수정 불가
create policy "audit_insert_only" on audit_logs
  for insert with check (true);
-- select는 service_role만
```

```typescript
// interceptors/audit.interceptor.ts
@Injectable()
export class AuditInterceptor implements NestInterceptor {
  constructor(private auditService: AuditService) {}

  intercept(ctx: ExecutionContext, next: CallHandler): Observable<any> {
    const req = ctx.switchToHttp().getRequest()
    const AUDIT_ACTIONS = [
      'POST /connections', 'DELETE /connections',
      'PATCH /settings', 'POST /connections/verify'
    ]
    const key = `${req.method} ${req.path.replace(/\/[0-9a-f-]{36}/g, '')}`

    return next.handle().pipe(
      tap(async () => {
        if (AUDIT_ACTIONS.some(a => key.includes(a.split(' ')[1]))) {
          await this.auditService.log({
            userId: req.user?.id,
            action: key,
            ipAddress: req.ip,
            userAgent: req.headers['user-agent'],
          })
        }
      })
    )
  }
}
```

---

## 10. 공급망 보안 (Dependency)

```bash
# package.json scripts 추가
{
  "scripts": {
    "audit": "npm audit --audit-level=high",
    "audit:fix": "npm audit fix",
    "snyk": "snyk test"
  }
}
```

```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: npm audit
        run: npm audit --audit-level=high
      - name: Python safety check
        run: pip install safety && safety check -r lambda/guardian/requirements.txt
      - name: Trivy scan (컨테이너/파일시스템)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          severity: HIGH,CRITICAL
```

---

## 11. 환경변수 & 시크릿 관리

```bash
# ❌ 절대 금지
TELEGRAM_BOT_TOKEN=1234567890:ABCDEF...  # .env 파일 커밋

# ✅ 올바른 방법
# Lambda → AWS SSM Parameter Store (SecureString)
aws ssm put-parameter \
  --name "/guardian/prod/telegram_bot_token" \
  --value "your_token" \
  --type SecureString \
  --key-id alias/guardian-key

# NestJS API → 런타임 주입 (Railway/ECS Secret)
# .env.example 만 커밋 (실제 값 없음)
```

```python
# lambda/guardian/config.py — SSM에서 런타임 로드
import boto3
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(name: str) -> str:
    ssm = boto3.client('ssm')
    resp = ssm.get_parameter(Name=f'/guardian/prod/{name}', WithDecryption=True)
    return resp['Parameter']['Value']

# 사용: get_secret('telegram_bot_token')
```

---

## 12. 보안 체크리스트

```
인프라
  [ ] IMDSv2 강제 (EC2/ECS)
  [ ] Lambda VPC 격리 (필요 시)
  [ ] KMS 키 자동 교체 (1년)
  [ ] CloudTrail 전체 리전 활성화
  [ ] AWS Config Rules 활성화

API 서버
  [ ] HTTPS 강제 (HTTP → HTTPS 리다이렉트)
  [ ] helmet 보안 헤더 적용
  [ ] Rate Limiting 전체 엔드포인트
  [ ] Input Validation (whitelist 방식)
  [ ] CORS 엄격 설정
  [ ] 에러 메시지 prod 숨김

데이터
  [ ] RLS 전 테이블 적용
  [ ] 자격증명 KMS 암호화
  [ ] 응답에서 민감 필드 마스킹
  [ ] 감사 로그 immutable 설정
  [ ] 30일 이상 이벤트 TTL 자동 삭제

인증/인가
  [ ] JWT 만료 시간 단축 (15분 access / 7일 refresh)
  [ ] Refresh Token Rotation
  [ ] IDOR 방지 Guard 전 엔드포인트
  [ ] ExternalId 서버 생성 강제

봇/외부 연동
  [ ] Telegram Webhook 서명 검증
  [ ] Discord Interaction 서명 검증 (ed25519)
  [ ] Webhook URL 화이트리스트

운영
  [ ] 의존성 취약점 주간 스캔 (npm audit, safety)
  [ ] 시크릿 커밋 방지 (git-secrets / gitleaks)
  [ ] 침투 테스트 분기 1회
```

---

## 13. 보안 사고 대응 플로우

```
이상 감지 (비정상 API 호출 급증 / 미인가 접근)
    ↓
1. 해당 사용자 세션 즉시 무효화
    ↓
2. AWS 연동 자격증명 비활성화 (is_active = false)
    ↓
3. Telegram 관리자 알림 발송
    ↓
4. audit_logs 기록
    ↓
5. 사용자에게 이메일 알림 + 재인증 요구
```
