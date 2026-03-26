import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")

st.title("📅 員工預班登記表")

# --- 1. Google 表單與試算表設定 ---
# 提交用的 Google Form URL (結尾須為 formResponse)
FORM_URL = "https://docs.google.com"

# 請確保這些 Entry ID 與你的表單欄位對應
ENTRY_NAME = "entry.2117462394"   # 姓名
ENTRY_DATE = "entry.1676285197"    # 日期
ENTRY_SHIFT = "entry.193877192"   # 班別

# 讀取用的 CSV 連結 (試算表需「發佈到網路」並選擇 CSV 格式)
SHEET_CSV_URL = "https://docs.google.com"

# --- 2. 功能函式 ---

def get_cloud_data():
    """從雲端抓取最新資料"""
    try:
        # 加入 timestamp 避免快取舊資料
        url = f"{SHEET_CSV_URL}&t={datetime.now().timestamp()}"
        df = pd.read_csv(url)
        # 確保日期欄位是字串，方便比對
        if "日期" in df.columns:
            df["日期"] = df["日期"].astype(str)
        return df
    except Exception as e:
        return None

def submit_to_google_form(name, records):
    """提交資料到 Google 表單"""
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

def reset_dates():
    """切換班別時重置日期選單"""
    st.session_state.reset_key += 1

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
    ["早", "晚", "休", "不接組"], 
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

# --- 核心：加入預覽並檢查人數 ---
if st.button("➕ 加入預覽清單", use_container_width=True):
    if name == "請選擇":
        st.error("⚠️ 請先選擇姓名")
    elif not selected_dates:
        st.warning("⚠️ 請選擇日期")
    else:
        # 抓取雲端資料進行比對
        cloud_df = get_cloud_data()
        overlimit_dates = []
        
        for d in selected_dates:
            if selected_shift == "休":
                # 統計雲端該日已有的「休」人數 (請確認 CSV 欄位名稱是否為 '日期' 與 '班別')
                cloud_count = 0
                if cloud_df is not None and not cloud_df.empty:
                    cloud_count = len(cloud_df[(cloud_df['日期'] == d) & (cloud_df['班別'] == "休")])
                
                # 統計目前預覽清單中是否也有別人重複點到 (防呆)
                preview_count = len([r for r in st.session_state.records if r["date"] == d and r["shift"] == "休"])
                
                total_off = cloud_count + preview_count
                if total_off >= 3:
                    overlimit_dates.append(f"{d} (已有 {total_off} 人休)")

        if overlimit_dates:
            st.error(f"❌ 無法加入：以下日期「休」的人數已達上限(3人)：\n\n" + "\n".join(overlimit_dates))
        else:
            st.session_state.submitted = False
            for d in selected_dates:
                # 覆蓋掉同日期的舊紀錄
                st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
                st.session_state.records.append({"date": d, "shift": selected_shift})
            st.success(f"已加入預覽：{len(selected_dates)} 筆 ({selected_shift}班)")

st.write("---")

# --- 5. 顯示與提交 ---
if st.session_state.records:
    st.subheader("📍 目前登記預覽")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ 清除預覽與日期", use_container_width=True):
            st.session_state.records = []
            st.session_state.reset_key += 1 
            st.session_state.submitted = False
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
    if st.button("✨ 點我清空內容", use_container_width=True):
        st.session_state.records = []
        st.session_state.reset_key += 1
        st.session_state.global_reset_key += 1
        st.session_state.submitted = False
        st.rerun()

# --- 6. 顯示雲端所有人的登記紀錄 ---
st.write("---")
st.subheader("📊 雲端預班總表")

if st.button("🔄 重新讀取雲端資料"):
    st.cache_data.clear()

all_data = get_cloud_data()

if all_data is not None and not all_data.empty:
    # 依日期排序
    if "日期" in all_data.columns:
        all_data = all_data.sort_values(by="日期", ascending=True)
        
    st.dataframe(all_data, use_container_width=True, hide_index=True)
    
    tw_time = datetime.utcnow() + timedelta(hours=8)
    st.caption(f"最後更新時間 (UTC+8)：{tw_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.info("目前雲端尚無資料，或 Google 試算表尚未「發佈到網路」。")
