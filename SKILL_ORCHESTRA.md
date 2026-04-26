# SKILL_ORCHESTRA.md — 3-AI 개발 환경 구현 명세

---

## 1. 전제 조건 설치

```bash
# 공통
brew install tmux

# aider (AI 코딩 어시스턴트)
pip install aider-chat

# Claude Code CLI (구독 — API 키 불필요)
npm install -g @anthropic-ai/claude-code
# 설치 후

---

## 2. orchestra.sh — tmux 자동 구성 스크립트

```bash
#!/usr/bin/env bash
# .ai-orchestra/orchestra.sh
# 사용법: bash orchestra.sh [프로젝트_루트_경로]

set -e
PROJECT_ROOT="${1:-$(pwd)}"
SESSION="guardian-dev"

# 기존 세션 정리
tmux kill-session -t "$SESSION" 2>/dev/null || true

# 새 세션 시작 (pane 0: Claude Code)
tmux new-session -d -s "$SESSION" -x 220 -y 50

# 레이아웃: 상단 Claude / 중단 GLM+Gemini / 하단 LocalStack
tmux split-window -v -p 60 -t "$SESSION:0"   # pane 1 (하단)
tmux split-window -v -p 50 -t "$SESSION:0.1" # pane 2 (중단)
tmux split-window -h -p 50 -t "$SESSION:0.1" # pane 1을 좌우 분할 → pane 1=GLM, pane 2=Gemini

# 각 pane 디렉토리 이동
for pane in 0 1 2 3; do
  tmux send-keys -t "$SESSION:0.$pane" "cd $PROJECT_ROOT" Enter
done

# pane 0: Claude Code (사령관)
tmux send-keys -t "$SESSION:0.0" \
  "aider \
    --model claude-sonnet-4-5 \
    --architect \
    --read .ai-orchestra/prompts/claude.md \
    --read .ai-orchestra/shared/tasks/ \
    --watch-files \
    --no-auto-commits" Enter

# pane 1: GLM 5.1 (구현)
tmux send-keys -t "$SESSION:0.1" \
  "aider \
    --model openrouter/thudm/glm-4-plus \
    --read .ai-orchestra/prompts/glm.md \
    --read .ai-orchestra/shared/tasks/ \
    --watch-files \
    --auto-commits \
    --commit-prompt 'feat: GLM implementation'" Enter

# pane 2: Gemini (문서화)
tmux send-keys -t "$SESSION:0.2" \
  "aider \
    --model gemini/gemini-2.0-flash-exp \
    --read .ai-orchestra/prompts/gemini.md \
    --read .ai-orchestra/shared/docs/ \
    --watch-files \
    --auto-commits \
    --commit-prompt 'docs: Gemini documentation update'" Enter

# pane 3: LocalStack
tmux send-keys -t "$SESSION:0.3" \
  "docker compose -f localstack/docker-compose.yml up --build" Enter

# 타이틀 설정
tmux select-pane -t "$SESSION:0.0" -T "🧠 Claude Code (사령관)"
tmux select-pane -t "$SESSION:0.1" -T "⚡ GLM 5.1 (구현)"
tmux select-pane -t "$SESSION:0.2" -T "📄 Gemini (문서화)"
tmux select-pane -t "$SESSION:0.3" -T "🐳 LocalStack"

tmux attach-session -t "$SESSION"
```

---

## 3. AI 시스템 프롬프트

### .ai-orchestra/prompts/claude.md (사령관)

```markdown
# Claude Code — 사령관 역할

당신은 AWS Guardian SaaS 프로젝트의 사령관입니다.

## 책임
- 태스크를 .ai-orchestra/shared/tasks/TASK_[번호].md 로 분해하여 작성
- GLM이 작성한 코드를 .ai-orchestra/shared/review/ 에서 검토
- 보안 취약점 즉시 지적 (SSRF, IDOR, Injection, 자격증명 노출)
- Gemini에게 문서화 지시를 .ai-orchestra/shared/docs/DOC_[번호].md 로 전달
- LocalStack 테스트 결과 최종 승인

## 태스크 파일 형식
TASK_[번호].md:
- 목표: 한 줄 요약
- 대상 파일: 수정/생성할 파일 경로
- 구현 명세: 상세 요구사항
- 완료 조건: 테스트 통과 기준
- 보안 체크: 반드시 확인할 보안 항목

## 코드 리뷰 기준
1. 입력 검증 (whitelist 방식인가?)
2. 자격증명 노출 없음
3. RLS/OwnershipGuard 적용됨
4. LocalStack 테스트 통과
5. 타입 안전성 (TypeScript strict mode)
```

### .ai-orchestra/prompts/glm.md (구현병)

```markdown
# GLM 5.1 — 구현 역할

당신은 AWS Guardian SaaS의 핵심 구현을 담당합니다.

## 작업 방식
1. .ai-orchestra/shared/tasks/ 에서 TASK 파일 확인
2. 지정된 파일 구현
3. 완료 시 .ai-orchestra/shared/review/REVIEW_[번호].md 작성
4. LocalStack 테스트 코드 반드시 포함

## 코딩 규칙
- TypeScript: strict mode, explicit types
- Python: type hints 필수, f-string 사용
- 모든 외부 입력: 검증 후 사용
- 에러: 절대 삼키지 말 것 (catch → 로깅 → 재throw)
- 환경변수: process.env.X! 금지, 검증 함수 통해 사용

## REVIEW 파일 형식
REVIEW_[번호].md:
- TASK 번호: 참조 태스크
- 변경 파일: 목록
- 테스트 결과: LocalStack 실행 결과 붙여넣기
- 특이사항: 구현 중 발견한 문제
```

### .ai-orchestra/prompts/gemini.md (문서병)

```markdown
# Gemini — 문서화 역할

당신은 AWS Guardian SaaS의 문서화를 담당합니다.

## 작업 방식
1. .ai-orchestra/shared/docs/ 에서 DOC 지시 파일 확인
2. 코드 변경사항을 감지하여 문서 자동 갱신
3. 항상 한국어로 작성 (코드 주석은 영어)

## 담당 문서
- SKILL.md (기술 명세)
- README.md (설치/실행 가이드)
- CHANGELOG.md (변경 이력)
- API.md (NestJS 엔드포인트 목록)
- LOCALSTACK.md (LocalStack 테스트 가이드)

## 문서 품질 기준
- 코드 예시 항상 포함
- 실행 가능한 curl 예시 포함
- LocalStack 에뮬레이션 시 엔드포인트 명시
- 보안 관련 항목은 ⚠️ 표시
```

---

## 4. LocalStack docker-compose.yml

```yaml
# localstack/docker-compose.yml
version: "3.9"

services:
  localstack:
    image: localstack/localstack:3.5
    container_name: guardian-localstack
    ports:
      - "4566:4566"
      - "4510-4559:4510-4559"
    environment:
      - SERVICES=lambda,dynamodb,s3,ssm,sts,events,logs,kms,ce,iam
      - DEBUG=1
      - LAMBDA_EXECUTOR=docker
      - LAMBDA_DOCKER_NETWORK=host
      - AWS_DEFAULT_REGION=ap-northeast-2
      - PERSISTENCE=1                   # 재시작 시 데이터 유지
      - SNAPSHOT_SAVE_STRATEGY=ON_SHUTDOWN
    volumes:
      - "./init:/etc/localstack/init/ready.d"   # 초기화 스크립트
      - "/var/run/docker.sock:/var/run/docker.sock"
      - "localstack-data:/var/lib/localstack"
    networks:
      - guardian-net

  # LocalStack 상태 모니터링 (선택)
  localstack-ui:
    image: localstack/localstack-desktop:latest
    ports:
      - "5050:5050"
    depends_on:
      - localstack
    networks:
      - guardian-net

volumes:
  localstack-data:

networks:
  guardian-net:
    driver: bridge
```

---

## 5. LocalStack 초기화 스크립트

```bash
#!/usr/bin/env bash
# localstack/init/01-setup.sh
# LocalStack 시작 시 자동 실행

set -e
ENDPOINT="http://localhost:4566"
REGION="ap-northeast-2"

echo "🚀 LocalStack 초기화 시작..."

# ── DynamoDB ──
echo "📦 DynamoDB 테이블 생성..."
awslocal dynamodb create-table \
  --table-name guardian-events \
  --attribute-definitions \
    AttributeName=event_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=event_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION

# TTL 설정
awslocal dynamodb update-time-to-live \
  --table-name guardian-events \
  --time-to-live-specification "Enabled=true,AttributeName=ttl" \
  --region $REGION

# ── S3 ──
echo "🪣 S3 테스트 버킷 생성..."
awslocal s3 mb s3://guardian-test-bucket --region $REGION
awslocal s3 mb s3://guardian-public-test --region $REGION  # 퍼블릭 버킷 (감지 테스트용)

# 퍼블릭 버킷 설정 (탐지 테스트용)
awslocal s3api put-bucket-acl \
  --bucket guardian-public-test \
  --acl public-read

# ── SSM ──
echo "🔐 SSM 파라미터 설정..."
awslocal ssm put-parameter \
  --name "/guardian/prod/cost_threshold" \
  --value "10" \
  --type String \
  --region $REGION

awslocal ssm put-parameter \
  --name "/guardian/prod/telegram_bot_token" \
  --value "TEST_BOT_TOKEN" \
  --type SecureString \
  --region $REGION

# ── KMS ──
echo "🔑 KMS 키 생성..."
KMS_KEY_ID=$(awslocal kms create-key \
  --description "Guardian encryption key" \
  --region $REGION \
  --query 'KeyMetadata.KeyId' \
  --output text)

awslocal kms create-alias \
  --alias-name alias/guardian-key \
  --target-key-id $KMS_KEY_ID \
  --region $REGION

echo "KMS_KEY_ID=$KMS_KEY_ID" >> .env.localstack

# ── IAM Role (STS AssumeRole 테스트용) ──
echo "👤 IAM 테스트 Role 생성..."
awslocal iam create-role \
  --role-name guardian-test-role \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"AWS":"arn:aws:iam::000000000000:root"},
      "Action":"sts:AssumeRole",
      "Condition":{"StringEquals":{"sts:ExternalId":"test-external-id"}}
    }]
  }' \
  --region $REGION

# ── Lambda 함수 패키징 및 배포 ──
echo "⚡ Lambda 함수 배포..."

# Guardian Lambda
cd /workspace/lambda/guardian
pip install -r requirements.txt -t . -q
zip -r /tmp/guardian.zip . -q
awslocal lambda create-function \
  --function-name aws-guardian \
  --runtime python3.12 \
  --role arn:aws:iam::000000000000:role/guardian-role \
  --handler handler.lambda_handler \
  --zip-file fileb:///tmp/guardian.zip \
  --timeout 300 \
  --memory-size 256 \
  --environment Variables="{
    TELEGRAM_BOT_TOKEN=TEST_TOKEN,
    DISCORD_WEBHOOK_URL=http://localhost:9999/mock-discord,
    SUPABASE_URL=http://localhost:54321,
    SUPABASE_SERVICE_KEY=test-key,
    ENCRYPTION_KEY=$(openssl rand -hex 32)
  }" \
  --region $REGION

# ── EventBridge 규칙 (5분마다로 단축 — 개발용) ──
echo "⏰ EventBridge 스케줄 설정..."
awslocal events put-rule \
  --name guardian-dev-schedule \
  --schedule-expression "rate(5 minutes)" \
  --state ENABLED \
  --region $REGION

awslocal events put-targets \
  --rule guardian-dev-schedule \
  --targets "Id=GuardianLambda,Arn=arn:aws:lambda:ap-northeast-2:000000000000:function:aws-guardian" \
  --region $REGION

echo "✅ LocalStack 초기화 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Lambda:     awslocal lambda invoke --function-name aws-guardian --payload '{}' out.json"
echo "DynamoDB:   awslocal dynamodb scan --table-name guardian-events"
echo "S3:         awslocal s3 ls"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 6. .env.localstack (로컬 개발용)

```bash
# localstack/.env.localstack
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=ap-northeast-2
AWS_ENDPOINT_URL=http://localhost:4566

# boto3 / SDK LocalStack 라우팅
LOCALSTACK_ENDPOINT=http://localhost:4566

# 앱 설정
TELEGRAM_BOT_TOKEN=test-token
TELEGRAM_CHAT_ID=123456789
DISCORD_WEBHOOK_URL=http://localhost:9999/mock-discord
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_KEY=test-service-key
ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000
KMS_KEY_ID=alias/guardian-key
```

---

## 7. LocalStack용 boto3 세션 팩토리

```python
# lambda/guardian/utils/aws_client.py
import os, boto3
from botocore.config import Config

IS_LOCAL = os.environ.get("AWS_ENDPOINT_URL") is not None
ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", None)

def get_client(service: str, region: str = "ap-northeast-2", **kwargs):
    """
    LocalStack 환경에서는 endpoint_url 자동 주입.
    프로덕션에서는 일반 boto3 클라이언트 반환.
    """
    config = Config(retries={"max_attempts": 3, "mode": "standard"})
    return boto3.client(
        service,
        region_name=region,
        endpoint_url=ENDPOINT,  # None이면 실제 AWS
        config=config,
        **kwargs
    )

def get_session_client(session: boto3.Session, service: str, region: str = "ap-northeast-2"):
    """AssumeRole 세션용 — LocalStack STS 경유"""
    return session.client(
        service,
        region_name=region,
        endpoint_url=ENDPOINT,
    )
```

```typescript
// apps/api/src/lib/aws-client.ts
import { DynamoDBClient } from '@aws-sdk/client-dynamodb'
import { S3Client } from '@aws-sdk/client-s3'
import { SSMClient } from '@aws-sdk/client-ssm'
import { STSClient } from '@aws-sdk/client-sts'
import { KMSClient } from '@aws-sdk/client-kms'

const IS_LOCAL = !!process.env.AWS_ENDPOINT_URL
const endpoint = process.env.AWS_ENDPOINT_URL

const baseConfig = {
  region: process.env.AWS_DEFAULT_REGION ?? 'ap-northeast-2',
  ...(endpoint && { endpoint }),
  ...(IS_LOCAL && {
    credentials: {
      accessKeyId: 'test',
      secretAccessKey: 'test',
    }
  })
}

export const dynamodb  = new DynamoDBClient(baseConfig)
export const s3        = new S3Client(baseConfig)
export const ssm       = new SSMClient(baseConfig)
export const sts       = new STSClient(baseConfig)
export const kms       = new KMSClient(baseConfig)
```

---

## 8. Cost Explorer 모킹 (LocalStack 미지원 → Mock 서버)

```typescript
// localstack/mocks/cost-explorer-mock.ts
// LocalStack은 CE API 미지원 → 경량 Express 목 서버로 대체

import express from 'express'
const app = express()
app.use(express.json())

app.post('/', (req, res) => {
  const body = req.body

  // GetCostAndUsage 응답 모킹
  if (body.Action === 'GetCostAndUsage' || req.path === '/') {
    const mockAmount = process.env.MOCK_COST_AMOUNT ?? '8.50'  // 기본: 정상
    res.json({
      ResultsByTime: [{
        TimePeriod: { Start: '2025-01-01', End: '2025-01-02' },
        Total: { UnblendedCost: { Amount: mockAmount, Unit: 'USD' } },
        Estimated: false
      }],
      DimensionValueAttributes: []
    })
  }
})

app.listen(4580, () => {
  console.log('💰 Cost Explorer Mock 서버 실행 중 → http://localhost:4580')
})
```

```bash
# docker-compose.yml에 추가
  ce-mock:
    build:
      context: ./localstack/mocks
      dockerfile: Dockerfile.ce
    ports:
      - "4580:4580"
    environment:
      - MOCK_COST_AMOUNT=15.00  # 임계값 초과 시나리오 테스트
```

---

## 9. 통합 테스트 스크립트

```bash
#!/usr/bin/env bash
# scripts/test-localstack.sh
# 전체 플로우 E2E 테스트

set -e
source localstack/.env.localstack

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 AWS Guardian LocalStack E2E 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Lambda 직접 호출 테스트
echo ""
echo "📋 [1/5] Lambda 직접 호출..."
awslocal lambda invoke \
  --function-name aws-guardian \
  --payload '{"test": true}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/lambda-result.json
echo "결과:"
cat /tmp/lambda-result.json | python3 -m json.tool

# 2. DynamoDB 이벤트 로그 확인
echo ""
echo "📋 [2/5] DynamoDB 이벤트 로그 확인..."
awslocal dynamodb scan \
  --table-name guardian-events \
  --region ap-northeast-2 | python3 -m json.tool

# 3. S3 퍼블릭 버킷 감지 테스트
echo ""
echo "📋 [3/5] S3 퍼블릭 버킷 감지 테스트..."
# guardian-public-test 버킷 퍼블릭으로 재설정
awslocal s3api put-bucket-acl \
  --bucket guardian-public-test \
  --acl public-read
# Lambda 호출 → 감지 → 자동 차단 확인
awslocal lambda invoke \
  --function-name aws-guardian \
  --payload '{"test_s3": true}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/s3-result.json
echo "S3 감지 결과:"
cat /tmp/s3-result.json | python3 -m json.tool

# 4. 비용 임계값 초과 테스트 (CE Mock MOCK_COST_AMOUNT=15.00)
echo ""
echo "📋 [4/5] 비용 임계값 초과 시나리오..."
MOCK_COST_AMOUNT=15.00 awslocal lambda invoke \
  --function-name aws-guardian \
  --payload '{"test_cost": true}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/cost-result.json
echo "비용 경보 결과:"
cat /tmp/cost-result.json | python3 -m json.tool

# 5. STS AssumeRole 테스트
echo ""
echo "📋 [5/5] STS AssumeRole (Cross-Account) 테스트..."
awslocal sts assume-role \
  --role-arn "arn:aws:iam::000000000000:role/guardian-test-role" \
  --role-session-name "test-session" \
  --external-id "test-external-id" | python3 -m json.tool

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 모든 테스트 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 10. AI 태스크 분배 예시

```
.ai-orchestra/shared/tasks/TASK_001.md
───────────────────────────────────────
목표: CostChecker LocalStack 호환 구현

대상 파일:
  - lambda/guardian/checkers/cost.py
  - lambda/guardian/utils/aws_client.py

구현 명세:
  - get_client() 팩토리 함수 사용 (AWS_ENDPOINT_URL 자동 감지)
  - CE API 미지원 → localhost:4580 목 서버로 폴백
  - 임계값 SSM /guardian/prod/cost_threshold 에서 읽기

완료 조건:
  - bash scripts/test-localstack.sh [4/5] 통과
  - DynamoDB에 COST_ALERT 이벤트 기록됨

보안 체크:
  - boto3 자격증명 코드에 하드코딩 없음
  - 에러 시 스택 트레이스 로그에 민감 정보 미포함

→ 완료 시 shared/review/REVIEW_001.md 작성 요망
```

```
.ai-orchestra/shared/docs/DOC_001.md
───────────────────────────────────────
목표: LOCALSTACK.md 갱신

갱신 내용:
  - Cost Explorer Mock 서버 실행 방법
  - test-localstack.sh 실행 결과 예시
  - 환경변수 MOCK_COST_AMOUNT 설명

참조 파일:
  - lambda/guardian/checkers/cost.py (REVIEW_001 승인 후)
  - localstack/mocks/cost-explorer-mock.ts
```

---

## 11. 빠른 시작 (Quick Start)

```bash
# 1. 저장소 클론 후
git clone https://github.com/yourname/aws-guardian-saas

# 2. 의존성 설치
npm install && pip install aider-chat localstack awscli-local

# 3. 환경변수 복사
cp localstack/.env.localstack.example localstack/.env.localstack

# 4. AI API 키 설정
export ANTHROPIC_API_KEY=...
export OPENROUTER_API_KEY=...   # GLM 5.1 (OpenRouter 경유)
export GEMINI_API_KEY=...

# 5. 오케스트라 실행 (모든 것이 자동으로 시작됨)
bash .ai-orchestra/orchestra.sh $(pwd)

# 6. 첫 태스크 시작 (Claude Code pane에서)
# /add .ai-orchestra/shared/tasks/TASK_001.md
```

---

## 12. tmux 단축키

| 단축키 | 동작 |
|--------|------|
| `Ctrl+b 0` | Claude Code pane 이동 |
| `Ctrl+b 1` | GLM pane 이동 |
| `Ctrl+b 2` | Gemini pane 이동 |
| `Ctrl+b 3` | LocalStack 로그 pane |
| `Ctrl+b z` | 현재 pane 전체화면 토글 |
| `Ctrl+b [` | 스크롤 모드 (로그 확인) |
| `Ctrl+b d` | 세션 detach (백그라운드 유지) |
| `tmux attach -t guardian-dev` | 세션 재연결 |
