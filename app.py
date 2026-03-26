import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered", page_icon="📅")

st.title("📅 員工預班登記表")

# --- 1. 外部連結設定 ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"

# 請確保這些 ID 與你的 Google Form 原始碼一致
ENTRY_NAME = "entry.2117462394"   
ENTRY_DATE = "entry.1676285197"   
ENTRY_SHIFT = "entry.193877192"  

# Google 試算表發佈連結 (CSV)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1144015050&single=true&output=csv"

# --- 2. 核心功能函數 ---

def get_cloud_data():
    """從雲端抓取目前的登記紀錄，並自動處理欄位名稱"""
    try:
        # 加上隨機參數防止快取
        df = pd.read_csv(f"{SHEET_CSV_URL}&t={datetime.now().timestamp()}")
        # 移除欄位名稱前後空白
        df.columns = [c.strip() for c in df.columns]
        
        # 尋找日期欄位
        possible_date_cols = ['日期', 'Date', '時間戳記', 'Timestamp']
        date_col = next((c for c in possible_date_cols if c in df.columns), None)
        
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
            df = df.rename(columns={date_col: '日期'})
        return df
    except:
        return pd.DataFrame()

def submit_to_google_form(name, records):
    """提交資料到 Google Form"""
    success_count = 0
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    for r in records:
        payload = {ENTRY_NAME: name, ENTRY_DATE: r["date"], ENTRY_SHIFT: r["shift"]}
        try:
            res = requests.post(FORM_URL, data=payload, headers=headers)
            if res.status_code == 200:
                success_count += 1
        except:
            pass
    return success_count

# --- 3. 初始化 Session State ---
if "records" not in st.session_state:
    st.session_state.records = []
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "global_reset_key" not in st.session_state:
    st.session_state.global_reset_key = 0

# --- 4. 介面設計 ---
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox("👤 1. 選擇姓名", staff_list, key=f"name_{st.session_state.global_reset_key}")

selected_shift = st.radio("⏰ 2. 選擇班別", ["早", "晚", "休", "不接組"], horizontal=True)

today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]
selected_dates = st.multiselect("🗓️ 3. 選擇日期", options=date_options, key=f"dates_{st.session_state.reset_key}")

# --- 5. 加入清單與人數檢查 ---
if st.button("➕ 加入預覽清單", use_container_width=True):
    if name == "請選擇" or not selected_dates:
        st.warning("⚠️ 請填妥姓名與日期")
    else:
        cloud_df = get_cloud_data()
        limit_errors = []
        
        for d in selected_dates:
            if selected_shift == "休":
                # 統計該日雲端休息人數 (排除目前使用者)
                cloud_count = 0
                if not cloud_df.empty and '日期' in cloud_df.columns and '班別' in cloud_df.columns:
                    name_col = '姓名' if '姓名' in cloud_df.columns else cloud_df.columns[1] # 備援機制
                    cloud_count = len(cloud_df[(cloud_df["日期"] == d) & (cloud_df["班別"] == "休") & (cloud_df[name_col] != name)])
                
                # 統計預覽區人數
                preview_count = len([r for r in st.