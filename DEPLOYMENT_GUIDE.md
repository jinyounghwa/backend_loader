# 배포 가이드

AWS Guardian은 로컬 개발 환경(LocalStack)과 상용 환경(AWS) 두 가지 배포 경로를 지원합니다.

## LocalStack (개발 환경) 배포

로컬 환경에서는 별도의 인프라 구성 없이 도커만으로 시스템을 구동할 수 있습니다.

```bash
# 원클릭 배포 및 실행
./start.sh
```

환경 변수 `AWS_ENV`가 `localstack`(기본값)일 경우, 모든 API 호출은 로컬 엔드포인트로 전달되며 비용 탐지는 가상 데이터를 사용합니다.

## AWS (상용 환경) 배포

상용 환경 배포 시에는 반드시 `AWS_ENV=production`을 설정해야 합니다.

### 1. 사전 준비
- AWS CLI 및 Terraform 설치
- 적절한 권한을 가진 AWS 계정 및 프로필 설정
- 텔레그램 및 디스코드 웹훅 정보 준비

### 2. Terraform을 이용한 인프라 구성
`terraform/` 디렉토리에서 인프라를 배포합니다.

```bash
cd terraform
terraform init

# 변수 파일(terraform.tfvars) 생성 및 값 입력 후 실행
terraform apply
```

### 3. 환경 변수 설정
Lambda 함수에 다음 환경 변수가 설정되어야 합니다.
- `AWS_ENV`: production
- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `TELEGRAM_CHAT_ID`: 알림을 받을 채팅 ID

## IAM 정책 및 권한

AWS Guardian Lambda 함수는 다음 권한이 필요합니다. 보안을 위해 리소스 제한 및 태그 조건을 적용했습니다.

### 주요 권한 목록
- `ce:GetCostAndUsage`: 비용 데이터 조회
- `ec2:Describe*`, `ec2:StopInstances`: EC2 감시 및 중지 (보안 태그가 있는 리소스로 제한 권장)
- `s3:Get*`, `s3:PutPublicAccessBlock`: S3 보안 설정 관리
- `ssm:GetParameter`: `/guardian/*` 경로의 설정 읽기
- `dynamodb:PutItem`, `dynamodb:Query`: 이벤트 로그 기록 및 조회

### SSM 파라미터 접근 제한
파라미터 경로는 반드시 `/guardian/`으로 시작해야 하며, IAM 정책에서 해당 경로에 대해서만 접근을 허용합니다.

## 모니터링 및 로깅

### CloudWatch Logs
- Lambda 실행 로그는 `/aws/lambda/guardian-monitor` 그룹에 기록됩니다.
- 에러 발생 시 상세 정보 노출을 방지하도록 설정되어 있으며, 구조화된 로그를 통해 문제 해결이 가능합니다.

### 이벤트 추적
- 모든 탐지 및 대응 이력은 DynamoDB에 저장됩니다.
- 프론트엔드 대시보드(apps/web)를 통해 시각적으로 확인할 수 있습니다.

## 보안 모범 사례

- 최소 권한 원칙: IAM 정책에서 `Resource: "*"` 사용을 지양하고 필요한 ARN만 명시합니다.
- 입력값 검증: 디스코드 명령어 입력 시 정규표현식을 통해 인스턴스 ID 및 파라미터 형식을 검증합니다.
- 민감 정보 관리: 텔레그램 토큰 등은 SSM Parameter Store의 SecureString으로 관리하는 것을 권장합니다.
- 네트워크 보안: Lambda 함수를 VPC 내에 배치하고 필요한 엔드포인트만 허용하여 외부 노출을 최소화합니다.
