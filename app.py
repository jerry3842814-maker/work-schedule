import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered", page_icon="📅")

st.title("📅 員工預班登記表")

# --- 1. 外部連結設定 ---
# 提交用的 Google 表單 URL (需確認結尾為 formResponse)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"

# 表單欄位 ID (請確認與你的表單一致)
ENTRY_NAME = "entry.2117462394"   # 姓名
ENTRY_DATE = "entry.1676285197"   # 日期
ENTRY_SHIFT = "entry.193877192"  # 班別

# 讀取用的 Google 試算表 CSV 連結 (需先「發佈到網路」)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1144015050&single=true&output=csv"

# --- 2. 核心功能函數 ---

def get_cloud_data():
    """從雲端抓取目前的登記紀錄"""
    try:
        # 加上 random 參數防止瀏覽器快取舊資料
        df = pd.read_csv(f"{SHEET_CSV_URL}&t={datetime.now().timestamp()}")
        if "日期" in df.columns:
            # 統一日期格式為 YYYY-MM-DD 方便比對
            df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
        return df
    except Exception as e:
        st.sidebar.error(f"無法讀取雲端資料: {e}")
        return pd.DataFrame()

def submit_to_google_form(name, records):
    """將清單送出至 Google 表單"""
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
                success_count += 1
            else:
                st.error(f"❌ {r['date']} 提交失敗")
        except Exception as e:
            st.error(f"❌ 網路錯誤：{e}")
    return success_count

def reset_dates():
    """重置日期選單"""
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

# 步驟 1：選擇姓名
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox(
    "👤 1. 選擇姓名", 
    staff_list, 
    key=f"name_select_{st.session_state.global_reset_key}"
)

# 步驟 2：選擇班別
selected_shift = st.radio(
    "⏰ 2. 選擇班別", 
    ["早", "晚", "休", "不接組"], 
    horizontal=True, 
    on_change=reset_dates
)

# 步驟 3：選擇日期
today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

selected_dates = st.multiselect(
    "🗓️ 3. 選擇日期 (休假名額有限)", 
    options=date_options, 
    key=f"date_selector_{st.session_state.reset_key}"
)

# --- 5. 加入清單與人數檢查 ---
if st.button("➕ 加入預覽清單", use_container_width=True):
    if name == "請選擇":
        st.error("⚠️ 請先選擇姓名")
    elif not selected_dates:
        st.warning("⚠️ 請選擇日期")
    else:
        # 即時獲取雲端資料進行比對
        cloud_df = get_cloud_data()
        limit_errors = []
        
        for d in selected_dates:
            if selected_shift == "休":
                # 計算雲端已有多少人休 (排除自己)
                cloud_count = 0
                if not cloud_df.empty and "日期" in cloud_df.columns and "班別" in cloud_df.columns:
                    # 假設雲端欄位名稱為 '日期', '班別', '姓名'
                    cloud_count = len(cloud_df[(cloud_df["日期"] == d) & (cloud_df["班別"] == "休") & (cloud_df["姓名"] != name)])
                
                # 計算目前預覽區內有多少人休 (同一批操作)
                preview_count = len([r for r in st.session_state.records if r["date"] == d and r["shift"] == "休"])
                
                total_off = cloud_count + preview_count
                
                if total_off >= 3:
                    limit_errors.append(f"{d} (已有 {total_off} 人休)")
                    continue # 跳過此日期的加入

            # 如果檢查通過或不是選「休」，則加入紀錄
            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})

        if limit_errors:
            st.error(f"❌ 以下日期休息人數已滿 (上限3人)，無法加入：\n\n" + "、".join(limit_errors))
        
        if len(selected_dates) > len(limit_errors):
            st.success("成功更新預覽清單")
            st.session_state.submitted = False

st.write("---")

# --- 6. 顯示與提交區 ---
if st.session_state.records:
    st.subheader("📍 目前登記預覽 (尚未送出)")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.table(df_preview) # 使用 table 較清楚
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空預覽", use_container_width=True):
            st.session_state.records = []
            st.rerun()
            
    with col2:
        if st.button("🚀 確認提交到雲端", type="primary", use_container_width=True):
            with st.spinner('正在同步至 Google...'):
                count = submit_to_google_form(name, st.session_state.records)
                if count == len(st.session_state.records):
                    st.session_state.submitted = True
                    st.balloons()
                elif count > 0:
                    st.warning(f"⚠️ 僅成功提交 {count} 筆。")

if st.session_state.submitted:
    st.success(f"✅ 提交成功！")
    if st.button("✨ 點我開始下一位登記", use_container_width=True):
        st.session_state.records = []
        st.session_state.reset_key += 1
        st.session_state.global_reset_key += 1
        st.session_state.submitted = False
        st.rerun()

# --- 7. 顯示雲端總表 ---
st.write("---")
st.subheader("📊 雲端登記現況")

if st.button("🔄 重新整理雲端資料"):
    st.cache_data.clear()

all_data = get_cloud_data()
if not all_data.empty:
    # 顯示過濾後的資料 (例如顯示今天以後的登記)
    display_df = all_data[all_data['日期'] >= str(today)].sort_values(by=["日期", "班別"])
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    tw_time = datetime.now() + timedelta(hours=8)
    st.caption(f"資料來源：Google Sheet | 更新時間：{tw_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.info("目前雲端尚無資料，或尚未「發佈到網路」。")