# Terraform 適用の違い（llm_driven_aws_build_test vs terraform-mfd-intelligent-platform-main）

## 結論：SCP で「公開 IP 付き EC2」が禁止されている可能性が高い

| 項目 | llm_driven_aws_build_test（失敗） | terraform-mfd-intelligent-platform-main（成功） |
|------|-----------------------------------|------------------------------------------------|
| **associate_public_ip_address** | `true`（明示） | 未指定（実質 false／プライベートサブネット） |
| **サブネット** | デフォルト VPC の「1つ目」を取得（public の可能性） | **プライベートサブネット**を明示指定（apne1a/apne1c/apne1d） |
| **VPC** | 同上で取得した vpc_id | 同じ VPC `vpc-0b4f169375170ca0a` を固定で指定 |
| **キーペア** | `aws_key_pair` で新規作成 | `data "aws_key_pair"` で**既存キー名**を参照 |
| **AMI** | `amazon` の AL2023 を data で取得 | **self**（自アカウント）のカスタム AMI を指定 |
| **バックエンド** | なし（ローカル state） | S3 バックエンド（poc-s3-apne1-llma-terraform） |

エラーメッセージは「`ec2:RunInstances` が `network-interface/*` に対して deny」でした。  
組織の SCP では「**パブリック IP 付きの EC2 起動**」や「**特定サブネット以外での RunInstances**」を禁止している可能性があります。  
動いている側は **プライベートサブネット＋公開 IP なし** のため、同じアカウント・同じロールでも apply が通っています。

## 推奨対応

1. **プライベートサブネットを使う**  
   動いているプロジェクトと同じサブネット（例: `subnet-03c2be04cd9ff903c` など）を `main.tf` で指定する。
2. **associate_public_ip_address = false**  
   公開 IP を付けない。
3. **アクセス方法**  
   公開 IP が無いため、SSM Session Manager や踏み台など、動いているプロジェクトと同様の方法で EC2 に接続し、FastAPI には内部から（または ALB 等）アクセスする。

## main.tf の修正内容（反映済み）

- **vpc_id** / **subnet_id** をオプション変数で追加。指定するとその VPC・サブネットを使用し、**associate_public_ip_address = false** で起動する。
- サブネットを指定しない場合は従来どおり（data で取得・公開 IP あり）。

### 実行例（SCP で RunInstances が拒否される場合）

動いているプロジェクトと同じ VPC・プライベートサブネットを指定して apply：

```bash
terraform apply \
  -var="ssh_public_key_path=/home/j0632714/llm_driven_aws_build_test/ssh_public_key.txt" \
  -var="vpc_id=vpc-0b4f169375170ca0a" \
  -var="subnet_id=subnet-0cea8415afe8e63ea"
```

EC2 はプライベートサブネットに立ち、公開 IP は付きません。アクセスは SSM Session Manager や踏み台など、terraform-mfd-intelligent-platform-main と同様の方法で行ってください。
