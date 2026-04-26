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

ASSISTANT_ICON = "🤖"
USER_ICON = "👤"

# ======================
# CSS（🔥 右上ポイントバー）
# ======================
st.markdown("""
<style>

/* 右上ポイント表示（シンプル） */
.point-bar {
    position: fixed;
    top: 15px;
    right: 20px;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 10px 18px;
    border-radius: 10px;
    font-weight: bold;
    font-size: 18px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    z-index: 9999;
}

</style>
""", unsafe_allow_html=True)

# ======================
# セッション初期化
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
# 🎯 ポイントバー表示（※シンプル版）
# ======================
points = st.session_state.points

st.markdown(f"""
<div class="point-bar">
    ⭐ {points} pt
</div>
""", unsafe_allow_html=True)

# ======================
# Dify設定
# ======================
DIFY_API_KEY = "app-Z8GvU88Jz1vwO81JXnV8SLL9"
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

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()

        text = data.get("answer", "（回答が取得できませんでした）")
        files = data.get("files", [])

        image_urls = [
            f["url"] for f in files if f.get("type") == "image"
        ]

        return text, image_urls

    except Exception as e:
        return f"⚠️ エラー: {e}", []

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
# 入力処理（チャット送信）
# ======================
if user_input:

    # ⭐ポイント加算（チャット送信）
    st.session_state.points += 1

    st.session_state.messages.append(
        {"role": "user", "content": user_input, "avatar": USER_ICON}
    )

    with st.chat_message("user", avatar=USER_ICON):
        st.markdown(user_input)

    # ローンモードへ切り替え
    if any(w in user_input for w in ["ローン", "返済", "金利"]):
        st.session_state.mode = "loan"
        st.session_state.step = 1

# ======================
# 🏦 ローンUI
# ======================
if st.session_state.mode == "loan":

    st.divider()
    st.subheader("🏦 ローンシミュレーション")

    # ---- STEP1 部屋選択 ----
    if st.session_state.step == 1:
        st.markdown("**201・202・203・204 から選択してください👇**")

        cols = st.columns(4)
        rooms = [201, 202, 203, 204]

        for i, room in enumerate(rooms):
            if cols[i].button(f"{room}号室"):

                # ⭐ポイント加算（部屋選択）
                st.session_state.points += 2

                price = df_rooms[df_rooms["room"] == room]["price"].values

                if len(price) > 0:
                    loan = int(price[0].replace(",", ""))
                    st.session_state.data["loan"] = loan
                    st.session_state.step = 2

    # ---- STEP2 年数入力 ----
    elif st.session_state.step == 2:
        years = st.number_input("返済年数（年）", 1, 50, 35)

        if st.button("次へ"):

            # ⭐ポイント加算（年数確定）
            st.session_state.points += 1

            st.session_state.data["years"] = years
            st.session_state.step = 3

    # ---- STEP3 金利 ----
    elif st.session_state.step == 3:
        rate = st.number_input("年利（例：0.01）", value=0.01)

        if st.button("次へ"):

            # ⭐ポイント加算（金利確定）
            st.session_state.points += 1

            st.session_state.data["rate"] = rate
            st.session_state.step = 4

    # ---- STEP4 返済方式 + 計算 ----
    elif st.session_state.step == 4:
        method = st.radio("返済方式", ["元利均等", "元金均等"])

        if st.button("計算する"):

            # ⭐ポイント加算（計算実行）
            st.session_state.points += 3

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

# ======================
# 🤖 通常チャット
# ======================
if user_input and st.session_state.mode == "free":

    with st.chat_message("assistant", avatar=ASSISTANT_ICON):
        with st.spinner("AIが回答中..."):

            text, urls = chat_with_dify(user_input)

            placeholder = st.empty()
            display = ""

            for c in text:
                display += c
                placeholder.markdown(display)
                time.sleep(0.01)

            if urls:
                st.markdown("### 🏠 間取り・設備")
                cols = st.columns(6)
                for i, url in enumerate(urls):
                    with cols[i % 6]:
                        st.image(url, width=60)

            st.session_state.messages.append(
                {"role": "assistant", "content": text, "avatar": ASSISTANT_ICON}
            )

# ======================
# 📊 シミュレーション結果
# ======================
if st.session_state.result is not None:

    st.divider()
    st.subheader("📊 シミュレーション結果")

    st.line_chart(st.session_state.result.set_index("回数")["残高"])
    st.dataframe(st.session_state.result)