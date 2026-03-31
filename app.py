import streamlit as st
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="台股看盤神器 Pro", layout="wide")

st.title("📈 台股看盤神器 Pro")

# ========================
# ⭐ 自選股初始化（關鍵）
# ========================
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["2330", "2002"]

# ========================
# ⭐ Sidebar（穩定版）
# ========================
st.sidebar.header("⭐ 自選股")

# ➕ 新增股票
new_stock = st.sidebar.text_input("輸入股票代碼（例如 2330）")

if st.sidebar.button("新增股票"):
    if new_stock.isdigit():
        if new_stock not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_stock)
    else:
        st.sidebar.warning("請輸入正確股票代碼")

# ❌ 刪除股票
if st.session_state.watchlist:
    remove_stock = st.sidebar.selectbox("選擇刪除股票", st.session_state.watchlist)

    if st.sidebar.button("刪除股票"):
        st.session_state.watchlist.remove(remove_stock)

# ========================
# TWSE
# ========================
def fetch_twse(stock_ids):
    ex_ch = "|".join([f"tse_{s}.tw" for s in stock_ids])
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&json=1"

    try:
        r = requests.get(url, timeout=10)
        return r.json().get("msgArray", [])
    except:
        return []

# ========================
# yfinance（加強穩定）
# ========================
@st.cache_data(ttl=60)
def fetch_yf(stock_id):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="3mo")
        return df if not df.empty else None
    except:
        return None

# ========================
# 技術指標
# ========================
def add_indicators(df):
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + rs))

    return df

# ========================
# 主流程
# ========================
twse_data = fetch_twse(st.session_state.watchlist)

st.subheader("📊 即時看盤")

for code in st.session_state.watchlist:

    df = fetch_yf(code)

    if df is None:
        st.error(f"{code} 讀取失敗")
        continue

    df = add_indicators(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    price = latest["Close"]
    change = price - prev["Close"]

    color = "red" if change > 0 else "green"

    st.markdown(f"""
    <div style="
        padding:15px;
        border-radius:12px;
        background:#111;
        margin-bottom:10px;
    ">
        <h3>{code}</h3>
        <h2 style="color:{'red' if change>0 else 'green'}">
            {price:.2f}
        </h2>

        📊 成交量：{int(latest['Volume']):,}<br>
        MA5：{latest['MA5']:.2f} ｜ MA20：{latest['MA20']:.2f}<br>
        RSI：{latest['RSI']:.2f}
    </div>
    """, unsafe_allow_html=True)

# ========================
# 更新時間 + 自動刷新（正確寫法）
# ========================
st.caption(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

st.autorefresh(interval=15000, key="refresh")