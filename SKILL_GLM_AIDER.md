# SKILL_GLM_AIDER.md — GLM 구독 API × aider 연결 가이드

> OpenAI 호환 엔드포인트 + 별도 인증 방식의 GLM 구독 API를
> aider에서 사용하는 모든 패턴 정리

---

## 핵심 원리

aider는 `--openai-api-base` 와 `--openai-api-key` 두 옵션으로
어떤 OpenAI 호환 엔드포인트든 연결 가능하다.
별도 인증 방식이라도 **프록시 래퍼**를 끼우면 aider가 인식하는
표준 Bearer 토큰 형식으로 변환할 수 있다.

---

## 패턴 A — API 키가 Bearer 토큰으로 직접 동작하는 경우

GLM 구독 API가 `Authorization: Bearer <YOUR_KEY>` 를 그대로
받아준다면 aider 옵션 두 개만으로 끝난다.

```bash
# .env.glm
GLM_API_BASE=https://your-glm-endpoint.com/v1
GLM_API_KEY=your-subscription-key
GLM_MODEL=glm-4-plus   # 실제 모델명으로 교체
```

```bash
# orchestra.sh — pane 1 GLM 부분
aider \
  --model openai/glm-4-plus \
  --openai-api-base "$GLM_API_BASE" \
  --openai-api-key  "$GLM_API_KEY" \
  --read .ai-orchestra/prompts/glm.md \
  --read .ai-orchestra/shared/tasks/ \
  --watch-files \
  --auto-commits \
  --commit-prompt 'feat: GLM implementation'
```

> `--model openai/<이름>` 형식을 쓰면 aider가 OpenAI 호환으로
> 인식하고 `--openai-api-base` 엔드포인트로 요청을 보낸다.

---

## 패턴 B — 별도 인증 헤더가 필요한 경우

GLM 구독 API가 `Authorization` 이 아닌 커스텀 헤더
(예: `X-Auth-Token`, `X-Api-Key`, `X-Subscription-Key` 등)를
요구한다면 **경량 프록시**를 로컬에 띄워서 헤더를 변환한다.

### glm-proxy.py

```python
#!/usr/bin/env python3
"""
GLM 구독 API 프록시
aider → localhost:8765/v1/chat/completions
     → GLM 구독 엔드포인트 (커스텀 인증 헤더 변환)
"""
import os, json, httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()

GLM_BASE    = os.environ["GLM_API_BASE"]      # 실제 GLM 엔드포인트
GLM_KEY     = os.environ["GLM_API_KEY"]       # 구독 키
AUTH_HEADER = os.environ.get("GLM_AUTH_HEADER", "Authorization")  # 인증 헤더명
AUTH_PREFIX = os.environ.get("GLM_AUTH_PREFIX", "Bearer")         # 헤더 값 접두사

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request):
    body = await request.body()

    # 인증 헤더 구성 (별도 방식 대응)
    if AUTH_PREFIX:
        auth_value = f"{AUTH_PREFIX} {GLM_KEY}"
    else:
        auth_value = GLM_KEY

    headers = {
        "Content-Type": "application/json",
        AUTH_HEADER: auth_value,
    }

    target_url = f"{GLM_BASE}/v1/{path}"

    # 스트리밍 응답 처리
    async def stream_response():
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                request.method, target_url,
                headers=headers, content=body
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.request(
            request.method, target_url,
            headers=headers, content=body
        )
        # 스트리밍 여부 판별
        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
                headers={"X-Accel-Buffering": "no"}
            )
        return resp

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
```

```bash
# requirements: glm-proxy
pip install fastapi uvicorn httpx
```

### 프록시 실행 + aider 연결

```bash
# .env.glm (패턴 B용)
GLM_API_BASE=https://your-glm-endpoint.com
GLM_API_KEY=your-subscription-key
GLM_AUTH_HEADER=X-Auth-Token      # 실제 헤더명으로 교체
GLM_AUTH_PREFIX=                  # 접두사 없으면 빈 문자열
GLM_MODEL=glm-4-plus
```

```bash
# 프록시를 백그라운드로 먼저 실행
source .env.glm
python .ai-orchestra/glm-proxy.py &
GLM_PROXY_PID=$!
echo "GLM 프록시 PID: $GLM_PROXY_PID"

# aider는 로컬 프록시로 연결
aider \
  --model openai/$GLM_MODEL \
  --openai-api-base http://127.0.0.1:8765 \
  --openai-api-key  dummy \
  --read .ai-orchestra/prompts/glm.md \
  --read .ai-orchestra/shared/tasks/ \
  --watch-files \
  --auto-commits \
  --commit-prompt 'feat: GLM implementation'
```

> `--openai-api-key dummy` 는 aider가 키 필드를 요구하기 때문에
> 형식상 채워넣는 값이다. 실제 인증은 프록시가 처리한다.

---

## 패턴 C — JWT / 세션 토큰 방식 (만료 갱신 필요)

구독 키로 JWT를 발급받아야 하거나 토큰 만료가 있는 경우,
프록시에 자동 갱신 로직을 추가한다.

```python
# glm-proxy.py 에 토큰 갱신 추가
import time, threading

class TokenManager:
    def __init__(self):
        self._token = None
        self._expires_at = 0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        with self._lock:
            if time.time() < self._expires_at - 60:  # 만료 60초 전 갱신
                return self._token
            self._refresh()
            return self._token

    def _refresh(self):
        """GLM 구독 API 토큰 갱신 — 실제 갱신 엔드포인트로 교체"""
        resp = httpx.post(
            f"{GLM_BASE}/auth/token",
            json={"api_key": GLM_KEY},
            timeout=10
        )
        data = resp.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 3600)

token_mgr = TokenManager()

# proxy 핸들러에서 사용
auth_value = f"Bearer {token_mgr.get_token()}"
```

---

## orchestra.sh 최종본 (3-AI 전체)

```bash
#!/usr/bin/env bash
# .ai-orchestra/orchestra.sh

set -e
PROJECT_ROOT="${1:-$(pwd)}"
SESSION="guardian-dev"

# 환경변수 로드
source "$PROJECT_ROOT/.env.glm"

# GLM 프록시 시작 (별도 인증 방식인 경우 — 패턴 A면 이 블록 제거)
echo "⚡ GLM 프록시 시작..."
python "$PROJECT_ROOT/.ai-orchestra/glm-proxy.py" \
  > "$PROJECT_ROOT/.ai-orchestra/logs/glm-proxy.log" 2>&1 &
GLM_PROXY_PID=$!
echo $GLM_PROXY_PID > "$PROJECT_ROOT/.ai-orchestra/glm-proxy.pid"

# 프록시 준비 대기
sleep 2
curl -s http://127.0.0.1:8765/v1/models > /dev/null 2>&1 \
  && echo "✅ GLM 프록시 준비 완료" \
  || echo "⚠️  GLM 프록시 응답 없음 — 로그 확인: .ai-orchestra/logs/glm-proxy.log"

# 기존 세션 정리
tmux kill-session -t "$SESSION" 2>/dev/null || true

# 세션 생성
tmux new-session -d -s "$SESSION" -x 220 -y 50
tmux split-window -v -p 60 -t "$SESSION:0"
tmux split-window -v -p 50 -t "$SESSION:0.1"
tmux split-window -h -p 50 -t "$SESSION:0.1"

# 각 pane 디렉토리 이동
for pane in 0 1 2 3; do
  tmux send-keys -t "$SESSION:0.$pane" "cd $PROJECT_ROOT" Enter
done

# ── pane 0: Claude Code 사령관 (구독 CLI) ──
tmux send-keys -t "$SESSION:0.0" \
  "claude \
    --add-dir .ai-orchestra/prompts \
    --add-dir .ai-orchestra/shared/tasks" Enter

# ── pane 1: GLM 5.1 구현 (구독 API → 프록시) ──
tmux send-keys -t "$SESSION:0.1" \
  "aider \
    --model openai/$GLM_MODEL \
    --openai-api-base http://127.0.0.1:8765 \
    --openai-api-key dummy \
    --read .ai-orchestra/prompts/glm.md \
    --watch-files \
    --auto-commits \
    --commit-prompt 'feat: GLM implementation'" Enter

# ── pane 2: Gemini 문서화 (구독 CLI) ──
tmux send-keys -t "$SESSION:0.2" \
  "gemini \
    --prompt-file .ai-orchestra/prompts/gemini.md" Enter

# ── pane 3: LocalStack ──
tmux send-keys -t "$SESSION:0.3" \
  "docker compose -f localstack/docker-compose.yml up" Enter

# 타이틀
tmux select-pane -t "$SESSION:0.0" -T "🧠 Claude Code (사령관)"
tmux select-pane -t "$SESSION:0.1" -T "⚡ GLM 5.1 (구현)"
tmux select-pane -t "$SESSION:0.2" -T "📄 Gemini (문서화)"
tmux select-pane -t "$SESSION:0.3" -T "🐳 LocalStack"

# 종료 시 프록시 정리
trap "kill $GLM_PROXY_PID 2>/dev/null; echo '🛑 GLM 프록시 종료'" EXIT

tmux attach-session -t "$SESSION"
```

---

## .env.glm 설정 파일

```bash
# .env.glm  (git에 절대 커밋 금지 → .gitignore에 추가)

# ── 공통 필수 ──
GLM_API_BASE=https://your-glm-endpoint.com   # 실제 엔드포인트
GLM_API_KEY=your-subscription-key            # 구독 키
GLM_MODEL=glm-4-plus                         # 실제 모델명

# ── 별도 인증 방식 설정 (패턴 B) ──
# 헤더명: Authorization / X-Auth-Token / X-Api-Key 등
GLM_AUTH_HEADER=Authorization
# 접두사: Bearer / Token / 빈 문자열
GLM_AUTH_PREFIX=Bearer

# ── JWT 갱신 필요 시 (패턴 C) ──
# GLM_TOKEN_ENDPOINT=https://your-glm-endpoint.com/auth/token
# GLM_TOKEN_EXPIRES_IN=3600
```

```bash
# .gitignore에 추가
.env.glm
.ai-orchestra/logs/
.ai-orchestra/glm-proxy.pid
```

---

## 연결 테스트

```bash
# 1. 프록시 단독 테스트
source .env.glm
python .ai-orchestra/glm-proxy.py &

curl http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$GLM_MODEL"'",
    "messages": [{"role": "user", "content": "hello"}],
    "max_tokens": 10
  }'

# 2. aider 연결 테스트 (한 줄만 물어보고 종료)
echo "hello" | aider \
  --model openai/$GLM_MODEL \
  --openai-api-base http://127.0.0.1:8765 \
  --openai-api-key dummy \
  --no-git \
  --yes

# 3. 정상이면 orchestra.sh 실행
bash .ai-orchestra/orchestra.sh $(pwd)
```

---

## 어떤 패턴인지 모를 때 판별 방법

```bash
# GLM API 문서/대시보드에서 확인하거나 직접 curl 테스트

# 테스트 1: Bearer 토큰 (패턴 A)
curl https://your-glm-endpoint.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-4-plus","messages":[{"role":"user","content":"hi"}]}'

# 테스트 2: 커스텀 헤더 (패턴 B 예시)
curl https://your-glm-endpoint.com/v1/chat/completions \
  -H "X-Auth-Token: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-4-plus","messages":[{"role":"user","content":"hi"}]}'

# → 200 응답 오는 패턴이 맞는 것
```
