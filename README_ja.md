# My Personal AI — API-free Python Agent

Python + Streamlit + Supabase で動く個人用ルールベースAIエージェントです。チャットの回答生成にOpenAI・Groq・Geminiなどの生成AIプロバイダーAPIを使いません。

## できること

- 日本語の基本会話・ヘルプ
- ASTの許可リストを使った安全な算術計算
- 長さ・重さ・容量の単位変換
- 日本時間の日付・時刻
- Supabaseに保存した長期記憶のキーワード検索
- PDF / DOCX / TXT / MD / CSV / XLSX のテキスト抽出
- 資料内の関連文検索と抽出的な要約
- 目的別の作業計画と、Supabase保存型の簡易タスク一覧
- 文字数・英数字単語数の確認
- 小さな内蔵知識ベースの検索
- ブラウザー標準の音声読み上げ、Chromebook OS音声入力

## 重要な制約

このエンジンはルール・パターン・検索・小さな知識ベースで動くAIエージェントです。大規模言語モデルではないため、ChatGPTのような自由な文章生成、未知の質問への推論、最新Web検索、音声の自動文字起こしはできません。回答できないことは「未対応」と示します。

AIの回答生成に生成AIプロバイダーAPIは使いません。一方、会話・長期記憶・タスクを保存するSupabaseとの通信は継続します。RenderのホスティングとSupabaseには各サービスのプラン・制限があります。

## Render環境変数

- `APP_ACCESS_PASSWORD`: アプリのアクセスパスワード
- `SUPABASE_URL`: Supabase Project URL
- `SUPABASE_PUBLISHABLE_KEY`: Edge Function呼び出し用の公開可能キー
- `MEMORY_API_TOKEN`: Edge Functionのアプリ専用認証トークン

Supabaseの強いSecret / Service RoleキーはEdge Function内だけに保存し、GitHubやRenderのブラウザー側へ公開しないでください。

## 実行・テスト

```bash
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
streamlit run app.py
```

## 安全設計

- ファイルはテキスト抽出だけを行い、原本をDBへ保存しません。
- アップロード文書は信頼されていない入力データとして扱います。
- 任意のPythonコードは実行しません。メール送信、購入、投稿、外部アカウント変更なども実行しません。
- 長期記憶への保存は、利用者が長期記憶タブから明示的に操作します。
- 個人利用向けの簡易パスワードゲートです。複数ユーザー向けには正式な認証とデータ分離が必要です。
