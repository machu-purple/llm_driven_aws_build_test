"""
自律型 AWS 構築エージェント（Azure OpenAI Responses API + native_shell / file_system + interrupt 対応）。

・モデルがファイル操作・シェル実行のツールを持ち、1セッション内で
  「コマンド実行 → エラー確認 → 修正」を自律的に行う。
・Python 側は進行イベントの監視と、必要時の interrupt への応答のみ行う。
"""
import os
from openai import AzureOpenAI
from git import Repo
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    """環境変数を取得し、CRLF などによる余分な文字を除去する。"""
    val = os.getenv(key, default)
    return (val or "").strip()


# --- Azure OpenAI 設定 ---
# エンドポイント: https://<リソース名>.openai.azure.com/ の形式（末尾スラッシュなしでも可）
azure_endpoint = _env("HOZEN_ENDPOINT")
api_key = _env("HOZEN_API_KEY")
# デプロイ名（Azure ポータルで作成したデプロイメント名）
deployment_name = _env("HOZEN_DEPLOYMENT_NAME")
# API バージョン（Responses API は 2024-05-01-preview 以降を推奨）
api_version = _env("HOZEN__API_VERSION")

# --- リポジトリ・AWS 設定 ---
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
remote_name = _env("REMOTE_NAME") or "origin"
aws_region = _env("AWS_REGION")
LLM_TIMEOUT = int(_env("LLM_TIMEOUT") or "180")


def get_git_remote_info():
    """現在のリポジトリの origin URL とリポジトリ名を取得。SSH は HTTPS に変換する。"""
    try:
        repo = Repo(repo_path)
        origin = repo.remote(name=remote_name)
        url = origin.url.strip()
        if url.startswith("git@"):
            url = url.replace(":", "/", 1).replace("git@", "https://")
        if url.endswith(".git"):
            repo_name = url.rsplit("/", 1)[-1][:-4]
        else:
            repo_name = url.rsplit("/", 1)[-1]
        return url, repo_name
    except Exception:
        return None, "llm_driven_aws_build_test"


def _build_agent_system_prompt() -> str:
    """自律エージェント用のシステムプロンプト（Terraform ルール・アプリ概要を含む）。"""
    git_url, git_repo_name = get_git_remote_info()
    if git_url:
        git_repo_instruction = f'variable "git_repo_url" の default は "{git_url}" とすること。variable "repo_name" の default は "{git_repo_name}" とすること。'
    else:
        git_repo_instruction = 'variable "git_repo_url" と variable "repo_name" を必ず定義すること。git_repo_url の default は "https://github.com/YOUR_USER/llm_driven_aws_build_test.git" のようなプレースホルダーでよい。repo_name の default は "llm_driven_aws_build_test"。'

    return f"""
あなたは優秀なインフラエンジニアです。AWS 構築エージェントとして、アプリ解析から Terraform 作成・検証（terraform init / plan）まで自律的に完結させてください。

アプリの概要:
- FastAPI + 静的フロントエンド（backend/main.py がエントリ、uvicorn で port 8000）
- 起動コマンド: uvicorn backend.main:app --host 0.0.0.0 --port 8000（app フォルダがカレント）
- 依存: requirements.txt、.env（Azure OpenAI 用の環境変数）
- 必ず EC2 上に構築すること（ECS / App Runner / Lambda は使わない）。EC2 インスタンス、セキュリティグループ（port 8000 許可）、user_data でアプリ起動まで含めること。
- AWS のリージョンは {aws_region} を使用すること（provider の region に指定すること）。

user_data で Git からデプロイする場合の必須ルール:
- リポジトリは「このプロジェクト全体」を clone する想定。アプリはリポジトリ直下の app/ にある。
- {git_repo_instruction}
- user_data 内では「git clone ${{var.git_repo_url}}」でリポジトリ全体を clone し、「cd ${{var.repo_name}}/app」で app に移動すること。
- その後のパスはすべて /home/appuser/${{var.repo_name}}/app を基準にすること。

Terraform の正しい書き方（必ず守ること）:
- VPC: data "aws_vpc" "default" {{ default = true }} は使用禁止。data "aws_vpcs" で ID を取得し、default が無ければ利用可能な VPC の 1 件目を使うこと。locals で local.vpc_id を設定し、aws_subnets の filter の values と aws_security_group の vpc_id は local.vpc_id を参照すること。
- サブネット: AWS provider 5.x では aws_subnet_ids は廃止。data "aws_subnets" の filter の values は [local.vpc_id]。aws_instance の subnet_id は tolist(data.aws_subnets.default.ids)[0] 等で取得すること。
- .env: user_data 内で .env が無いときだけ .env.example を .env にコピーすること。
- SSH 公開鍵: variable "ssh_public_key_path" は必須にし、description に「実行時に -var=ssh_public_key_path=/絶対パス/id_rsa.pub を渡すこと」と書くこと。
- heredoc 内のシェル変数（APP_USER 等）は HCL 補間と衝突しないよう $${{ "APP_USER" }} のように $ を二重にすること。
- optional な variable "vpc_id" と "subnet_id" (default = null) を定義し、指定時はそれを使い、subnet_id 指定時は associate_public_ip_address = false とすること。

構築の途中で「サブネットはどうしますか？」など確認が必要な場合は、interrupt でユーザーに問いかけてください。
"""


def _responses_client() -> AzureOpenAI | None:
    """Azure OpenAI の Responses API 用クライアント。api_version をクエリに付与する。"""
    if not azure_endpoint or not api_key:
        return None
    # Responses API は /openai/v1/ パスで提供されるため base_url を明示
    base_url = f"{azure_endpoint.rstrip('/')}/openai/v1"
    return AzureOpenAI(
        api_key=api_key,
        base_url=base_url,
        api_version=api_version,
        timeout=LLM_TIMEOUT,
    )


def _autonomous_tools():
    """Responses API に渡すツール。Azure のサポート値: shell, code_interpreter, file_search, ..."""
    return [
        {"type": "shell"},
    ]


def _handle_interrupt(stream, event, prompt_suffix: str = "回答入力: "):
    """interrupt イベント時にユーザー入力を取り、submit_tool_outputs で再開する（API が対応している場合）。"""
    content = getattr(event, "content", None) or getattr(event, "message", str(event))
    if isinstance(content, list):
        content = " ".join(
            getattr(c, "text", str(c)) for c in content if hasattr(c, "text")
        )
    print(f"\n\n [確認が必要] {content}", flush=True)
    user_answer = input(prompt_suffix)
    call_id = getattr(event, "call_id", None)
    if call_id and hasattr(stream, "submit_tool_outputs"):
        stream.submit_tool_outputs(outputs=[{"call_id": call_id, "output": user_answer}])
    else:
        print("（この API では submit_tool_outputs が利用できません。入力は無視されます。）", flush=True)


def run_autonomous_build_agent(project_path: str, requirements: str) -> tuple[bool, str]:
    """
    自律型エージェントを起動する。モデルが shell ツールでコマンド実行・ファイル操作を行い、
    エラー時は自ら修正する。interrupt 時はユーザーに問いかけ再開する。
    成功時は (True, 最終メッセージ)、失敗時は (False, エラー内容)。
    """
    client = _responses_client()
    if not client:
        return False, "AZURE_OPENAI_ENDPOINT と AZURE_OPENAI_API_KEY が未設定です。"

    print(f"自律型エージェントを起動中（{deployment_name}）...", flush=True)
    system_content = _build_agent_system_prompt()
    user_content = f"要件: {requirements}\nプロジェクトパス: {project_path}"

    input_items = [
        {"role": "system", "content": [{"type": "input_text", "text": system_content}]},
        {"role": "user", "content": [{"type": "input_text", "text": user_content}]},
    ]

    response = client.responses.create(
        model=deployment_name,
        input=input_items,
        reasoning={"effort": "medium"},
        tools=_autonomous_tools(),
        stream=True,
        timeout=LLM_TIMEOUT,
    )

    final_message = ""
    did_print_reasoning_label = False
    did_print_output_label = False

    for event in response:
        event_type = getattr(event, "type", None) or ""
        if event_type in ("reasoning.delta", "response.reasoning_text.delta"):
            if not did_print_reasoning_label:
                print("\n[推論]", flush=True)
                did_print_reasoning_label = True
            delta = getattr(event, "delta", "") or ""
            print(delta, end="", flush=True)
        elif event_type == "response.output_text.delta":
            if not did_print_output_label:
                print("\n[出力]", flush=True)
                did_print_output_label = True
            delta = getattr(event, "delta", "") or ""
            print(delta, end="", flush=True)
        elif event_type == "interrupt":
            _handle_interrupt(response, event)
        elif event_type in ("message.done", "response.completed"):
            if event_type == "response.completed" and hasattr(event, "response"):
                try:
                    out = getattr(event.response, "output", None) or []
                    for item in (out if isinstance(out, list) else [out]):
                        for c in getattr(item, "content", []) or []:
                            if getattr(c, "type", None) == "output_text" and hasattr(c, "text"):
                                final_message += (c.text or "")
                except Exception:
                    pass
            print("\n\n✅ 構築および検証が完了しました。", flush=True)
            if final_message:
                print("--- 最終レポート ---", flush=True)
                print(final_message, flush=True)
            return True, final_message
        elif "tool_call" in event_type or event_type == "response.function_call_arguments.done":
            exit_code = getattr(event, "exit_code", None)
            if exit_code is not None and exit_code != 0:
                print(f"\n❌ [ツール] エラー検知。モデルが修正を検討中... (Exit Code: {exit_code})", flush=True)
            elif exit_code is not None and exit_code == 0:
                print("\n🔧 [ツール] 実行完了 (exit 0)", flush=True)

    return False, final_message or "ストリームが終了しましたが response.completed が受信されていません。"


def push_to_github(file_name: str, content: str, commit_message: str) -> None:
    """terraform/ に保存し、Git add / commit / push する。"""
    terraform_dir = os.path.join(repo_path, "terraform")
    os.makedirs(terraform_dir, exist_ok=True)
    file_path = os.path.join(terraform_dir, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    repo = Repo(repo_path)
    git_file_path = os.path.join("terraform", file_name)
    repo.git.add(git_file_path)
    repo.index.commit(commit_message)
    origin = repo.remote(name=remote_name)
    origin.push()
    print(f"Successfully pushed {git_file_path} to GitHub!")


if __name__ == "__main__":
    requirements = "appフォルダのFastAPIアプリをEC2にデプロイするTerraformコードを書いて。terraform init と terraform plan で検証まで完了すること。"

    success, result = run_autonomous_build_agent(repo_path, requirements)

    if success:
        tf_path = os.path.join(repo_path, "terraform", "main.tf")
        if os.path.isfile(tf_path):
            with open(tf_path, "r", encoding="utf-8") as f:
                tf_content = f.read()
        else:
            tf_content = result if isinstance(result, str) else ""
        if tf_content.strip():
            print("\nGitHubへPush中...", flush=True)
            push_to_github("main.tf", tf_content, "Add Terraform for app deployment to AWS via AI Agent")
        print("完了！GitHub Actionsの動きを確認してください。", flush=True)
    else:
        print("\nエラーが解消されなかったため、GitHub への Push は行いません。", flush=True)
