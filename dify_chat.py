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

ASSISTANT_ICON = "🏘"
USER_ICON = "👤"

# =================🏘
# CSS（🔥 右上ポイントバー）
# ======================
st.markdown("""
<style>

/* 右上ポイントバー */
.point-bar {
    position: fixed;
    top: 15px;
    right: 20px;
    background: rgba(255, 215, 0, 0.85);
    color: #333;
    padding: 10px 18px;
    border-radius: 14px;
    font-weight: bold;
    font-size: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    backdrop-filter: blur(8px);
    z-index: 9999;
    animation: fadeIn 0.5s ease;
}

/* アニメーション */
@keyframes fadeIn {
    from {opacity: 0; transform: translateY(-10px);}
    to {opacity: 1; transform: translateY(0);}
}

/* レベル表示 */
.point-rank {
    font-size: 12px;
    margin-top: 3px;
    text-align: right;
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
# 🎯 ポイントバー表示
# ======================
points = st.session_state.points

# ランク表示
if points >= 30:
    rank = "🏆 シルバー"
elif points >= 10:
    rank = "🥉 ブロンズ"
else:
    rank = "🔰 ビギナー"

st.markdown(f"""
<div class="point-bar">
    ⭐ {points} pt
    <div class="point-rank">{rank}</div>
</div>
""", unsafe_allow_html=True)

# ======================
# Dify設定
# ======================
DIFY_API_KEY = "app-Z8GvU88Jz1vwO81JXnV8SLL9 "  # ←自分のキーに
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
# 入力処理
# ======================
if user_input:

    st.session_state.points += 1

    st.session_state.messages.append(
        {"role": "user", "content": user_input, "avatar": USER_ICON}
    )

    with st.chat_message("user", avatar=USER_ICON):
        st.markdown(user_input)

    if any(w in user_input for w in ["ローン", "返済", "金利"]):
        st.session_state.mode = "loan"
        st.session_state.step = 1

# ======================
# 🏦 ローンUI
# ======================
if st.session_state.mode == "loan":

    st.divider()
    st.subheader("🏦 ローンシミュレーション")

    if st.session_state.step == 1:
        st.markdown("**201・202・203・204 から選択してください👇**")

        cols = st.columns(4)
        rooms = [201, 202, 203, 204]

        for i, room in enumerate(rooms):
            if cols[i].button(f"{room}号室"):

                price = df_rooms[df_rooms["room"] == room]["price"].values

                if len(price) > 0:
                    loan = int(price[0].replace(",", ""))
                    st.session_state.data["loan"] = loan
                    st.session_state.step = 2

    elif st.session_state.step == 2:
        years = st.number_input("返済年数（年）", 1, 50, 35)

        if st.button("次へ"):
            st.session_state.data["years"] = years
            st.session_state.step = 3

    elif st.session_state.step == 3:
        rate = st.number_input("年利（例：0.01）", value=0.01)

        if st.button("次へ"):
            st.session_state.data["rate"] = rate
            st.session_state.step = 4

    elif st.session_state.step == 4:
        method = st.radio("返済方式", ["元利均等", "元金均等"])

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
# 📊 結果
# ======================
if st.session_state.result is not None:

    st.divider()
    st.subheader("📊 シミュレーション結果")

    st.line_chart(st.session_state.result.set_index("回数")["残高"])
    st.dataframe(st.session_state.result)