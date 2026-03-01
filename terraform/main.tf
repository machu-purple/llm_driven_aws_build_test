terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.100.0"
    }
  }
  required_version = ">= 1.0.0"
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "aws_profile" {
  type    = string
  default = "default"
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

variable "git_repo_url" {
  type    = string
  default = "https://github.com/J0632714/llm_driven_aws_build_test.git"
}

variable "repo_name" {
  type    = string
  default = "llm_driven_aws_build_test"
}

variable "ssh_public_key_path" {
  type        = string
  description = "実行時に -var=ssh_public_key_path=/絶対パス/id_rsa.pub を渡すこと"
  default     = "~/.ssh/id_rsa.pub"
}

variable "vpc_id" {
  type    = string
  default = null
}

variable "subnet_id" {
  type    = string
  default = null
}

data "aws_vpcs" "default" {
  filter {
    name   = "isDefault"
    values = ["true"]
  }
}

data "aws_vpcs" "all" {}

locals {
  vpc_id = var.vpc_id != null
    ? var.vpc_id
    : (
      length(data.aws_vpcs.default.ids) > 0
        ? data.aws_vpcs.default.ids[0]
        : data.aws_vpcs.all.ids[0]
    )
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_security_group" "app_sg" {
  name        = "${var.repo_name}-sg"
  description = "Allow SSH and app port"
  vpc_id      = local.vpc_id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "App port"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_key_pair" "deployer" {
  key_name   = "${var.repo_name}-key"
  public_key = file(var.ssh_public_key_path)
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t3.micro"
  key_name                    = aws_key_pair.deployer.key_name
  subnet_id                   = var.subnet_id != null ? var.subnet_id : data.aws_subnets.default.ids[0]
  associate_public_ip_address = var.subnet_id != null ? false : true
  vpc_security_group_ids      = [aws_security_group.app_sg.id]

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    amazon-linux-extras install -y python3
    useradd -m appuser
    mkdir -p /home/appuser/.ssh
    cp /home/ec2-user/.ssh/authorized_keys /home/appuser/.ssh/authorized_keys
    chown -R appuser:appuser /home/appuser/.ssh
    cd /home/appuser
    git clone ${var.git_repo_url}
    cd ${var.repo_name}/app
    if [ ! -f .env ]; then
      cp .env.example .env
    fi
    pip3 install --upgrade pip
    pip3 install -r requirements.txt
    nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
  EOF

  tags = {
    Name = var.repo_name
  }
}

output "public_ip" {
  value = aws_instance.app.public_ip
}