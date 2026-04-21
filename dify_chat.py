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

# ======================
# アイコン設定
# ======================
ASSISTANT_ICON = "🏡"
USER_ICON = "👤"

# ======================
# Dify設定
# ======================
DIFY_API_KEY = "app-Z8GvU88Jz1vwO81JXnV8SLL9"
BASE_URL = "https://api.dify.ai/v1"

def chat_with_dify(message):
    url = f"{BASE_URL}/chat-messages"

    headers = {
        "Authorization": "Bearer " + DIFY_API_KEY.strip(),
        "Content-Type": "application/json; charset=utf-8"
    }

    payload = {
        "inputs": {},
        "query": str(message),
        "user": "user1"
    }

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    text = data.get("answer", "")
    files = data.get("files", [])

    image_urls = [
        f["url"] for f in files if f.get("type") == "image"
    ]

    return text, image_urls

# ======================
# CSS（公式っぽいUI）
# ======================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f5f7fa, #e4efe9);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* AI */
.stChatMessage[data-testid="assistant"] {
    background: white;
    border-radius: 18px;
    padding: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    animation: fadeUp 0.4s ease;
}

/* ユーザー */
.stChatMessage[data-testid="user"] {
    background: #dff5e1;
    border-radius: 18px;
    padding: 14px;
    animation: fadeUp 0.4s ease;
}

@keyframes fadeUp {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
""", unsafe_allow_html=True)

# ======================
# タイトル
# ======================
st.title("🏡 和建設 住まい相談AI")
st.caption("間取り・設備・品質・ローンまでサポート 🌿")

# ======================
# データ
# ======================
df_rooms = pd.read_csv("rooms.csv")

# ======================
# セッション
# ======================
for key, val in {
    "messages": [],
    "mode": "free",
    "step": 0,
    "data": {},
    "result": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

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

if user_input:

    # ユーザー表示
    st.session_state.messages.append(
        {"role": "user", "content": user_input, "avatar": USER_ICON}
    )
    with st.chat_message("user", avatar=USER_ICON):
        st.markdown(user_input)

    # ローン判定
    if any(w in user_input for w in ["ローン", "返済", "金利"]):
        st.session_state.mode = "loan"

    # ======================
    # ローン処理
    # ======================
    if st.session_state.mode == "loan":

        if st.session_state.step == 0:
            bot_msg = "🏦 購入したい部屋番号を教えてください"
            st.session_state.step = 1

        elif st.session_state.step == 1:
            try:
                room = int(user_input)
                price = df_rooms[df_rooms["room"] == room]["price"].values
                if len(price) == 0:
                    bot_msg = "その部屋番号は見つかりませんでした💦"
                else:
                    loan = int(price[0].replace(",", ""))
                    st.session_state.data["loan"] = loan
                    bot_msg = f"💰 価格は {loan:,} 円です\n返済年数を教えてください"
                    st.session_state.step = 2
            except:
                bot_msg = "数字で入力してください🙂"

        elif st.session_state.step == 2:
            try:
                st.session_state.data["years"] = int(user_input)
                bot_msg = "📉 年利（例：0.01）を入力してください"
                st.session_state.step = 3
            except:
                bot_msg = "年数は数字で入力してください"

        elif st.session_state.step == 3:
            try:
                st.session_state.data["rate"] = float(user_input)
                bot_msg = "返済方式は「元利均等」か「元金均等」です"
                st.session_state.step = 4
            except:
                bot_msg = "小数で入力してください"

        elif st.session_state.step == 4:
            method = user_input

            if method not in ["元利均等", "元金均等"]:
                bot_msg = "「元利均等」か「元金均等」で入力してください🙂"
            else:
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

                bot_msg = "📊 シミュレーション結果を表示しました！"
                st.session_state.mode = "free"
                st.session_state.step = 0

        st.session_state.messages.append(
            {"role": "assistant", "content": bot_msg, "avatar": ASSISTANT_ICON}
        )
        with st.chat_message("assistant", avatar=ASSISTANT_ICON):
            st.markdown(bot_msg)

    # ======================
    # Dify（ぬるぬる＋画像極小）
    # ======================
    else:
        with st.chat_message("assistant", avatar=ASSISTANT_ICON):
            with st.spinner("AIが回答中..."):
                time.sleep(0.3)

                text, urls = chat_with_dify(user_input)

                # タイピング表示
                placeholder = st.empty()
                display = ""
                for c in text:
                    display += c
                    placeholder.markdown(display)
                    time.sleep(0.008)

                # 🔥 画像（確実に小さい）
                if urls:
                    st.markdown("### 🏠 間取り・設備・品質")

                    cols = st.columns(6)  # ←ここ重要
                    for i, url in enumerate(urls):
                        with cols[i % 6]:
                            st.image(url, width=60)  # ←ここ超重要（小さい）

                st.session_state.messages.append(
                    {"role": "assistant", "content": text, "avatar": ASSISTANT_ICON}
                )

# ======================
# ローン結果
# ======================
if st.session_state.result is not None:

    st.divider()
    st.subheader("📊 ローン概要")

    loan = st.session_state.data["loan"]
    years = st.session_state.data["years"]
    rate = st.session_state.data["rate"]

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 借入額", f"{loan:,} 円")
    c2.metric("📆 年数", f"{years} 年")
    c3.metric("📉 金利", f"{rate*100:.2f} %")

    st.subheader("📈 残高推移")
    st.line_chart(st.session_state.result.set_index("回数")["残高"])

    st.subheader("📄 詳細表")
    st.dataframe(
        st.session_state.result.round(0),
        height=300,
        use_container_width=True
    )