# AWS diagram-as-code インストール

## AWS diagram-as-code 概要

AWSの構成図を、手書きやツール操作ではなくPythonなどのプログラミングコード（Python等）で作成・管理する手法のことです。

「Diagrams」といったライブラリを使い、リソース間の接続をコードで定義することで、図を自動生成します。

- メリット: Gitでのバージョン管理が可能、修正が容易、インフラの実態（IaC）と図の乖離を防ぎやすい。
- 特徴: 構成変更時にコードを書き換えるだけで、美しい図を即座に再出力できます。
- AWS CDKはGoをサポートしており、インフラ構成をGoで定義できます。これに cdk-dia などのツールを組み合わせることで、Goで書いた実際のインフラ定義コードから、そのまま構成図を自動抽出・生成することが可能です。

---

## 手順1 WSLに入る

PowerShell
```
wsl
```

---

## 手順2 GOインストール

### Proxyをセッティング

#### 現在のProxyを確認

Bash
```
env | grep -i proxy
```

#### Proxyが入っていない場合は入れる

Bash
```
export http_proxy="http://j0<職番>:<統合認証PASS>@proxy01.hm.jp.honda.com:8080"
export https_proxy="http://j0<職番>:<統合認証PASS>@proxy01.hm.jp.honda.com:8080"
```

### もし古いバージョンが入っている場合は、競合を避けるために削除

Bash
```
sudo rm -rf /usr/local/go
```

### Go をダウンロードして展開

Bash
```
# ダウンロード（バージョンは適宜最新に読み替えてください）
curl -OL https://go.dev/dl/go1.23.0.linux-amd64.tar.gz

# /usr/local に展開
sudo tar -C /usr/local -xzf go1.23.0.linux-amd64.tar.gz
```

### Pathを通す

~/.bashrc（または ~/.zshrc）の末尾に以下の行を追加して、どこからでも go コマンドが使えるようにします。

Bash
```
# ファイルの末尾に追記
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc

# 設定を反映
source ~/.bashrc
```

### 正しくインストールされたか確認

Bash
```
go version
```

go version go1.23.0 linux/amd64 のように表示されれば成功

---

## 手順3 Go で awsdac をインストールする

Bash
```
go install github.com/awslabs/diagram-as-code/cmd/awsdac@latest
```

#### awsdacがインストールされたか確認

Bash
```
awsdac --help
```

コマンドについての説明がでてきたら成功