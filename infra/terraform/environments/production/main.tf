terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "veriunlearn-terraform-state"
    key            = "production/eks/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "veriunlearn-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "veriunlearn"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}

module "eks" {
  source = "../../modules/eks"

  project_name = "veriunlearn"
  environment  = "production"

  cluster_version                = var.cluster_version
  vpc_cidr                       = var.vpc_cidr
  cluster_endpoint_public_access = var.cluster_endpoint_public_access

  standard_instance_types = var.standard_instance_types
  standard_capacity_type  = var.standard_capacity_type
  standard_desired_size   = var.standard_desired_size
  standard_min_size       = var.standard_min_size
  standard_max_size       = var.standard_max_size

  gpu_instance_types = var.gpu_instance_types
  gpu_desired_size   = var.gpu_desired_size
  gpu_min_size       = var.gpu_min_size
  gpu_max_size       = var.gpu_max_size

  tags = {
    Project     = "veriunlearn"
    Environment = "production"
    CostCenter  = "ml-platform"
  }
}
