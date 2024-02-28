## 概要

スプレッドシートで指定した商品及び出品者の Amazon 在庫数を取得し、スプレッドシートに入力します。

## 実行間隔

毎日 JST 06:00 に実行します。

## 設定の編集

### 実行間隔の変更

- `.github/workflows/stock_watcher.yml` L7 を編集

### アカウント情報の変更

GitHub リポジトリ > Settings > Secrets and variables > Actions > Repository secrets から以下の各 secrets を編集（鉛筆マーク）

- `WORKBOOK_KEY`: スプレッドシート（「https://docs.google.com/spreadsheets/d/」以降の文字列）
- `JSON`: サービスアカウント
- `SLACK_WEBHOOK`: Slack エラー通知用 Webhook

## 手動実行方法

定期実行が正常に完了しなかった場合、手動での再実行が可能です。
[アクションのページ](https://github.com/vyper-japan/stock_watcher/actions/workflows/stock_watcher.yml)にアクセスし、
「Run workflow」 > 「Run workflow」をクリックしてください。
再実行してもうまくいかない場合、Slack にてご連絡ください。
