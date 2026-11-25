from __future__ import annotations

import hmac
import json

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

from agent import run_agent_task
from audio_tools import speech_to_text
from config import get_setting, openai_api_key
from memory.store import MemoryStore
from tools.file_reader import extract_uploaded_file

st.set_page_config(
    page_title="My Personal AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {max-width: 1180px; padding-top: 1.7rem;}
      [data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.18);}
    </style>
    """,
    unsafe_allow_html=True,
)


def authenticate() -> bool:
    """Simple single-owner password gate for a private personal app."""
    expected = str(get_setting("APP_ACCESS_PASSWORD", "")).strip()
    if not expected:
        st.error("APP_ACCESS_PASSWORD を Streamlit Secrets に設定してください。")
        st.stop()

    if st.session_state.get("authenticated") is True:
        return True

    st.title("🔐 My Personal AI")
    entered = st.text_input("アクセスパスワード", type="password")
    if st.button("ログイン", type="primary", use_container_width=True):
        if hmac.compare_digest(entered, expected):
            st.session_state.authenticated = True
            st.rerun()
        st.error("パスワードが違います。")
    st.info("個人利用向けの簡易認証です。複数ユーザー向けには正式な認証機能が必要です。")
    return False


if not authenticate():
    st.stop()

api_key = openai_api_key() or st.session_state.get("runtime_openai_api_key")
if not api_key:
    st.title("My Personal AI")
    st.warning("OpenAI APIキーがまだ設定されていません。")
    st.write(
        "OpenAI APIキーはこの画面のパスワード入力欄に直接入力できます。"
        "キーは現在のブラウザーセッションのメモリ内だけで使い、"
        "会話履歴・データベース・GitHubには保存しません。"
    )
    st.link_button(
        "OpenAI APIキー管理ページ",
        "https://platform.openai.com/api-keys",
        use_container_width=True,
    )
    with st.form("openai_key_form"):
        entered_key = st.text_input("OpenAI APIキー（sk- から始まるキー）", type="password")
        submit_key = st.form_submit_button("このセッションで接続", type="primary")
    if submit_key:
        if not entered_key.startswith("sk-") or len(entered_key) < 20:
            st.error("APIキーの形式を確認してください。キー全文はチャットに送らないでください。")
        else:
            st.session_state.runtime_openai_api_key = entered_key
            st.success("このセッションにAPIキーを設定しました。")
            st.rerun()
    st.stop()

client = OpenAI(api_key=api_key)
store = MemoryStore.from_settings()

# Single-owner ID: chat history remains available after reloads and on other devices.
if "session_id" not in st.session_state:
    st.session_state.session_id = "personal-owner-default"
for key, default in {
    "uploaded_context": "",
    "uploaded_name": "",
    "latest_answer": "",
    "last_plan": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.title("🧠 My Personal AI")
    st.caption("Chromebook / Windows / Mac 対応")
    use_web_search = st.toggle("Web検索を使う", value=True)
    use_multi_agent = st.toggle(
        "複数AIで計画・実行・確認",
        value=False,
        help="有効にすると複数回APIを呼ぶため、利用料金が増える場合があります。",
    )
    speak_answers = st.toggle("回答を音声で読み上げる", value=False)
    st.caption(f"AIモデル: {get_setting('OPENAI_MODEL', 'gpt-6.2-sol')}")
    st.caption(f"記憶保存先: {store.backend_name}")
    if store.backend_name == "SQLite（ローカル試作用）":
        st.warning("クラウド公開後はSupabaseを設定してください。")
    if st.button("ログアウト", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("My Personal AI")
st.caption("会話・長期記憶・Web検索・ファイル分析・音声・複数AI")

chat_tab, files_tab, memory_tab, setup_tab = st.tabs(
    ["💬 チャット", "📎 ファイル・音声", "🧠 長期記憶", "⚙️ 接続状態"]
)

with chat_tab:
    try:
        messages = store.get_messages(st.session_state.session_id, limit=60)
    except Exception as exc:
        st.error(f"会話履歴を読み込めませんでした: {exc}")
        messages = []

    for item in messages:
        role = item.get("role", "assistant")
        if role in {"user", "assistant"}:
            with st.chat_message(role):
                st.markdown(item.get("content", ""))

    with st.form("chat_form", clear_on_submit=True):
        prompt = st.text_area("メッセージ", placeholder="AIに話しかけてください", height=100)
        send = st.form_submit_button("送信", type="primary", use_container_width=True)

    if send and prompt.strip():
        try:
            store.add_message(st.session_state.session_id, "user", prompt.strip())
            memories = store.get_memories(limit=12)
            history = store.get_messages(st.session_state.session_id, limit=12)
            with st.spinner("AIエージェントが考えています…"):
                result = run_agent_task(
                    client=client,
                    user_request=prompt.strip(),
                    history=history[:-1],
                    memories=memories,
                    document_context=st.session_state.uploaded_context,
                    use_web_search=use_web_search,
                    use_multi_agent=use_multi_agent,
                )
            answer = result["answer"]
            store.add_message(st.session_state.session_id, "assistant", answer)
            st.session_state.latest_answer = answer
            st.session_state.last_plan = result.get("plan", [])
            st.rerun()
        except Exception as exc:
            st.error(f"処理中にエラーが発生しました: {exc}")

    if st.session_state.last_plan:
        with st.expander("今回のAI作業計画を見る", expanded=True):
            for index, step in enumerate(st.session_state.last_plan, start=1):
                st.markdown(f"{index}. {step}")

    if st.session_state.latest_answer and speak_answers:
        st.caption("音声はChromeなどのブラウザ読み上げ機能で生成されます（AI音声）。")
        speech_text = json.dumps(st.session_state.latest_answer[:4000], ensure_ascii=False)
        components.html(
            f"""
            <div style="display:flex;gap:8px;align-items:center;font-family:system-ui">
              <button id="speak" style="padding:10px 14px;border:0;border-radius:10px;background:#61D6B5;color:#09211b;font-weight:600">
                ▶ 音声で再生
              </button>
              <button id="stop" style="padding:10px 14px;border:1px solid #777;border-radius:10px;background:transparent;color:inherit">
                ■ 停止
              </button>
              <span id="speech-status" style="font-size:12px;opacity:.75"></span>
            </div>
            <script>
              const speechText = {speech_text};
              const status = document.getElementById("speech-status");
              document.getElementById("speak").addEventListener("click", () => {{
                if (!("speechSynthesis" in window)) {{
                  status.textContent = "このブラウザは音声読み上げに対応していません。";
                  return;
                }}
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(speechText);
                utterance.lang = "ja-JP";
                utterance.rate = 1.0;
                utterance.onstart = () => status.textContent = "再生中";
                utterance.onend = () => status.textContent = "再生完了";
                utterance.onerror = () => status.textContent = "再生できませんでした";
                window.speechSynthesis.speak(utterance);
              }});
              document.getElementById("stop").addEventListener("click", () => {{
                if ("speechSynthesis" in window) window.speechSynthesis.cancel();
                status.textContent = "停止しました";
              }});
            </script>
            """,
            height=65,
        )

with files_tab:
    st.subheader("ファイル分析")
    uploaded = st.file_uploader(
        "PDF / DOCX / TXT / MD / CSV / XLSX",
        type=["pdf", "docx", "txt", "md", "csv", "xlsx"],
        help="ファイルはテキスト抽出後にAIへ送ります。原本はDBに保存しません。",
    )
    if uploaded is not None and st.button("ファイルを読み込む", type="primary"):
        try:
            st.session_state.uploaded_context = extract_uploaded_file(
                uploaded.name, uploaded.getvalue()
            )
            st.session_state.uploaded_name = uploaded.name
            st.success(f"{uploaded.name} を読み込みました。チャットで質問できます。")
        except Exception as exc:
            st.error(f"ファイルを読み込めませんでした: {exc}")

    if st.session_state.uploaded_context:
        st.info(f"分析対象: {st.session_state.uploaded_name}")
        with st.expander("抽出したテキストを確認"):
            st.text(st.session_state.uploaded_context[:12000])
        if st.button("ファイルを解除"):
            st.session_state.uploaded_context = ""
            st.session_state.uploaded_name = ""
            st.rerun()

    st.divider()
    st.subheader("音声入力")
    audio = st.audio_input("マイクで話す", sample_rate=16000)
    if audio is not None and st.button("音声を文字に変換"):
        try:
            transcript = speech_to_text(client, audio.getvalue())
            st.session_state.transcript_draft = transcript
        except Exception as exc:
            st.error(f"音声を変換できませんでした: {exc}")

    if "transcript_draft" in st.session_state:
        st.text_area("文字起こし結果（編集できます）", key="transcript_draft", height=120)
        st.info("内容をコピーしてチャット欄に貼り付けてください。")

with memory_tab:
    st.subheader("長期記憶")
    st.write("AIに覚えておいてほしい情報だけを明示的に保存します。")
    with st.form("memory_form", clear_on_submit=True):
        category = st.selectbox("カテゴリ", ["好み", "目標", "プロジェクト", "設定", "その他"])
        memory_text = st.text_area("記憶する内容")
        save_memory = st.form_submit_button("記憶に保存", type="primary")
    if save_memory and memory_text.strip():
        try:
            store.add_memory(category, memory_text.strip())
            st.success("記憶に保存しました。")
            st.rerun()
        except Exception as exc:
            st.error(f"保存できませんでした: {exc}")

    try:
        saved = store.get_memories(limit=100)
        if not saved:
            st.info("まだ記憶はありません。")
        for item in saved:
            with st.container(border=True):
                st.caption(f"{item.get('category', 'その他')} ・ {item.get('created_at', '')}")
                st.write(item.get("content", ""))
                if st.button("この記憶を削除", key=f"delete_memory_{item['id']}"):
                    store.delete_memory(str(item["id"]))
                    st.rerun()
    except Exception as exc:
        st.error(f"記憶を読み込めませんでした: {exc}")

with setup_tab:
    st.subheader("接続状況")
    st.write("APIキーやDB接続情報は、コードではなくホスティング先のSecretsに設定してください。")
    st.table(
        [
            {"項目": "OpenAI APIキー", "状態": "環境変数・セッションで設定済み" if api_key else "未設定"},
            {"項目": "Supabase URL", "状態": "設定済み" if get_setting("SUPABASE_URL") else "未設定"},
            {"項目": "Supabase記憶API", "状態": "設定済み" if (get_setting("SUPABASE_PUBLISHABLE_KEY") and get_setting("MEMORY_API_TOKEN")) else "未設定"},
            {"項目": "アクセスパスワード", "状態": "設定済み" if get_setting("APP_ACCESS_PASSWORD") else "未設定"},
        ]
    )
    st.markdown(
        """
        Renderの環境変数:
        - APP_ACCESS_PASSWORD
        - OPENAI_API_KEY（任意。環境変数に置かない場合は、ログイン後の専用入力欄を使用）
        - OPENAI_MODEL（既定値: gpt-6.2-sol）
        - SUPABASE_URL
        - SUPABASE_PUBLISHABLE_KEY
        - MEMORY_API_TOKEN

        Supabaseの強いSecretキーはEdge Function内だけで使用し、RenderやGitHubには置きません。
        """
    )
    st.caption("この初期版は個人利用向けです。外部への送信・購入・投稿などは自動実行しません。")

st.divider()
st.caption("My Personal AI · 個人用開発プロトタイプ")
