import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

st.set_page_config(page_title="台股看盤神器", layout="wide")
st.title("📈 大師加持（開發中v1）")

stocks = [
    {"id": "2330", "name": "台積電"},
    {"id": "2002", "name": "中鋼"},
    {"id": "1326", "name": "台化"},
    {"id": "6505", "name": "台塑化"}
]

# ------------------------
# TWSE 即時資料
# ------------------------
def fetch_twse():
    ex_ch = "|".join([f"tse_{s['id']}.tw" for s in stocks])
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&json=1"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://mis.twse.com.tw/"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        return data.get("msgArray", [])
    except:
        return None


# ------------------------
# yfinance 歷史資料
# ------------------------
def fetch_yf_hist(stock_id):
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        df = ticker.history(period="3mo")

        if df.empty:
            return None

        return df
    except:
        return None


# ------------------------
# KD
# ------------------------
def calculate_kd(df, period=9):
    low_min = df['Low'].rolling(window=period).min()
    high_max = df['High'].rolling(window=period).max()

    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100

    df['K'] = rsv.ewm(com=2).mean()
    df['D'] = df['K'].ewm(com=2).mean()

    return df


# ------------------------
# 動能
# ------------------------
def calculate_momentum(df, period=10):
    df['Momentum'] = df['Close'] - df['Close'].shift(period)
    return df


# ------------------------
# 訊號判斷
# ------------------------
def analyze_signal(df):
    if len(df) < 2:
        return "資料不足", "無法判斷"

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signal = "觀望"

    if prev['K'] < prev['D'] and latest['K'] > latest['D']:
        signal = "📈 買進（黃金交叉）"
    elif prev['K'] > prev['D'] and latest['K'] < latest['D']:
        signal = "📉 賣出（死亡交叉）"

    trend = "🔥 上升動能" if latest['Momentum'] > 0 else "❄️ 下跌動能"

    return signal, trend


# ------------------------
# 整合單一股票資料
# ------------------------
def get_stock_data(twse_data, stock):
    code = stock["id"]
    name = stock["name"]

    # 找 TWSE
    tw = next((x for x in twse_data if x["c"] == code), None)

    # yfinance 歷史
    df = fetch_yf_hist(code)

    if df is not None and len(df) >= 2:
        prev_close = df["Close"].iloc[-2]
        open_price = df["Open"].iloc[-1]
        high = df["High"].iloc[-1]
        low = df["Low"].iloc[-1]
        yf_close = df["Close"].iloc[-1]
    else:
        prev_close = open_price = high = low = yf_close = None

    # 即時價（優先 TWSE）
    if tw:
        z = tw.get("z")
        if z not in ["-", "", None]:
            price = float(z)
        else:
            price = yf_close
    else:
        price = yf_close

    # fallback
    if prev_close is None and tw:
        prev_close = float(tw.get("y") or 0)

    # 技術指標
    if df is not None:
        df = calculate_kd(df)
        df = calculate_momentum(df)
        signal, trend = analyze_signal(df)
        latest = df.iloc[-1]
        k = latest["K"]
        d = latest["D"]
        momentum = latest["Momentum"]
    else:
        signal = trend = "無資料"
        k = d = momentum = None

    change = price - prev_close if prev_close else 0
    change_pct = (change / prev_close * 100) if prev_close else 0

    return {
        "name": name,
        "code": code,
        "price": price,
        "prev_close": prev_close,
        "open": open_price,
        "high": high,
        "low": low,
        "change": change,
        "change_pct": change_pct,
        "K": k,
        "D": d,
        "Momentum": momentum,
        "signal": signal,
        "trend": trend
    }


# ------------------------
# 主流程
# ------------------------
twse_data = fetch_twse() or []

rows = []

for s in stocks:
    data = get_stock_data(twse_data, s)
    rows.append(data)

df = pd.DataFrame(rows)

# ------------------------
# UI 顯示
# ------------------------
st.subheader("📊 即時報價")

st.dataframe(
    df[[
        "name", "code", "price", "prev_close",
        "change", "change_pct", "open", "high", "low"
    ]].rename(columns={
        "name": "股票",
        "code": "代碼",
        "price": "最新價",
        "prev_close": "昨收",
        "change": "漲跌",
        "change_pct": "漲跌幅",
        "open": "開盤",
        "high": "最高",
        "low": "最低"
    }),
    use_container_width=True,
    hide_index=True
)

st.divider()

st.subheader("📈 技術分析")

for _, row in df.iterrows():
    st.write(f"### {row['name']} ({row['code']})")

    if row["K"] is not None:
        st.write(f"K值：{row['K']:.2f} ｜ D值：{row['D']:.2f}")
        st.write(f"動能：{row['Momentum']:.2f}")
    else:
        st.write("技術資料不足")

    st.write(f"訊號：{row['signal']} ｜ {row['trend']}")
    st.divider()

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.caption(f"更新時間：{now}")

# 自動刷新
time.sleep(15)
st.rerun()