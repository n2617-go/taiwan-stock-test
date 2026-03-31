import streamlit as st
import requests
import time
from datetime import datetime

st.set_page_config(page_title="即時台股股價", layout="wide")
st.title("📈 即時台股股價")
st.caption("資料來源：TWSE 官方 API（5秒更新） • 台積電、中鋼、台化、台塑化")

stocks = [
    {"id": "2330", "name": "台積電"},
    {"id": "2002", "name": "中鋼"},
    {"id": "1326", "name": "台化"},
    {"id": "6505", "name": "台塑化"}
]

def fetch_data():
    ex_ch = "|".join([f"tse_{s['id']}.tw" for s in stocks])
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&json=1"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get("msgArray", [])
    except:
        return None

if "last_data" not in st.session_state:
    st.session_state.last_data = None

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 手動刷新", use_container_width=True):
        st.rerun()

data = fetch_data()
if data:
    st.session_state.last_data = data

if st.session_state.last_data:
    rows = []
    for stock in st.session_state.last_data:
        code = stock["c"]
        name = stock["n"]
        price = float(stock.get("z") or 0)
        prev = float(stock.get("y") or 0)
        volume = int(stock.get("v") or 0)
        
        is_closed = stock.get("z") in [None, "-", ""]
        if is_closed or price == 0:
            price = prev
        
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0
        
        rows.append({
            "股票名稱": name,
            "代碼": code,
            "最新價": f"{price:.2f} {'(收盤)' if is_closed else ''}",
            "昨收": f"{prev:.2f}",
            "漲跌": f"{'▲' if change > 0 else '▼'} {change:.2f}",
            "漲跌幅": f"{change_pct:+.2f}%",
            "累計成交量": f"{volume:,}"
        })
    
    st.dataframe(rows, use_container_width=True, hide_index=True)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"最後更新：{now}（每15秒自動更新）")
else:
    st.error("暫時無法取得資料，請稍後再試")

# 自動刷新
time.sleep(15)
st.rerun()
