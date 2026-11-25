# My Personal AI（Chromebook / Windows / Mac 対応）

Python + Streamlit + OpenAI Responses API + Supabase で作る、個人用AIエージェントの初期版です。開発はブラウザ上のGitHub Codespacesで行えます。LinuxをChromebookにインストールする必要はありません。

## できること

- 日本語チャット
- OpenAI Responses APIによる回答
- Web検索（OpenAIの組み込み web_search ツール）
- 長期記憶（Supabase Edge Function。未設定の開発時はSQLite）
- 会話履歴（個人用固定IDで再読み込み後も同じ履歴を表示）
- PDF / DOCX / TXT / MD / CSV / XLSX のテキスト抽出と分析
- ブラウザのマイク入力、OpenAI音声文字起こし、Chrome標準の音声読み上げ
- Planner / Worker / Reviewer の3役によるマルチエージェント処理
- 個人利用向けの簡易パスワードゲート

## 重要な制限・安全設計

- この初期版は個人利用向けです。複数ユーザー向けに公開する場合は、Supabase Auth、ユーザーIDに基づくRLSポリシー、ユーザーごとのデータ分離を実装してください。
- アプリは情報収集・分析・文章作成を行います。メール送信、購入、投稿、データ削除などの外部への書き込み操作は実行しません。
- アップロードされたファイルはテキスト抽出後にAIへ送られます。原本ファイルはデータベースに保存しません。機密情報をアップロードしないでください。
- APIキーはコードに書かず、Streamlit Secretsだけに保存してください。
- SupabaseのSecret / Service RoleキーはRLSを迂回する強いキーです。サーバー側Secrets以外に置かず、GitHubやブラウザへ公開しないでください。
- Streamlit Community Cloudで公開する前に APP_ACCESS_PASSWORD を設定してください。
- SQLiteはローカル試作用です。クラウドの一時ファイルシステムでは永続保存が保証されないため、公開後はSupabaseを設定してください。
- OpenAI API、音声、Web検索、ホスティングの利用は別料金になる場合があります。使用量上限を設定してください。

## ファイル構成

- app.py: Streamlit画面
- agent.py: AIの計画・実行・確認
- audio_tools.py: 音声文字起こし（回答読み上げはブラウザ標準機能）
- config.py: Secretsと環境変数
- memory/: Supabase / SQLiteの記憶ストア
- tools/: ファイル読み込み
- supabase/migrations/: DBテーブル定義
- tests/: 基本テスト
- .devcontainer/devcontainer.json: Codespaces用Python環境
- requirements.txt: Python依存ライブラリ

## ブラウザだけで開発する手順

1. GitHubリポジトリはPrivateに設定することをおすすめします。
2. GitHubリポジトリの Code → Codespaces → Create codespace on main を選びます。
3. CodespacesがPython環境と8501番ポートを準備します。
4. ターミナルで python -m pip install -r requirements.txt を実行します。
5. python -m pytest -q でテストします。
6. streamlit run app.py --server.address 0.0.0.0 で起動します。
7. Portsタブで8501番ポートを開きます。

## Supabaseの設定

1. 新しいSupabaseプロジェクトを作成します。既存の別用途プロジェクトは流用しないでください。
2. SQL Editorで supabase/migrations/0001_init.sql を実行します。
3. SupabaseのProject URLとPublishable Keyを取得します。強いSecretキーはEdge Function内でのみ使用します。
4. Streamlit Community CloudのApp settings → Secretsに次を登録します。

OPENAI_API_KEY = "..."
OPENAI_MODEL = "gpt-6.2-sol"
APP_ACCESS_PASSWORD = "..."
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
MEMORY_API_TOKEN = "サーバーが保持するランダムな認証トークン"

## Renderへの公開

1. RenderでGitHubリポジトリを選びます。
2. `render.yaml` のBlueprint、またはPython Web Serviceとして作成します。
3. `APP_ACCESS_PASSWORD` と `MEMORY_API_TOKEN` をSecretsとして設定します。
4. OpenAI APIキーはRenderの環境変数に置くか、ログイン後の専用入力欄に入力します。専用入力欄を使う場合、キーは現在のStreamlitセッションのメモリにだけ保持されます。
5. `SUPABASE_URL` と `SUPABASE_PUBLISHABLE_KEY` は設定済みの値を使います。

## Streamlit Community Cloudへの公開

1. GitHubにプッシュしたリポジトリをStreamlit Community Cloudに接続します。
2. app.py をエントリポイントとして選びます。
3. App settings → Secretsに上記の値を設定します。
4. APP_ACCESS_PASSWORDを設定し、ログインできることを確認します。OpenAI APIキーはRenderの環境変数に設定するか、ログイン後の専用パスワード入力欄でそのセッションだけに設定できます。

## テスト

python -m pip install -r requirements.txt
python -m pytest -q

## 環境変数

- OPENAI_API_KEY: 必須。OpenAI APIキー
- OPENAI_MODEL: 任意。既定値 gpt-6.2-sol
- APP_ACCESS_PASSWORD: 必須。個人利用向けアクセスパスワード
- SUPABASE_URL: クラウドで推奨。Supabase Project URL
- SUPABASE_PUBLISHABLE_KEY: Edge Function呼び出し用の公開可能なキー
- MEMORY_API_TOKEN: Edge Functionの単一アプリ用認証トークン（Renderの環境変数に保存）

モデル・APIの使用可否・価格は変わることがあるため、OpenAI Platformで最新情報を確認してください。
