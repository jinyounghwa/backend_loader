resource "aws_iam_role" "lambda_role" {
  name = "aws-guardian-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "aws-guardian-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CostExplorer"
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage"
        ]
        Resource = "*"
      },
      {
        Sid    = "EC2Read"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeRegions",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = "*"
      },
      {
        Sid    = "EC2StopInstances"
        Effect = "Allow"
        Action = [
          "ec2:StopInstances"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:ResourceTag/AutoManaged" = "true"
          }
        }
      },
      {
        Sid    = "S3Read"
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets",
          "s3:GetBucketAcl",
          "s3:GetBucketPolicy",
          "s3:GetPublicAccessBlock"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3WritePublicAccessBlock"
        Effect = "Allow"
        Action = [
          "s3:PutPublicAccessBlock"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "s3:ResourceTag/GuardianManaged" = "true"
          }
        }
      },
      {
        Sid    = "CloudTrail"
        Effect = "Allow"
        Action = [
          "cloudtrail:LookupEvents"
        ]
        Resource = "*"
      },
      {
        Sid    = "IAM"
        Effect = "Allow"
        Action = [
          "iam:ListUsers",
          "iam:ListAccessKeys",
          "iam:GetUser"
        ]
        Resource = "*"
      },
      {
        Sid    = "GuardDuty"
        Effect = "Allow"
        Action = [
          "guardduty:ListDetectors",
          "guardduty:ListFindings",
          "guardduty:GetFindings"
        ]
        Resource = "*"
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:CreateTable",
          "dynamodb:DescribeTable"
        ]
        Resource = [
          aws_dynamodb_table.events.arn,
          aws_dynamodb_table.responses.arn,
          "arn:aws:dynamodb:*:*:table/guardian-iam-baseline"
        ]
      },
      {
        Sid    = "SSMParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter"
        ]
        Resource = "arn:aws:ssm:*:*:parameter/guardian/*"
      },
      {
        Sid    = "CloudWatch"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/aws-guardian-*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy" {
  policy_arn = aws_iam_role_policy.lambda_policy.arn
  role       = aws_iam_role.lambda_role.name

  depends_on = [aws_iam_role_policy.lambda_policy]
}
