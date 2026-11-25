# My Personal AI — Local Python Engine

Python + Streamlit + Supabase で動く個人用ローカルAIエンジンです。チャット回答の生成にOpenAI・Groq・Geminiなどの生成AIプロバイダーAPIを使用しません。

## ローカルAIエンジンの機能

- 日本語の基本会話・機能ヘルプ
- 安全な算術計算（許可した演算子だけをPython ASTで評価）
- 日本時間の日付・時刻
- Supabaseに保存した長期記憶のキーワード検索
- PDF / DOCX / TXT / MD / CSV / XLSX のテキスト抽出
- 読み込んだ資料からの抽出的な要約（原文から重要文を選ぶ方式）
- 目的別の作業計画テンプレート
- ブラウザー標準の音声読み上げ
- ChromebookのOS音声入力を使ったテキスト入力

## 大切な制限

この初期エンジンはルール・パターン・小さな知識集・記憶検索で動きます。ChatGPTのような大規模言語モデルではありません。未知の質問への自由な文章生成、最新情報のWeb検索、音声の自動文字起こしはできません。回答できない内容は、分からないと明示します。

「生成AIプロバイダーAPIを使わない」という意味であり、Supabaseのクラウドデータベースと通信するためのバックエンドAPI通信は引き続き使います。RenderのホスティングとSupabaseには各サービスのプラン・利用制限があります。

## Render環境変数

- `APP_ACCESS_PASSWORD`: アプリへのアクセスパスワード
- `SUPABASE_URL`: Supabase Project URL
- `SUPABASE_PUBLISHABLE_KEY`: Edge Function呼び出し用の公開可能キー
- `MEMORY_API_TOKEN`: Edge Functionのアプリ専用認証トークン

Supabaseの強いSecret / Service RoleキーはEdge Function内だけに保存し、GitHubやブラウザーへ公開しないでください。

## 実行

```bash
python -m pip install -r requirements.txt
python -m pytest -q
streamlit run app.py
```

## ファイル構成

- `app.py`: Streamlit UI
- `ai_engine.py`: APIを使わないローカルAI処理エンジン
- `agent.py`: 既存UIとの互換用アダプター
- `memory/`: Supabase Edge Function / SQLiteの記憶ストア
- `tools/`: PDF / DOCX / TXT / MD / CSV / XLSXの読み込み
- `tests/`: ローカルAIと既存機能のテスト
- `render.yaml`: Render Blueprint

## 安全設計

- ファイルはテキスト抽出だけを行い、原本をデータベースへ保存しません。
- アップロード文書は信頼されていない入力データとして扱います。
- メール送信、購入、投稿、外部アカウント変更などは実行しません。
- 長期記憶への保存はユーザーが長期記憶タブから明示的に操作します。
- 個人利用向けの簡易パスワードゲートです。複数ユーザー向けには正式な認証とデータ分離が必要です。
