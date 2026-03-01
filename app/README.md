# チャットボット（サンプル）

Azure OpenAI を使った簡易チャットボットです。FastAPI + 静的フロントエンドで動作します。

## セットアップ

1. 仮想環境の作成と有効化（任意）

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   ```

2. 依存関係のインストール

   ```bash
   pip install -r requirements.txt
   ```

3. 環境変数の設定

   プロジェクトルートに `.env` を作成し、`.env.example` を参考に以下を設定してください。

   - `API_TYPE=HOZEN`
   - `HOZEN_ENDPOINT` … Azure OpenAI のエンドポイントURL
   - `HOZEN_API_KEY` … API キー
   - `HOZEN__API_VERSION` … API バージョン
   - `HOZEN_DEPLOYMENT_NAME` … デプロイ名（未設定時は `gpt-4o-mini`）

## 起動方法

プロジェクトルートで以下を実行します。

**AWS 上で起動し、ローカル PC からアクセスする場合（推奨）**

- `--host 0.0.0.0` で全インターフェースにバインドし、外部からの接続を受け付けます。
- AWS のセキュリティグループで、インバウンドに TCP 8000 を許可してください。

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- **ローカル PC のブラウザ**で次の URL を開いてチャット画面にアクセスします。  
  **http://\<AWS のパブリック IP または DNS\>:8000**
- 例: EC2 のパブリック IP が `203.0.113.10` の場合 → `http://203.0.113.10:8000`

本番運用では `--reload` を外して起動してください。

**同一マシンだけで使う場合**

- ブラウザで http://localhost:8000 を開きます。
