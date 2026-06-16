# ---------------------------------------------------------
# AWS PROVIDER, BACKEND & LOCALS
# ---------------------------------------------------------
terraform {
  backend "s3" {
    # TODO: Replace this with the exact bucket name you created in AWS S3
    bucket = "g360-tf-state"
    key    = "g360/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  name_prefix = "g360"
  # Using Haiku for minimal cost per token
  bedrock_model = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0" 
}

# ---------------------------------------------------------
# 1. NETWORKING (Public/Private Subnets & Cost-Optimized NAT)
# ---------------------------------------------------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "${local.name_prefix}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  database_subnets = ["10.0.201.0/24", "10.0.202.0/24"]

  # COST SAVING: Single NAT Gateway instead of one per AZ
  enable_nat_gateway     = true
  single_nat_gateway     = true 
  enable_dns_hostnames   = true
}

# ---------------------------------------------------------
# 2. DATA LAYER (S3, RDS Free Tier, DynamoDB)
# ---------------------------------------------------------
resource "random_id" "suffix" { byte_length = 4 }

resource "aws_s3_bucket" "data_lake" {
  bucket        = "${local.name_prefix}-data-lake-${random_id.suffix.hex}"
  force_destroy = true # Allows easy cleanup for demos
}

# COST SAVING: DynamoDB instead of expensive DocumentDB
resource "aws_dynamodb_table" "nosql_store" {
  name           = "${local.name_prefix}-documents"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "DocumentId"
  attribute {
    name = "DocumentId"
    type = "S"
  }
}

# Generate a random password for the database
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$&*()-_=+[]{}<>:?"
}

# Security Group to protect the database
resource "aws_security_group" "db_sg" {
  name        = "${local.name_prefix}-db-sg"
  description = "Database security group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

# COST SAVING: t4g.micro is Free Tier eligible
resource "aws_db_instance" "postgres" {
  identifier             = "${local.name_prefix}-db"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  engine                 = "postgres"
  username               = "g360admin"
  password               = random_password.db_password.result
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  skip_final_snapshot    = true # Critical for easy terraform destroy
}

# ---------------------------------------------------------
# 3. AI COMPUTE LAYER (Fargate Spot & Bedrock IAM)
# ---------------------------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"
}

# IAM Role for the Fargate Task (Least Privilege)
resource "aws_iam_role" "task_role" {
  name = "${local.name_prefix}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "ai_data_access" {
  name = "ai-and-data-access"
  role = aws_iam_role.task_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = [local.bedrock_model] },
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = ["${aws_s3_bucket.data_lake.arn}/*"] },
      { Effect = "Allow", Action = ["dynamodb:*"], Resource = [aws_dynamodb_table.nosql_store.arn] }
    ]
  })
}

# ---------------------------------------------------------
# 4. FRONT DOOR (API Gateway HTTP API)
# ---------------------------------------------------------
resource "aws_apigatewayv2_api" "backend_api" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
}

# Outputs to use in your demo
output "api_endpoint" {
  value = aws_apigatewayv2_api.backend_api.api_endpoint
  description = "The public URL to hit your AI backend."
}
output "s3_bucket_name" {
  value = aws_s3_bucket.data_lake.id
}

# ---------------------------------------------------------
# 5. DOCKER REGISTRY (ECR)
# ---------------------------------------------------------
resource "aws_ecr_repository" "backend_repo" {
  name                 = "${local.name_prefix}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete        = true # Makes it easy to delete later
}