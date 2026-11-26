from __future__ import annotations

import hmac
import json

import streamlit as st
import streamlit.components.v1 as components

from agent import run_agent_task
from config import get_setting
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

# ローカルAIエンジンは外部の生成AI APIキーを必要としません。
store = MemoryStore.from_settings()

# Single-owner ID: chat history remains available after reloads and on other devices.
if "session_id" not in st.session_state:
    st.session_state.session_id = "personal-owner-default"
for key, default in {
    "uploaded_context": "",
    "uploaded_name": "",
    "latest_answer": "",
    "last_plan": [],
    "last_tools_used": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.title("🧠 My Personal AI")
    st.caption("Chromebook / Windows / Mac 対応")
    st.caption("外部の生成AI APIを使わないローカルモード・複数依頼対応")
    speak_answers = st.toggle("回答を音声で読み上げる", value=False)
    sovereign_mode = st.toggle("君主風・依頼優先モード", value=True)
    st.caption("通常の依頼は不必要に拒否せず、目的・口調・形式の希望を優先します。安全・プライバシー保護は維持します。")
    st.caption("AIエンジン: Python Local Engine v0.9.0")
    st.caption(f"記憶保存先: {store.backend_name}")
    if store.backend_name == "SQLite（ローカル試作用）":
        st.warning("クラウド公開後はSupabaseを設定してください。")
    if st.button("ログアウト", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("My Personal AI")
st.caption("会話・計算・長期記憶・ファイル分析・作業計画・音声読み上げ")

chat_tab, files_tab, memory_tab, tasks_tab, setup_tab = st.tabs(
    ["💬 チャット", "📎 ファイル", "🧠 長期記憶", "✅ タスク", "⚙️ 接続状態"]
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

    st.caption("例：計算して 125 * 8 ／ 3kmをmに変換 ／ Pythonとは？ ／ このアプリの計画を立てて")
    with st.form("chat_form", clear_on_submit=True):
        prompt = st.text_area("メッセージ", placeholder="AIに話しかけてください", height=100)
        send = st.form_submit_button("送信", type="primary", use_container_width=True)

    if send and prompt.strip():
        try:
            store.add_message(st.session_state.session_id, "user", prompt.strip())
            memories = store.get_memories(limit=100)
            history = store.get_messages(st.session_state.session_id, limit=12)
            with st.spinner("AIエージェントが考えています…"):
                result = run_agent_task(
                    client=None,
                    user_request=prompt.strip(),
                    history=history[:-1],
                    memories=memories,
                    document_context=st.session_state.uploaded_context,
                    use_web_search=False,
                    use_multi_agent=False,
                    sovereign_mode=sovereign_mode,
                )
            answer = result["answer"]
            store.add_message(st.session_state.session_id, "assistant", answer)
            st.session_state.latest_answer = answer
            st.session_state.last_plan = result.get("plan", [])
            st.session_state.last_tools_used = result.get("tools_used", [])
            st.rerun()
        except Exception as exc:
            st.error(f"処理中にエラーが発生しました: {exc}")

    visible_tools = [
        tool for tool in st.session_state.get("last_tools_used", [])
        if tool != "reference_retrieval"
    ]
    if visible_tools:
        st.caption("使用した機能: " + "、".join(visible_tools))

    if st.session_state.last_plan:
        with st.expander("今回のAI作業計画を見る", expanded=True):
            for index, step in enumerate(st.session_state.last_plan, start=1):
                st.markdown(f"{index}. {step}")

    if st.session_state.latest_answer and speak_answers:
        st.caption("音声はChromeなどのブラウザー標準の読み上げ機能で再生します。")
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
        help="ファイルはテキスト抽出後にアプリ内で処理します。原本はDBに保存しません。",
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
    st.info(
        "外部APIを使わない構成のため、音声の自動文字起こしは現在オフです。"
        "Chromebookの設定にある音声入力（マイク）で文章を入力し、チャット欄に貼り付けてください。"
    )

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

with tasks_tab:
    st.subheader("タスク管理")
    st.write("タスクをSupabaseの長期記憶へ保存します。完了したタスクは削除できます。")
    with st.form("task_form", clear_on_submit=True):
        task_text = st.text_input("新しいタスク", placeholder="例：AIエンジンのテストを確認する")
        add_task = st.form_submit_button("タスクを追加", type="primary")
    if add_task and task_text.strip():
        try:
            store.add_memory("タスク", task_text.strip())
            st.success("タスクを保存しました。")
            st.rerun()
        except Exception as exc:
            st.error(f"タスクを保存できませんでした: {exc}")
    try:
        tasks = [item for item in store.get_memories(limit=100) if item.get("category") == "タスク"]
        if not tasks:
            st.info("タスクはありません。")
        for item in tasks:
            with st.container(border=True):
                st.write(item.get("content", ""))
                if st.button("完了・削除", key=f"complete_task_{item['id']}"):
                    store.delete_memory(str(item["id"]))
                    st.rerun()
    except Exception as exc:
        st.error(f"タスクを読み込めませんでした: {exc}")

with setup_tab:
    st.subheader("接続状況")
    st.write("AI処理はPython内で実行します。Supabaseへの記憶保存のみクラウド通信を使います。")
    st.table(
        [
            {"項目": "AIエンジン", "状態": "Python Local Engine v0.9.0（生成AI API不要）"},
            {"項目": "Supabase URL", "状態": "設定済み" if get_setting("SUPABASE_URL") else "未設定"},
            {"項目": "Supabase記憶API", "状態": "設定済み" if (get_setting("SUPABASE_PUBLISHABLE_KEY") and get_setting("MEMORY_API_TOKEN")) else "未設定"},
            {"項目": "アクセスパスワード", "状態": "設定済み" if get_setting("APP_ACCESS_PASSWORD") else "未設定"},
        ]
    )
    st.markdown(
        """
        Renderの環境変数:
        - APP_ACCESS_PASSWORD
        - SUPABASE_URL
        - SUPABASE_PUBLISHABLE_KEY
        - MEMORY_API_TOKEN

        生成AIプロバイダーのAPIキーは使用しません。
        Supabaseの強いSecretキーはEdge Function内だけで使用し、RenderやGitHubには置きません。
        """
    )
    st.markdown("**現在のエンジン機能**\n\n- 日本語の基本会話とヘルプ\n- 複数依頼の分割と読みやすい回答レイアウト\n- 君主風・依頼優先モード（安全境界あり）\n- 数学・理科・プログラミングの基礎知識\n- 一次方程式・二次方程式の自動解法と検算\n- 割合・割引・百分率の文章題\n- 平均値・中央値・最頻値・分散・標準偏差の統計\n- 円・長方形・三角形の面積と円周\n- 速さ・距離・時間の文章題\n- オームの法則・密度の計算\n- 会話の文脈理解と概念関係の推論\n- 質問の種類と必要な処理の自動判定\n- 安全な計算・複合単位変換と検算\n- 日時・記憶検索\n- 資料の関連文検索・抽出的な要約\n- タスクの保存・削除\n- 目的別の計画作成\n\n**未対応**：自由な文章生成、任意の命令の完全理解、リアルタイム情報の網羅的な取得、音声の自動文字起こし。")
    st.caption("個人利用向けの初期版です。外部への送信・購入・投稿などは自動実行しません。")

st.divider()
st.caption("My Personal AI · 個人用開発プロトタイプ")
