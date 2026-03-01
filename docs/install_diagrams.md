# Diagrams インストール

## Diagrams概要

Diagramsは、システムのアーキテクチャ構成図をコード（Python）で記述・生成できるライブラリです。

- 直感的な記述: クラウド（AWS, GCP, Azure等）やオンプレのアイコンを、ノード（点）とエッジ（線）としてコードで繋ぐだけで図が作成できます。
- 効率化: GUIツールを使わず、バージョン管理（Git等）が可能になり、図の修正や共有が容易です。
- 依存: 描画にはGraphvizを使用します。

---

### 手順1 WSL起動

PowerShell
```
wsl
```

---

### 手順2 描画エンジン (Graphviz) のインストール

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

#### Graphvizのインストール

Bash
```
# パッケージリストの更新
sudo apt update
# Graphviz のインストール
sudo apt install -y graphviz
```

---

### 手順3 diagrams のインストール

Bash
```
# 仮想環境(任意)
cd ~/<仮想環境フォルダ>
source .venv/bin/activate

# インストール
python3 -m pip install diagrams
```

#### インストールされたか確認

Bash
```
python3 -m pip list
```
diagramsがあれば成功

### 手順4 日本語フォントのインストール

Bash
```
# IPAフォントのインストール
sudo apt update
sudo apt install -y fonts-ipafont
# フォントを更新
fc-cache -fvr
```
