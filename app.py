import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

st.set_page_config(page_title="台股看盤神器 Pro", layout="wide")

st.title("📈 台股看盤神器 Pro")

# ========================
# ⭐ 自選股（可編輯）
# ========================
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["2330", "2002", "1326", "6505"]

st.sidebar.header("⭐ 自選股")

new_stock = st.sidebar.text_input("新增股票代碼")

if st.sidebar.button("➕ 新增"):
    if new_stock and new_stock not in st.session_state.watchlist:
        st.session_state.watchlist.append(new_stock)

remove_stock = st.sidebar.selectbox("刪除股票", st.session_state.watchlist)

if st.sidebar.button("❌ 刪除"):
    st.session_state.watchlist.remove(remove_stock)

stocks = [{"id": s, "name": s} for s in st.session_state.watchlist]

# ========================
# TWSE 即時
# ========================
def fetch_twse():
    ex_ch = "|".join([f"tse_{s['id']}.tw" for s in stocks])
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&json=1"

    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://mis.twse.com.tw/"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json().get("msgArray", [])
    except:
        return []

# ========================
# yfinance
# ========================
def fetch_yf_hist(stock_id):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="3mo")
        return df if not df.empty else None
    except:
        return None

# ========================
# 技術指標
# ========================
def add_indicators(df):
    # KD
    low_min = df['Low'].rolling(9).min()
    high_max = df['High'].rolling(9).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    df['K'] = rsv.ewm(com=2).mean()
    df['D'] = df['K'].ewm(com=2).mean()

    # Momentum
    df['Momentum'] = df['Close'] - df['Close'].shift(10)

    # MA
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    # RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    return df

# ========================
# 訊號判斷（升級版）
# ========================
def analyze_signal(df):
    latest = df.iloc[-1]

    signal = "觀望"

    if latest['K'] > latest['D'] and latest['RSI'] < 70 and latest['MA5'] > latest['MA20']:
        signal = "🔥 偏多（可觀察買點）"

    elif latest['K'] < latest['D'] and latest['RSI'] > 30 and latest['MA5'] < latest['MA20']:
        signal = "❄️ 偏空（注意風險）"

    return signal

# ========================
# 整合
# ========================
def get_stock_data(twse_data, stock):
    code = stock["id"]

    tw = next((x for x in twse_data if x["c"] == code), None)
    df = fetch_yf_hist(code)

    if df is not None:
        df = add_indicators(df)

        prev_close = df["Close"].iloc[-2]
        latest = df.iloc[-1]

        price = float(tw["z"]) if tw and tw.get("z") not in ["-", ""] else latest["Close"]

        return {
            "code": code,
            "price": price,
            "prev_close": prev_close,
            "volume": latest["Volume"],
            "K": latest["K"],
            "D": latest["D"],
            "RSI": latest["RSI"],
            "MA5": latest["MA5"],
            "MA20": latest["MA20"],
            "signal": analyze_signal(df)
        }

    return None

# ========================
# 主流程
# ========================
twse_data = fetch_twse()

data_list = []
for s in stocks:
    d = get_stock_data(twse_data, s)
    if d:
        data_list.append(d)

# ========================
# 🎨 卡片 UI
# ========================
st.markdown("""
<style>
.card {
    padding: 16px;
    border-radius: 16px;
    background: #111;
    margin-bottom: 12px;
}
.red { color: #ff4b4b; }
.green { color: #00c853; }
</style>
""", unsafe_allow_html=True)

for row in data_list:
    change = row["price"] - row["prev_close"]
    color = "red" if change > 0 else "green"

    st.markdown(f"""
    <div class="card">
        <h3>{row['code']}</h3>
        <h2 class="{color}">{row['price']:.2f}</h2>

        📊 成交量：{int(row['volume']):,}<br>
        MA5：{row['MA5']:.2f} ｜ MA20：{row['MA20']:.2f}<br>
        RSI：{row['RSI']:.2f}<br>
        K：{row['K']:.2f} ｜ D：{row['D']:.2f}<br>

        🚦 {row['signal']}
    </div>
    """, unsafe_allow_html=True)

# 更新時間
st.caption(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

time.sleep(15)
st.rerun()