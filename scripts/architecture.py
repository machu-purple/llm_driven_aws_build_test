# architecture.py
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS
from diagrams.aws.network import VPC, PublicSubnet
from diagrams.aws.devtools import Codebuild
from diagrams.aws.storage import S3
from diagrams.aws.security import IAMRole
from diagrams.programming.language import Python

# --- ここを IPAGothic に変更 ---
font_name = "IPAGothic"

graph_attr = {"fontname": font_name}
node_attr = {"fontname": font_name}
edge_attr = {"fontname": font_name}
# -----------------------------

with Diagram(
    "LLM Driven AWS Build Test", 
    show=False, 
    filename="llm_architecture",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr
):
    
    with Cluster("WSL (Development)", graph_attr={"fontname": font_name}):
        agent = Python("agent.py\n(LLM Agent)")
        tf_cli = Codebuild("Terraform CLI")
        app_code = S3("Application Code")

    with Cluster("AWS Cloud", graph_attr={"fontname": font_name}):
        role = IAMRole("Terraform Execution Role")
        
        with Cluster("Target VPC", graph_attr={"fontname": font_name}):
            with Cluster("Public Subnet", graph_attr={"fontname": font_name}):
                chatbot = ECS("Chatbot App")

    # 矢印（エッジ）の定義
    agent >> Edge(label="生成・実行", fontname=font_name) >> tf_cli
    tf_cli >> Edge(label="ロールをAssume", fontname=font_name) >> role
    role >> Edge(label="インフラ構築", fontname=font_name) >> chatbot
    app_code >> Edge(label="デプロイ", fontname=font_name) >> chatbot