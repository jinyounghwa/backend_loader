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

  tags = {
    Name        = "aws-guardian-lambda-role"
    Environment = var.environment
  }
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
        Action = ["ce:GetCostAndUsage"]
        Resource = ["*"]
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          }
        }
      },
      {
        Sid    = "EC2Describe"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeRegions",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = ["*"]
      },
      {
        Sid    = "EC2StopInstances"
        Effect = "Allow"
        Action = ["ec2:StopInstances"]
        Resource = [
          "arn:aws:ec2:*:*:instance/*"
        ]
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
          "s3:GetBucketLocation",
          "s3:GetPublicAccessBlock"
        ]
        Resource = ["arn:aws:s3:::*"]
      },
      {
        Sid    = "S3WritePublicAccessBlock"
        Effect = "Allow"
        Action = ["s3:PutPublicAccessBlock"]
        Resource = ["arn:aws:s3:::*"]
        Condition = {
          StringEquals = {
            "s3:ResourceTag/GuardianManaged" = "true"
          }
        }
      },
      {
        Sid    = "CloudTrail"
        Effect = "Allow"
        Action = ["cloudtrail:LookupEvents"]
        Resource = ["arn:aws:cloudtrail:*:*:trail/*"]
      },
      {
        Sid    = "IAM"
        Effect = "Allow"
        Action = [
          "iam:ListUsers",
          "iam:ListAccessKeys",
          "iam:GetUser"
        ]
        Resource = ["arn:aws:iam::*:user/*"]
      },
      {
        Sid    = "GuardDuty"
        Effect = "Allow"
        Action = [
          "guardduty:ListDetectors",
          "guardduty:ListFindings",
          "guardduty:GetFindings"
        ]
        Resource = ["arn:aws:guardduty:*:*:detector/*"]
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
          "${aws_dynamodb_table.events.arn}/index/*",
          "${aws_dynamodb_table.responses.arn}/index/*",
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
        Resource = ["arn:aws:ssm:*:*:parameter/aws-guardian/*"]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          aws_cloudwatch_log_group.guardian_logs.arn,
          aws_cloudwatch_log_group.discord_logs.arn
        ]
      },
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = ["cloudwatch:PutMetricData"]
        Resource = ["*"]
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "aws-guardian"
          }
        }
      },
      {
        Sid    = "STSCrossAccount"
        Effect = "Allow"
        Action = ["sts:AssumeRole"]
        Resource = ["arn:aws:iam::*:role/aws-guardian-cross-account-role"]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "true"
          }
        }
      }
    ]
  })
}

