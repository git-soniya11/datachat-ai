git status
import html
import base64
from typing import Any
from pathlib import Path

import pandas as pd
import requests
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="DataChat AI",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONFIGURATION
# ============================================================

# FastAPI is running with prefix="/api"
BACKEND_ROOT_URL = "http://127.0.0.1:8000"
BACKEND_URL = f"{BACKEND_ROOT_URL}/api"

REQUEST_TIMEOUT = 180


# ============================================================
# SESSION STATE
# ============================================================

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "preview" not in st.session_state:
    st.session_state.preview = None

if "uploaded_keys" not in st.session_state:
    st.session_state.uploaded_keys = set()


# ============================================================
# HELPERS
# ============================================================

def normalize_files(data: Any) -> list:
    """Convert different possible API file-list responses to a list."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("files", "data", "items", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def filename_from_item(item: Any) -> str:
    """Extract filename from a backend file object."""
    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        return str(
            item.get("filename")
            or item.get("name")
            or item.get("file_name")
            or ""
        )

    return ""


def fetch_uploaded_files() -> list:
    """Get uploaded files from FastAPI."""
    response = requests.get(
        f"{BACKEND_URL}/files",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return normalize_files(response.json())


def upload_file(uploaded_file) -> tuple[bool, str]:
    """Upload one file to FastAPI."""
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }

    response = requests.post(
        f"{BACKEND_URL}/uploads",
        files=files,
        timeout=REQUEST_TIMEOUT,
    )

    if response.ok:
        return True, response.text or "Upload successful."

    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text

    return False, str(detail)


def delete_file(filename: str) -> tuple[bool, str]:
    """Delete a file through FastAPI."""
    response = requests.delete(
        f"{BACKEND_URL}/files/{requests.utils.quote(filename, safe='')}",
        timeout=REQUEST_TIMEOUT,
    )

    if response.ok:
        return True, response.text or "File deleted."

    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text

    return False, str(detail)


def preview_file(filename: str) -> dict:
    """Request a dataset preview from FastAPI."""
    response = requests.get(
        f"{BACKEND_URL}/files/{requests.utils.quote(filename, safe='')}/preview",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()

    if isinstance(data, dict):
        return data

    return {
        "filename": filename,
        "preview": data,
    }


def send_chat(question: str, selected_files: list) -> Any:
    """Send the natural-language question to FastAPI /api/chat."""
    payload = {
        "message": question,
        "files": selected_files,
    }

    response = requests.post(
        f"{BACKEND_URL}/chat",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    return response.json()


def extract_chat_answer(data: Any) -> Any:
    """
    Preserve PandasAI typed responses such as:
    {"type": "chart", "value": "exports/charts/....png"}

    For wrapper responses such as {"response": ...}, unwrap the
    wrapper while keeping the original typed result intact.
    """
    if isinstance(data, dict):

        # IMPORTANT:
        # Do not unwrap {"type": "...", "value": ...}.
        # The renderer needs the type to know that the value is a chart.
        if "type" in data and ("value" in data or "data" in data):
            return data

        for key in ("response", "answer", "result", "data"):
            if key in data:
                return data[key]

    return data


def render_result(result: Any) -> None:
    """Render text, numbers, dataframes and common chart/image responses."""

    if isinstance(result, dict):

        result_type = str(
            result.get("type")
            or result.get("result_type")
            or ""
        ).lower()

        # ----------------------------
        # NUMBER / VALUE
        # ----------------------------
        if result_type in {"number", "numeric", "integer", "float"}:
            value = result.get("value", result.get("data"))
            st.metric("Answer", value)
            return

        # ----------------------------
        # DATAFRAME / TABLE
        # ----------------------------
        if result_type in {"dataframe", "df", "table"}:
            value = result.get("value", result.get("data", result.get("rows")))

            if isinstance(value, list):
                try:
                    st.dataframe(
                        pd.DataFrame(value),
                        use_container_width=True,
                        hide_index=True,
                    )
                except Exception:
                    st.write(value)
            else:
                st.write(value)

            return

        # ----------------------------
        # IMAGE / CHART
        # ----------------------------
        if result_type in {"image", "chart", "plot", "figure"}:
            value = result.get("value", result.get("data"))

            if isinstance(value, str):
                # Base64 image
                if value.startswith("data:image"):
                    try:
                        encoded = value.split(",", 1)[1]
                        st.image(
                            base64.b64decode(encoded),
                            use_container_width=True,
                        )
                        return
                    except Exception:
                        pass

                # HTTP/HTTPS image URL
                if value.startswith(("http://", "https://")):
                    try:
                        st.image(value, use_container_width=True)
                        return
                    except Exception:
                        st.error(f"Could not display chart: {value}")
                        return

                # PandasAI commonly returns a relative path such as:
                # exports/charts/temp_chart_xxx.png
                chart_path = value.replace("\\", "/")

                # Try the path relative to the Streamlit working directory.
                local_path = Path(chart_path)

                if local_path.exists():
                    st.image(
                        str(local_path),
                        caption="Generated Chart",
                        use_container_width=True,
                    )
                    return

                # If FastAPI and Streamlit use the same project directory,
                # this also handles paths returned with a leading "./".
                if chart_path.startswith("./"):
                    local_path = Path(chart_path[2:])
                    if local_path.exists():
                        st.image(
                            str(local_path),
                            caption="Generated Chart",
                            use_container_width=True,
                        )
                        return

                # The backend path cannot be rendered directly by Streamlit
                # when it belongs to the FastAPI process. If the backend
                # exposes /exports as static files, use the HTTP URL.
                if chart_path.startswith("exports/"):
                    chart_url = f"{BACKEND_ROOT_URL}/{chart_path}"
                    try:
                        st.image(
                            chart_url,
                            caption="Generated Chart",
                            use_container_width=True,
                        )
                        return
                    except Exception:
                        st.error(
                            "Chart was generated, but Streamlit could not "
                            f"load it from: {chart_url}"
                        )
                        return

                st.error(f"Chart file not found: {value}")
                return

            st.write(value)
            return

        # ----------------------------
        # TEXT / WRAPPED RESPONSES
        # ----------------------------
        if "response" in result or "answer" in result or "result" in result:
            render_result(extract_chat_answer(result))
            return

        # A typed result may use "data" instead of "value".
        if result_type and "data" in result:
            render_result(
                {
                    "type": result_type,
                    "value": result["data"],
                }
            )
            return

        # Generic dictionary
        st.json(result)
        return

    if isinstance(result, list):
        if result and all(isinstance(row, dict) for row in result):
            st.dataframe(
                pd.DataFrame(result),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write(result)
        return

    # ----------------------------
    # RAW PATH RETURNED AS STRING
    # ----------------------------
    if isinstance(result, str):
        clean_result = result.replace("\\", "/")

        if clean_result.startswith("data:image"):
            try:
                encoded = clean_result.split(",", 1)[1]
                st.image(
                    base64.b64decode(encoded),
                    use_container_width=True,
                )
                return
            except Exception:
                pass

        raw_path = Path(clean_result)

        if raw_path.exists():
            st.image(
                str(raw_path),
                caption="Generated Chart",
                use_container_width=True,
            )
            return

        if clean_result.startswith("exports/"):
            chart_url = f"{BACKEND_ROOT_URL}/{clean_result}"
            try:
                st.image(
                    chart_url,
                    caption="Generated Chart",
                    use_container_width=True,
                )
                return
            except Exception:
                st.error(
                    "Chart was generated, but it could not be loaded."
                )
                return

    st.markdown(str(result))


def refresh_files() -> None:
    """Refresh file list from backend."""
    try:
        items = fetch_uploaded_files()
        st.session_state.uploaded_files = [
            filename_from_item(item)
            for item in items
            if filename_from_item(item)
        ]
    except requests.RequestException as exc:
        st.session_state.uploaded_files = []
        st.session_state.backend_error = str(exc)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at 10% 0%,
                rgba(91, 45, 170, 0.28),
                transparent 28%
            ),
            radial-gradient(
                circle at 90% 0%,
                rgba(39, 83, 145, 0.22),
                transparent 30%
            ),
            #050817;
        color: #f8faff;
    }

    .main .block-container {
        max-width: 1250px;
        padding-top: 42px;
        padding-bottom: 60px;
    }

    .main-title {
        font-size: 38px;
        line-height: 1.1;
        font-weight: 750;
        color: #f8faff;
        margin-bottom: 7px;
    }

    .subtitle {
        color: #aab2c5;
        font-size: 15px;
        line-height: 1.7;
        margin-bottom: 28px;
    }

    .card {
        background: rgba(17, 24, 39, 0.88);
        border: 1px solid #202c43;
        border-radius: 18px;
        padding: 23px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.18);
    }

    .card-title {
        color: #f7f8ff;
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 7px;
    }

    .card-subtitle {
        color: #8f99ae;
        font-size: 14px;
    }

    .metric-card {
        background: linear-gradient(
            145deg,
            rgba(17, 24, 39, 0.96),
            rgba(12, 18, 33, 0.96)
        );
        border: 1px solid #202c43;
        border-radius: 18px;
        padding: 27px 20px;
        text-align: center;
        min-height: 138px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.16);
    }

    .metric-value {
        color: #a66cff;
        font-size: 31px;
        font-weight: 750;
        margin-bottom: 12px;
    }

    .metric-label {
        color: #f2f3f7;
        font-size: 15px;
        font-weight: 550;
    }

    .file-card {
        background: #0d1424;
        border: 1px solid #1d2940;
        border-radius: 12px;
        padding: 14px 16px;
        margin: 8px 0 10px 0;
        color: #d6d9e3;
        font-size: 14px;
    }

    .empty-card {
        background: #0d1424;
        border: 1px dashed #34415c;
        border-radius: 13px;
        padding: 22px;
        color: #8791a6;
        text-align: center;
        margin-top: 10px;
    }

    .chat-card {
        background: rgba(8, 13, 27, 0.72);
        border: 1px solid #1b2740;
        border-radius: 18px;
        padding: 24px;
    }

    .user-message {
        background: linear-gradient(135deg, #6740ee, #9858ff);
        padding: 14px 17px;
        border-radius: 15px;
        margin: 12px 0;
        color: white;
        box-shadow: 0 7px 20px rgba(112, 66, 235, 0.18);
    }

    .assistant-message {
        background: #111827;
        border: 1px solid #26334a;
        padding: 16px 18px;
        border-radius: 15px;
        margin: 12px 0;
        color: #e8ebf2;
    }

    .history-title {
        color: #f7f8ff;
        font-size: 20px;
        font-weight: 700;
        margin: 22px 0 12px 0;
    }

    .stButton > button {
        border-radius: 10px;
        border: 0;
        background: linear-gradient(135deg, #7c4dff, #9b5cff);
        color: white;
        font-weight: 650;
        min-height: 42px;
        transition: 0.2s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #8b5cff, #aa6cff);
        color: white;
        border: 0;
    }

    [data-testid="stFileUploader"] {
        background: #f4f5f8;
        border-radius: 12px;
        padding: 6px;
    }

    [data-testid="stFileUploader"] section {
        border: none;
    }

    [data-testid="stFileUploader"] small {
        color: #555 !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #111827;
        border: 1px solid #26334a;
        border-radius: 11px;
        color: white;
    }

    textarea {
        background-color: #111827 !important;
        color: white !important;
        border: 1px solid #34405a !important;
        border-radius: 13px !important;
    }

    textarea::placeholder {
        color: #7f899f !important;
    }

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    hr {
        border-color: #202b40;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# REFRESH FILES FROM BACKEND
# ============================================================

if "files_loaded" not in st.session_state:
    st.session_state.files_loaded = True
    refresh_files()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">DataChat AI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
        Conversational Analytics Platform · Upload CSV & Excel files,
        ask questions in natural language, and turn raw data into
        insights, charts, and analytics using AI.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TOP METRICS
# ============================================================

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">
                {len(st.session_state.uploaded_files)}
            </div>
            <div class="metric-label">Uploaded Files</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metric2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">
                {len(st.session_state.chat_history)}
            </div>
            <div class="metric-label">Chat Messages</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with metric3:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">AI</div>
            <div class="metric-label">Powered Analytics</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown("<br>", unsafe_allow_html=True)


# ============================================================
# SECTION HEADERS
# ============================================================

left_header, right_header = st.columns([1, 2])

with left_header:
    st.markdown(
        """
        <div class="card">
            <div class="card-title">📁 Upload Files</div>
            <div class="card-subtitle">
                Upload CSV or Excel datasets
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_header:
    st.markdown(
        """
        <div class="card">
            <div class="card-title">💬 Chat With Your Data</div>
            <div class="card-subtitle">
                Ask analytical questions in natural language
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown("<br>", unsafe_allow_html=True)


# ============================================================
# MAIN TWO-COLUMN AREA
# ============================================================

left_col, right_col = st.columns([1, 2], gap="large")


# ============================================================
# LEFT PANEL
# ============================================================

with left_col:

    uploads = st.file_uploader(
        "Upload CSV or XLSX",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        help="CSV or XLSX files. Upload size is controlled by Streamlit config.",
    )

    if uploads:

        upload_changed = False

        for uploaded in uploads:

            upload_key = (
                f"{uploaded.name}:{uploaded.size}:"
                f"{getattr(uploaded, 'file_id', '')}"
            )

            if upload_key in st.session_state.uploaded_keys:
                continue

            with st.spinner(f"Uploading {uploaded.name}..."):

                try:
                    success, message = upload_file(uploaded)

                    if success:
                        st.session_state.uploaded_keys.add(upload_key)
                        upload_changed = True
                        st.success(f"{uploaded.name} uploaded.")

                    else:
                        st.error(f"{uploaded.name}: {message}")

                except requests.RequestException as exc:
                    st.error(
                        f"Could not upload {uploaded.name}: {exc}"
                    )

        if upload_changed:
            refresh_files()

    st.markdown(
        '<div class="card-title" style="margin-top:25px;">📁 Uploaded Files</div>',
        unsafe_allow_html=True,
    )

    files = st.session_state.uploaded_files

    if not files:

        st.markdown(
            """
            <div class="empty-card">
                Your workspace is ready.<br>
                Upload a dataset to begin.
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        for index, filename in enumerate(files):

            safe_filename = html.escape(filename)

            st.markdown(
                f"""
                <div class="file-card">
                    📄 {safe_filename}
                </div>
                """,
                unsafe_allow_html=True,
            )

            preview_col, delete_col = st.columns(2)

            with preview_col:

                if st.button(
                    "Preview",
                    key=f"preview_{index}_{filename}",
                    use_container_width=True,
                ):

                    try:
                        st.session_state.preview = preview_file(filename)
                        st.rerun()

                    except requests.RequestException as exc:
                        st.error(
                            f"Preview failed: {exc}"
                        )

            with delete_col:

                if st.button(
                    "Delete",
                    key=f"delete_{index}_{filename}",
                    use_container_width=True,
                ):

                    try:
                        success, message = delete_file(filename)

                        if success:
                            st.session_state.preview = None
                            refresh_files()
                            st.rerun()

                        else:
                            st.error(message)

                    except requests.RequestException as exc:
                        st.error(
                            f"Delete failed: {exc}"
                        )


    # --------------------------------------------------------
    # PREVIEW
    # --------------------------------------------------------

    if st.session_state.preview:

        preview = st.session_state.preview

        preview_filename = (
            preview.get("filename")
            or preview.get("name")
            or "Dataset"
        )

        st.markdown(
            f'<div class="card-title" style="margin-top:22px;">'
            f'📊 Dataset Preview · {html.escape(str(preview_filename))}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # FastAPI returns {"filename": "...", "preview": [...]}
        preview_rows = (
            preview.get("preview")
            or preview.get("rows")
            or preview.get("data")
            or preview.get("value")
            or []
        )

        if isinstance(preview_rows, list) and preview_rows:

            try:
                preview_df = pd.DataFrame(preview_rows)

                st.dataframe(
                    preview_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(
                    f"Showing {len(preview_df)} preview rows · "
                    f"{len(preview_df.columns)} columns"
                )

            except Exception as exc:
                st.error(f"Could not display preview: {exc}")

        elif isinstance(preview_rows, dict) and preview_rows:

            try:
                st.dataframe(
                    pd.DataFrame(preview_rows),
                    use_container_width=True,
                    hide_index=True,
                )
            except Exception:
                st.json(preview_rows)

        else:
            st.warning("No preview data available for this file.")

    # def preview_file(base_url, filename):
    #     try:
    #         response = requests.get(
    #             f"{base_url}/files/{filename}/preview",
    #             timeout=30
    #         )

    #         response.raise_for_status()

    #         data = response.json()

    #         return data

    #     except requests.RequestException as e:
    #         st.error(f"Preview failed: {e}")
    #         return None

    #     except Exception as e:
    #         st.error(f"Preview error: {e}")
    #         return None


# # ============================================================
# # RIGHT PANEL - CHAT
# # ============================================================

with right_col:

    st.markdown(
        '<div class="chat-card">',
        unsafe_allow_html=True,
    )

    st.markdown("**Select datasets**")

    selected_files = st.multiselect(
        "Select datasets",
        options=st.session_state.uploaded_files,
        default=(
            st.session_state.uploaded_files[:1]
            if st.session_state.uploaded_files
            else []
        ),
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("**Ask a question**")

    question = st.text_area(
        "Question",
        placeholder=(
            "Example: Which department has the highest "
            "average salary?"
        ),
        height=160,
        label_visibility="collapsed",
    )

    send_col, clear_col = st.columns(2)

    with send_col:
        send = st.button(
            "🚀 Send Message",
            use_container_width=True,
            type="primary",
        )

    with clear_col:
        clear = st.button(
            "🗑️ Clear Chat",
            use_container_width=True,
        )

    if clear:
        st.session_state.chat_history = []
        st.rerun()

    # ========================================================
    # SEND QUESTION
    # ========================================================

    if send:

        if not selected_files:

            st.warning(
                "Please select at least one dataset."
            )

        elif not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner("Analyzing data with AI..."):

                try:

                    raw_response = send_chat(
                        question.strip(),
                        selected_files,
                    )

                    answer = extract_chat_answer(raw_response)

                    st.session_state.chat_history.append(
                        {
                            "role": "user",
                            "message": question.strip(),
                        }
                    )

                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "message": answer,
                        }
                    )

                    st.rerun()

                except requests.exceptions.HTTPError as exc:

                    detail = str(exc)

                    try:
                        detail = exc.response.json().get(
                            "detail",
                            exc.response.text,
                        )
                    except Exception:
                        pass

                    st.error(
                        f"Backend error: {detail}"
                    )

                except requests.exceptions.ConnectionError:

                    st.error(
                        "Could not connect to FastAPI. "
                        "Make sure your backend is running on "
                        "http://127.0.0.1:8000."
                    )

                except requests.exceptions.Timeout:

                    st.error(
                        "The AI request timed out. "
                        "Try again or increase the backend timeout."
                    )

                except Exception as exc:

                    st.error(
                        f"Something went wrong: {exc}"
                    )


    # ========================================================
    # CHAT HISTORY
    # ========================================================

    st.markdown(
        '<div class="history-title">Conversation History</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.chat_history:

        st.markdown(
            """
            <div class="empty-card">
                Start chatting with your datasets.
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        for chat in st.session_state.chat_history:

            if chat["role"] == "user":

                safe_message = html.escape(
                    str(chat["message"])
                )

                st.markdown(
                    f"""
                    <div class="user-message">
                        <b>You:</b><br>
                        {safe_message}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    """
                    <div class="assistant-message">
                        <b>🤖 DataChat AI</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                render_result(chat["message"])

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )