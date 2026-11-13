"""
登入閘門（DEMO 展示版）—— 需以 Google 帳號登入才能查看，**不限網域**。

使用 Streamlit 原生 OIDC 登入（st.login / st.user，需 streamlit>=1.42、Authlib、httpx）。

設定：`.streamlit/secrets.toml`（本機）與 Streamlit Cloud Secrets（線上）需有 [auth] / [auth.google]，
      內容見 `.streamlit/secrets.toml.example`。
用法：在 app.py 的 st.set_page_config() 之後、其餘畫面之前呼叫 require_login()。
安全原則：fail-closed —— 未設定 [auth] 時一律擋下並停止渲染（不會退回成「免登入」）。

要限制誰能看時：把允許的 email 填進 ALLOWED_EMAILS，或把允許的網域填進 ALLOWED_DOMAINS。
兩者都留空 = 任何通過 Google 驗證的帳號都能登入。
"""
from __future__ import annotations

import streamlit as st

# 選用的白名單（小寫）。兩者都留空 = 不限制。
ALLOWED_EMAILS: set[str] = set()      # 例：{"someone@example.com"}
ALLOWED_DOMAINS: set[str] = set()     # 例：{"example.com"}


def current_email() -> str:
    """回傳目前登入者 email（小寫）；未登入回空字串。"""
    if getattr(st.user, "is_logged_in", False):
        return (st.user.get("email") or "").strip().lower()
    return ""


def _is_allowed(email: str) -> bool:
    if not ALLOWED_EMAILS and not ALLOWED_DOMAINS:
        return True
    return email in ALLOWED_EMAILS or email.rsplit("@", 1)[-1] in ALLOWED_DOMAINS


def require_login() -> str:
    """驗證已用 Google 登入，通過則回傳 email；否則顯示提示並 st.stop()。"""
    # 0) 尚未設定 [auth] → fail-closed
    try:
        has_auth = "auth" in st.secrets
    except Exception:
        has_auth = False   # 完全沒有 secrets 檔
    if not has_auth:
        st.error(
            "🔒 登入尚未設定。請於 `.streamlit/secrets.toml`（本機）與 "
            "Streamlit Cloud Secrets（線上）補上 [auth] / [auth.google] 設定。"
            "（範本見 `.streamlit/secrets.toml.example`）")
        st.stop()

    # 1) 未登入 → 顯示登入頁
    if not getattr(st.user, "is_logged_in", False):
        st.markdown("## 📊 人效報告（展示版）")
        st.info("請使用 Google 帳號登入後查看。本展示版的資料皆為合成範例資料。")
        st.button("使用 Google 登入", type="primary",
                  on_click=st.login, args=("google",))
        st.stop()

    # 2) 已登入 → 需有已驗證的 email；若設了白名單再比對
    email = (st.user.get("email") or "").strip().lower()
    verified = st.user.get("email_verified", True)
    if not email or not verified or not _is_allowed(email):
        st.error(f"⛔ 此帳號（{email or '未知'}）無法查看本頁。")
        st.button("換一個帳號登入", on_click=st.logout)
        st.stop()

    return email


def logout_button(location=st.sidebar) -> None:
    """在指定位置（預設側欄）顯示目前登入者與登出按鈕。"""
    email = current_email()
    if email:
        location.caption(f"👤 {email}")
        location.button("登出", on_click=st.logout, use_container_width=True)
