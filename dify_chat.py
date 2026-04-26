import streamlit as st
import pandas as pd
import requests
import time

# ======================
# ページ設定
# ======================
st.set_page_config(
    page_title="和建設 相談チャット",
    layout="centered"
)

ASSISTANT_ICON = "🏡"
USER_ICON = "👤"

# ======================
# Dify設定
# ======================
DIFY_API_KEY = "app-xxxxxxxxxxxxxxxx"
BASE_URL = "https://api.dify.ai/v1"

def chat_with_dify(message):
    url = f"{BASE_URL}/chat-messages"
    headers = {
        "Authorization": "Bearer " + DIFY_API_KEY.strip(),
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},
        "query": str(message),
        "user": "user1"
    }

    r = requests.post(url, headers=headers, json=payload)
    data = r.json()

    text = data.get("answer", "")
    files = data.get("files", [])
    image_urls = [f["url"] for f in files if f.get("type") == "image"]

    return text, image_urls

# ======================
# セッション
# ======================
for key, val in {
    "messages": [],
    "mode": "free",
    "step": 0,
    "data": {},
    "result": None,
    "points": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ======================
# 🎯 サイドバー（ポイント）
# ======================
with st.sidebar:
    st.title("👤 あなたの状況")

    st.metric("✨ ポイント", f"{st.session_state.points} pt")

    max_points = 50
    progress = min(st.session_state.points / max_points, 1.0)
    st.progress(progress)

    if st.session_state.points >= 30:
        st.success("🏆 シルバーランク")
    elif st.session_state.points >= 10:
        st.info("🥉 ブロンズランク")

# ======================
# タイトル
# ======================
st.title("🏡 和建設 住まい相談AI")
st.caption("間取り・設備・ローンまでサポート")

# ======================
# データ
# ======================
df_rooms = pd.read_csv("rooms.csv")

# ======================
# 履歴表示
# ======================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=msg.get("avatar")):
        st.markdown(msg["content"])

# ======================
# 入力
# ======================
user_input = st.chat_input("質問を入力してください")

# ======================
# 入力処理
# ======================
if user_input:

    st.session_state.points += 1

    st.session_state.messages.append(
        {"role": "user", "content": user_input, "avatar": USER_ICON}
    )

    with st.chat_message("user", avatar=USER_ICON):
        st.markdown(user_input)

    if "ローン" in user_input:
        st.session_state.mode = "loan"

# ======================
# 🏦 ローンモードUI
# ======================
if st.session_state.mode == "loan":

    if st.session_state.step == 0:
        st.session_state.step = 1

    if st.session_state.step == 1:
        with st.chat_message("assistant", avatar=ASSISTANT_ICON):
            st.markdown("🏦 部屋番号を選んでください\n\n201 / 202 / 203 / 204")

            cols = st.columns(4)

            rooms = [201, 202, 203, 204]

            for i, room in enumerate(rooms):
                if cols[i].button(f"{room}"):

                    price = df_rooms[df_rooms["room"] == room]["price"].values

                    if len(price) > 0:
                        loan = int(price[0].replace(",", ""))
                        st.session_state.data["loan"] = loan
                        st.session_state.step = 2
                        st.rerun()

    elif st.session_state.step == 2:
        years = st.number_input("返済年数（年）", min_value=1, max_value=50, value=35)

        if st.button("次へ（年利入力）"):
            st.session_state.data["years"] = years
            st.session_state.step = 3
            st.rerun()

    elif st.session_state.step == 3:
        rate = st.number_input("年利（例：0.01）", value=0.01)

        if st.button("次へ（返済方式）"):
            st.session_state.data["rate"] = rate
            st.session_state.step = 4
            st.rerun()

    elif st.session_state.step == 4:
        method = st.radio("返済方式を選択", ["元利均等", "元金均等"])

        if st.button("計算する"):
            loan = st.session_state.data["loan"]
            years = st.session_state.data["years"]
            rate = st.session_state.data["rate"]

            months = years * 12
            m_rate = rate / 12
            balance = loan
            rows = []

            if method == "元利均等":
                payment = loan * m_rate * (1 + m_rate)**months / ((1 + m_rate)**months - 1)
                for i in range(1, months + 1):
                    interest = balance * m_rate
                    principal = payment - interest
                    balance -= principal
                    rows.append([i, payment, principal, interest, balance])
            else:
                principal_payment = loan / months
                for i in range(1, months + 1):
                    interest = balance * m_rate
                    payment = principal_payment + interest
                    balance -= principal_payment
                    rows.append([i, payment, principal_payment, interest, balance])

            st.session_state.result = pd.DataFrame(
                rows,
                columns=["回数", "毎月返済額", "元金", "利息", "残高"]
            )

            st.session_state.mode = "free"
            st.session_state.step = 0
            st.rerun()

# ======================
# 🤖 通常チャット
# ======================
elif user_input:

    with st.chat_message("assistant", avatar=ASSISTANT_ICON):
        with st.spinner("AIが回答中..."):
            text, urls = chat_with_dify(user_input)

            placeholder = st.empty()
            display = ""

            for c in text:
                display += c
                placeholder.markdown(display)
                time.sleep(0.01)

# ======================
# 結果表示
# ======================
if st.session_state.result is not None:

    st.divider()
    st.subheader("📊 ローン結果")

    st.line_chart(st.session_state.result.set_index("回数")["残高"])
    st.dataframe(st.session_state.result)