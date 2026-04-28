terraform {
  backend "s3" {
    endpoint            = "http://localhost:4566"
    region              = "us-east-1"
    bucket              = "aws-guardian-state"
    key                 = "aws-guardian/terraform.tfstate"
    encrypt             = false
    dynamodb_table      = "terraform-locks"
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
  }
}
