以下のように Terraform コードをプロジェクトルート（`/home/jin/llm_driven_aws_build_test`）に配置してください。

---

## main.tf

```hcl
provider "aws" {
  region = "ap-northeast-1"
}

# デフォルト VPC を取得（なければ利用可能な VPC の 1 件目を later ローカルで選択）
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

# サブネット一覧を取得（VPC 内のサブネット）
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
}

# Amazon Linux2 の最新 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-ebs"]
  }
}

# セキュリティグループ（ポート 8000 開放）
resource "aws_security_group" "allow_8000" {
  name        = "allow_8000"
  description = "Allow inbound port 8000"
  vpc_id      = local.vpc_id

  ingress {
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

# EC2 インスタンス
resource "aws_instance" "app" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t3.micro"
  vpc_security_group_ids      = [aws_security_group.allow_8000.id]
  subnet_id                   = var.subnet_id != null ? var.subnet_id : tolist(data.aws_subnets.default.ids)[0]
  associate_public_ip_address = var.subnet_id != null ? false : true

  # Git からクローンして FastAPI を起動する user_data
  user_data = <<-EOF
    #!/bin/bash
    set -e

    APP_USER=appuser
    if ! id "$${APP_USER}" >/dev/null 2>&1; then
      useradd -m -s /bin/bash "$${APP_USER}"
    fi

    yum update -y
    yum install -y git python3 python3-pip

    mkdir -p /home/$${APP_USER}/.ssh
    chmod 700 /home/$${APP_USER}/.ssh
    echo "${local.ssh_public_key}" > /home/$${APP_USER}/.ssh/authorized_keys
    chmod 600 /home/$${APP_USER}/.ssh/authorized_keys
    chown -R $${APP_USER}: /home/$${APP_USER}/.ssh

    cd /home/$${APP_USER}
    git clone ${var.git_repo_url}
    cd ${var.repo_name}/app

    if [ ! -f .env ]; then
      cp .env.example .env
    fi

    pip3 install -r requirements.txt

    nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
  EOF
}

# SSH 公開鍵を AWS 側の key_pair にも登録（SSH ログイン用）
resource "aws_key_pair" "deployer" {
  key_name   = "deployer-key"
  public_key = local.ssh_public_key
}

# 外部に見える IP を出力
output "instance_public_ip" {
  description = "EC2 インスタンスの Public IP"
  value       = aws_instance.app.public_ip
}
```

---

## variables.tf

```hcl
variable "git_repo_url" {
  description = "Git リポジトリ URL（user_data でクローン）"
  type        = string
  default     = "https://github.com/machu-purple/llm_driven_aws_build_test.git"
}

variable "repo_name" {
  description = "リポジトリ名（user_data でディレクトリ移動）"
  type        = string
  default     = "llm_driven_aws_build_test"
}

variable "ssh_public_key_path" {
  description = "実行時に -var=ssh_public_key_path=/絶対パス/id_rsa.pub を渡すこと"
  type        = string
}

variable "vpc_id" {
  description = "既存 VPC を指定する場合は ID を渡す（オプション）"
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "既存 Subnet を指定する場合は ID を渡す（オプション）"
  type        = string
  default     = null
}
```

---

## locals.tf

```hcl
locals {
  ssh_public_key = file(var.ssh_public_key_path)
}
```

---

これで Terraform のコード作成は完了です。  
次に `terraform init` → `terraform plan` を実行しますが、`ssh_public_key_path` は必須変数なので、以下の形式で SSH 公開鍵ファイル（id_rsa.pub）の絶対パスをお知らせください。

```
-var=ssh_public_key_path=/absolute/path/to/id_rsa.pub
```

お手数ですが、SSH 公開鍵の絶対パスを教えてください。