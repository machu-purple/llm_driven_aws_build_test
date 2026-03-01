# LLM 駆動 AWS ビルド（Terraform 生成エージェント）

`scripts/agent.py` が Azure OpenAI で EC2 用の Terraform コードを生成し、`terraform/main.tf` として保存して GitHub に push します。

## 必要な情報の「どこに」「どう書く」「どう使う」

### 1. 環境変数（ローカルで agent.py を動かすとき）

| どこに書く | どう書く | どう使う |
|------------|----------|----------|
| **プロジェクトルートの `.env`** | `.env.example` をコピーして値を埋める（下記） | `scripts/agent.py` が `load_dotenv()` で読み込み、LLM 呼び出し・Git・生成 Terraform のリージョンに利用 |

**手順**

```bash
cp .env.example .env
# .env を編集して実際の値を入れる
```

**主な変数**

- **Azure OpenAI（必須）**  
  `HOZEN_ENDPOINT`, `HOZEN_API_KEY`, `HOZEN__API_VERSION`, `HOZEN_DEPLOYMENT_NAME`  
  → Terraform を生成する LLM の接続に使用。
- **AWS**  
  `AWS_REGION`（例: `ap-northeast-1`）  
  → 生成される Terraform の `provider "aws" { region = "..." }` に反映される。未設定時は `ap-northeast-1`。
- **GitHub（任意）**  
  `REPO_PATH`（既定: `./`）, `REMOTE_NAME`（既定: `origin`）  
  → `main.tf` を commit して push するリポジトリ・リモートの指定。  
  **push の認証**: ローカル実行時は **git の設定**（`git credential` や SSH 鍵）が使われます。GitHub のトークンや URL は .env には書かず、git 側で設定してください。

`.env` は **git に含めない**でください（`.gitignore` に `.env` を追加推奨）。

---

### 2. Terraform を実行するとき（AWS の認証）

生成された `main.tf` を `terraform plan` / `terraform apply` する環境では、**AWS の認証情報**が必要です。

| どこに書く | どう書く | どう使う |
|------------|----------|----------|
| **ローカルで terraform を実行する場合** | 通常どおり `~/.aws/credentials` と `~/.aws/config`、または環境変数 `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`。**`terraform/` ディレクトリに移動して実行** | Terraform の AWS Provider が参照する |
| **GitHub Actions で terraform を実行する場合** | リポジトリの **Settings → Secrets and variables → Actions** に以下を登録 | ワークフロー内で `env` に渡し、`terraform` が利用 |

**GitHub Actions に登録する Secrets の例**

- `AWS_ACCESS_KEY_ID` … IAM のアクセスキー
- `AWS_SECRET_ACCESS_KEY` … IAM のシークレットキー
- （必要なら）`AWS_REGION` … 例: `ap-northeast-1`

ワークフロー例:

```yaml
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  AWS_REGION: ${{ secrets.AWS_REGION }}
run: |
  cd terraform
  terraform init
  terraform apply -auto-approve
```

---

### terraform/main.tf の変数（EC2 が clone するリポジトリ）

`terraform/main.tf` の user_data では、EC2 が **このリポジトリを clone** して `app/` を動かします。次の変数を **実際のリポジトリ URL に合わせて設定**してください。

| 変数 | 説明 | 例 |
|------|------|-----|
| `git_repo_url` | clone する Git の URL | `https://github.com/your-org/llm_driven_aws_build_test.git` |
| `repo_name` | clone でできるディレクトリ名（リポジトリ名） | `llm_driven_aws_build_test` |
| `ssh_public_key_path` | EC2 用 SSH 公開鍵のパス。Terraform の `file()` は `~` を展開しないため、**絶対パス**を渡すこと | `/home/user/.ssh/id_rsa.pub` |
| `vpc_id` | 任意。指定すると、その VPC を使って EC2 を起動する（指定なしの場合は data で自動判定） | `vpc-0b4f169375170ca0a` |
| `subnet_id` | 任意。指定すると、そのサブネットで EC2 を起動し、**公開 IP は付与されない**（`associate_public_ip_address = false`）。指定しない場合は VPC 内の 1 番目のサブネット＋公開 IP あり | `subnet-0cea8415afe8e63ea` |

**`vpc_id` / `subnet_id` をどこで確認するか**

- **このリポジトリでの動作確認に使った値**  
  - `vpc_id = vpc-0b4f169375170ca0a`  
  - `subnet_id = subnet-0cea8415afe8e63ea`  
  これらは、既存プロジェクト `terraform-mfd-intelligent-platform-main` の  
  `accounts/honda-flex-gamma-llma-poc/ec2-sandbox/main.tf` で指定されている VPC / サブネットと同じものです。

- **自分の環境で確認する場合（別アカウント・別環境）**  
  - AWS マネジメントコンソールの **VPC → VPC** 一覧から `vpc-xxxx` 形式の ID を確認して `vpc_id` に指定します。
  - 同じく **VPC → サブネット** 一覧から、使いたいサブネットの ID（`subnet-xxxx`）を確認して `subnet_id` に指定します。
  - ネットワークチームや AWS 管理者から「使ってよい VPC / サブネット」を案内されている場合は、その値をそのまま使ってください。

**terraform plan / apply の実行例（よくあるエラーを防ぐ）**

- **ローカルで単純に試す場合（公開 IP あり／SCP 制約なし想定）**  
  ```bash
  cd terraform
  terraform init
  terraform plan  \
    -var="ssh_public_key_path=/home/あなたのユーザー名/.ssh/id_rsa.pub"
  terraform apply \
    -var="ssh_public_key_path=/home/あなたのユーザー名/.ssh/id_rsa.pub"
  ```

- **このリポジトリで実際に動作確認したコマンド（SCP で公開 IP 付き EC2 が制限されている環境）**  
  事前に `ssh_public_key.txt` に公開鍵を保存しておきます（`.env` の `SSH_PUBLIC_KEY` から書き出してもよい）。

  ```bash
  cd terraform
  terraform init
  terraform apply \
    -var="ssh_public_key_path=/home/j0632714/llm_driven_aws_build_test/ssh_public_key.txt" \
    -var="vpc_id=vpc-0b4f169375170ca0a" \
    -var="subnet_id=subnet-0cea8415afe8e63ea"
  ```

  この指定をすると、`subnet_id` を明示しているため **公開 IP なし（プライベートサブネット）** で EC2 が起動し、  
  組織の SCP による「公開 IP 付き EC2 の起動禁止」に引っかかりにくくなります。

- **terraform/main.tf の default を編集する** … `variable "git_repo_url"` の `default` を自分の URL に変更する。
- **コマンドで渡す** … `terraform apply -var 'git_repo_url=https://github.com/...'`
- **terraform/terraform.tfvars に書く** … `terraform/` ディレクトリに `terraform.tfvars` を作り、`git_repo_url = "https://..."` を記述する。

プライベートリポジトリの場合は、EC2 から clone できるよう SSH 鍵やトークンを user_data で設定する必要があります。

---

### 3. まとめ

- **agent.py 用**: ルートの `.env` に Azure 必須 + AWS（`AWS_REGION`）+ 任意で GitHub（`REPO_PATH`, `REMOTE_NAME`）を記載。Git の認証は git の設定で行う。
- **Terraform 実行用**: 実行する環境（ローカル or GitHub Actions）に合わせて、AWS の認証（credentials または Secrets）とリージョンを設定する。

詳細な変数一覧は **`.env.example`** を参照してください。

## 実行方法

### 1. 準備（初回のみ）

```bash
# プロジェクトルートに移動
cd /home/j0632714/llm_driven_aws_build_test

# 仮想環境を作る（推奨）
python3 -m venv .venv
source .venv/bin/activate   # Windows なら .venv\Scripts\activate

# 依存のインストール
pip install -r requirements.txt

# .env がまだなければ .env.example をコピーして編集
cp .env.example .env
# .env に HOZEN_ENDPOINT, HOZEN_API_KEY などを入れる
```

### 2. 実行

```bash
# プロジェクトルートで
python scripts/agent.py
```

- LLM が EC2 用 Terraform を生成 → `terraform/main.tf` に保存  
- 同じリポジトリに commit & push（`origin` へ）  
- その後、手動または GitHub Actions で `terraform plan` / `apply` を実行して AWS に反映

**注意**: push するには git の認証（SSH または credential）が済んでいる必要があります。未設定の場合は `git remote -v` と `git push` を手動で試してから `scripts/agent.py` を実行してください。

## リポジトリ構成

```
.
├── scripts/
│   ├── agent.py          … Terraform 生成＆GitHub push
│   └── architecture.py   … アーキテクチャ関連スクリプト
├── terraform/
│   ├── main.tf           … agent が生成する Terraform（EC2 など）
│   ├── terraform.tfstate … Terraform の状態ファイル（git に含めない）
│   └── .terraform/       … Terraform のプラグインキャッシュ（git に含めない）
├── app/                  … デプロイ対象の FastAPI アプリ
├── docs/                 … ドキュメント
│   └── images/           … 画像ファイル
├── requirements.txt      … agent.py 実行用の Python 依存（openai, python-dotenv, GitPython）
├── .env.example          … 環境変数のサンプル（AWS / GitHub / Azure）
└── .env                  … 実際の値（git に含めない）
```
