# GithubにSSH接続

### 1. SSHキー（鍵ペア）を作成

WSLに入る

PowerShell
```
wsl
```

github登録メールアドレス

Bash
```
ssh-keygen -t ed25519 -C "<Name>_<Family name>@jp.honda"
```

- Enter file to save: そのまま Enter（/home/<user>/.ssh/id_ed25519 に保存されます）
- Enter passphrase: 空欄で Enter 2回（パスワードなしにする場合）

### 2. 公開鍵の中身をコピーする

作成された鍵のうち、.pub で終わる方（公開鍵）の中身を表示してコピーします。

Bash
```
cat ~/.ssh/id_ed25519.pub
```
表示される文字列をすべてコピー

### 3. GitHubに公開鍵を登録する

1. GitHubにブラウザでログインし、右上のアイコンから [Settings] を開く。

2. 左メニューの [SSH and GPG keys] をクリック。

3. [New SSH key] ボタンを押す。

4. Title: 適当な名前。

5. Key: 先ほどコピーした文字列を貼り付け。

6. [Add SSH key] を押して保存。

### 4. 接続テストをする

Bash
```
ssh -T git@github.com
```

Are you sure you want to continue connecting (yes/no/[fingerprint])?
⇒yes

Hi <name>! You've successfully authenticated... と出れば成功

### 5. リポジトリの設定を HTTPS から SSH に変更

現在のプロジェクトフォルダに移動し、接続先URLを書き換えます。

Bash
```
cd ~/<プロジェクトフォルダ>
git remote set-url origin git@github.com:<user>/<プロジェクトフォルダ>.git
```

これでSSH経由でpushができる筈