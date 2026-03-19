import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")

st.title("📅 員工排班登記表")

# --- 1. Google 設定 ---
# 提交用的 Form URL
FORM_URL = "https://docs.google.com"

# 表單欄位 ID
ENTRY_NAME = "entry.2117462394"   # 姓名
ENTRY_DATE = "entry.1676285197"    # 日期
ENTRY_SHIFT = "entry.193877192"   # 班別

# ⚠️ 請在此替換為你「發佈到網路」產生的 CSV 連結 ⚠️
# 範例格式：https://docs.google.com
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pubhtml"

# --- 2. 函式定義 ---

# 當班別改變時，重置日期選單
def reset_dates():
    st.session_state.reset_key += 1

# 提交資料到 Google Form
def submit_to_google_form(name, records):
    success_count = 0
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    for r in records:
        payload = {
            ENTRY_NAME: name,
            ENTRY_DATE: r["date"],
            ENTRY_SHIFT: r["shift"]
        }
        try:
            res = requests.post(FORM_URL, data=payload, headers=headers)
            if res.status_code == 200:
                if "登入" in res.text or "Google 帳戶" in res.text:
                    st.error(f"❌ 提交失敗：表單要求登入。請關閉 Google 表單的「限制填寫一次」。")
                    return -1
                success_count += 1
            else:
                st.error(f"❌ 日期 {r['date']} 失敗，代碼：{res.status_code}")
        except Exception as e:
            st.error(f"❌ 網路錯誤：{e}")
    return success_count

# 從雲端抓取資料 (快取 10 秒)
@st.cache_data(ttl=10)
def get_cloud_data(url):
    try:
        # 強制讀取最新 CSV
        df = pd.read_csv(url)
        return df
    except Exception:
        return None

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

# 第 1 步：選擇姓名
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox(
    "👤 1. 選擇姓名", 
    staff_list, 
    key=f"name_select_{st.session_state.global_reset_key}"
)

# 第 2 步：選擇班別
selected_shift = st.radio(
    "⏰ 2. 選擇班別", 
    ["早", "晚", "休"], 
    horizontal=True, 
    on_change=reset_dates
)

# 第 3 步：選擇日期
today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

selected_dates = st.multiselect(
    "🗓️ 3. 選擇日期 (選好班別再選日期)", 
    options=date_options, 
    key=f"date_selector_{st.session_state.reset_key}"
)

# 加入按鈕
if st.button("➕ 加入預覽清單", use_container_width=True):
    if name == "請選擇":
        st.error("⚠️ 請先選擇姓名")
    elif not selected_dates:
        st.warning("⚠️ 請選擇日期")
    else:
        st.session_state.submitted = False
        for d in selected_dates:
            # 避免重複日期不同班別
            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})
        st.success(f"已加入預覽：{len(selected_dates)} 筆")

st.write("---")

# --- 5. 顯示與提交 ---
if st.session_state.records:
    st.subheader("📍 本次登記預覽")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清除預覽", use_container_width=True):
            st.session_state.records = []
            st.session_state.reset_key += 1
            st.rerun() 
    with col2:
        if st.button("🚀 確認提交到雲端", type="primary", use_container_width=True):
            with st.spinner('正在提交資料...'):
                count = submit_to_google_form(name, st.session_state.records)
                if count == len(st.session_state.records):
                    st.session_state.submitted = True
                    st.balloons()
                elif count > 0:
                    st.warning(f"⚠️ 僅成功提交 {count} 筆。")

if st.session_state.submitted:
    st.success(f"✅ 成功提交！資料已同步至雲端。")
    if st.button("✨ 點我重置清空", use_container_width=True):
        st.session_state.records = []
        st.session_state.reset_key += 1
        st.session_state.global_reset_key += 1
        st.session_state.submitted = False
        st.cache_data.clear() # 強制清除快取以獲取最新雲端資料
        st.rerun()

# --- 6. 雲端總表顯示 (所有人看這裡) ---
st.write("---")
st.subheader("📊 雲端即時排班總表")

# 按鈕：手動重新整理
if st.button("🔄 刷新雲端資料", use_container_width=True):
    st.cache_data.clear()

# 抓取雲端 CSV 資料
all_data = get_cloud_data(SHEET_CSV_URL)

if all_data is not None and not all_data.empty:
    # 嘗試依日期排序（需與你的試算表標題一致）
    try:
        # 假設你的標題叫「日期」，如果不是請修改這裡
        if "日期" in all_data.columns:
            all_data = all_data.sort_values(by="日期", ascending=True)
    except:
        pass
        
    st.dataframe(all_data, use_container_width=True, hide_index=True)
    st.caption(f"最後同步時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.info("💡 提醒：Google 雲端同步約有 1-5 分鐘延遲，若剛提交沒看到是正常的。")
else:
    st.warning("⚠️ 無法讀取雲端資料。請檢查：1. 是否已「發佈到網路」 2. 網址是否正確。")
