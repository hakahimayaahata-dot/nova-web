# NOVA WEB demo

日本語の検索＋ページ本文プレビューのサンプルです。

## 機能
- 検索語句を DuckDuckGo に送る
- サーバー側で HTTPS ページを取得して、本文テキストだけを表示する
- HTML/JavaScriptをブラウザ上でそのまま実行しない

## 安全上の制限
このサンプルは任意URLの汎用プロキシではありません。サーバー側リクエスト偽造（SSRF）などの危険を抑えるため、取得先を `example.com` と Wikipedia の公開ドメインに限定しています。内部IPアドレスへの接続も拒否します。リダイレクト先も再検証します。

本番公開する場合は、認証、レート制限、監視、厳格なドメイン許可リスト、HTTPS設定などが必要です。学校や職場のネットワーク制限を回避する用途には使用しないでください。

## 起動方法
Python 3.10 以降を用意し、このフォルダで実行します。

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1

pip install -r requirements.txt
python app.py
```

ブラウザで http://127.0.0.1:5000 を開きます。

## 許可するサイトを増やす場合
`app.py` の `ALLOWED_HOSTS` に、自分が管理しているサイトや取得許可のある公開ドメインだけを追加してください。サブドメインを一括許可する変更は避けてください。
