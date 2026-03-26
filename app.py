import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")
st.title("📅 員工預班登記表")

# --- 1. Google 表單設定 ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"
ENTRY_NAME = "entry.2117462394"   # 姓名
ENTRY_DATE = "entry.1676285197"   # 日期
ENTRY_SHIFT = "entry.193877192"   # 班別

# 當班別改變時，增加 reset_key 以重置日期選單
def reset_dates():
    st.session_state.reset_key += 1

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

# === 新增功能：檢查「休」班是否超過3人（唯一姓名計數）===
def check_rest_violations(cloud_df, selected_name, selected_shift, selected_dates):
    """檢查即將登記的「休」日期是否會使人數超過3人（支援唯一姓名計數）"""
    if selected_shift != "休" or cloud_df is None or cloud_df.empty or "日期" not in cloud_df.columns:
        return []
    
    # 自動偵測「班別」欄位（優先用內容值，其次用欄位名稱）
    shift_col = None
    for col in cloud_df.columns:
        try:
            if cloud_df[col].astype(str).str.contains(r"早|晚|休|不接組", na=False, regex=True).any():
                shift_col = col
                break
        except:
            pass
    if shift_col is None:
        shift_col = next((col for col in cloud_df.columns if isinstance(col, str) and "班" in col), None)
    
    if shift_col is None:
        return []
    
    # 自動偵測「姓名」欄位
    name_col = next((col for col in cloud_df.columns if isinstance(col, str) and "姓名" in col), None)
    
    # 篩選「休」班資料
    rest_df = cloud_df[cloud_df[shift_col].astype(str) == "休"]
    if rest_df.empty:
        return []
    
    # 計算每個日期的「休」人數（唯一姓名）
    if name_col:
        date_to_count = rest_df.groupby("日期")[name_col].nunique().to_dict()
        date_to_names = {date: set(group[name_col].dropna().astype(str)) 
                        for date, group in rest_df.groupby("日期")}
    else:
        # 無姓名欄位時改用總筆數（fallback）
        date_to_count = rest_df.groupby("日期").size().to_dict()
        date_to_names = {}
    
    violating_dates = []
    for d in selected_dates:
        current_count = date_to_count.get(d, 0)
        already_registered = False
        if name_col and d in date_to_names:
            already_registered = selected_name in date_to_names[d]
        
        projected_count = current_count if already_registered else current_count + 1
        if projected_count > 3:
            violating_dates.append(d)
    
    return violating_dates

# --- 2. 初始化 ---
if "records" not in st.session_state:
    st.session_state.records = []
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "global_reset_key" not in st.session_state:
    st.session_state.global_reset_key = 0

# --- 3. 介面設計 ---
# 姓名選單使用 global_reset_key，只有「全部清空」時才會重置
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox(
    "👤 1. 選擇姓名",
    staff_list,
    key=f"name_select_{st.session_state.global_reset_key}"
)

# 第 2 步：選擇班別 (加入 on_change 事件)
selected_shift = st.radio(
    "⏰ 2. 選擇班別",
    ["早", "晚", "休", "不接組"],
    horizontal=True,
    on_change=reset_dates
)

# 第 3 步：選擇日期
today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

# 日期選單使用 reset_key，不論是切換班別或局部清除都會重置
selected_dates = st.multiselect(
    "🗓️ 3. 選擇日期 (選好班別再選日期)",
    options=date_options,
    key=f"date_selector_{st.session_state.reset_key}"
)

if st.button("➕ 加入預覽清單", use_container_width=True):
    if name == "請選擇":
        st.error("⚠️ 請先選擇姓名")
    elif not selected_dates:
        st.warning("⚠️ 請選擇日期")
    else:
        # === 新增：檢查「休」班是否超過3人 ===
        cloud_df = get_cloud_data() if "get_cloud_data" in globals() else None
        violating_dates = check_rest_violations(cloud_df, name, selected_shift, selected_dates)
        
        if violating_dates:
            st.warning(
                f"⚠️ **重要警示**：以下日期登記「休」將超過3人上限！\n"
                f"{', '.join(violating_dates)}\n"
                f"（系統已計算目前雲端人數 + 您本次登記）\n"
                f"請確認是否仍要加入，或與主管討論調整。"
            )
        
        # 正常加入預覽（即使有警示仍允許登記）
        st.session_state.submitted = False
        for d in selected_dates:
            # 移除同日期舊記錄（避免重複）
            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})
        st.success(f"已加入預覽：{len(selected_dates)} 筆 ({selected_shift}班)")

st.write("---")

# --- 4. 顯示與提交 ---
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
            if name == "請選擇":
                st.error("❌ 請選擇姓名")
            else:
                with st.spinner("正在提交資料..."):
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

# --- 5. 顯示雲端所有人的登記紀錄 ---
st.write("---")
st.subheader("📊 雲端預班總表")

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1144015050&single=true&output=csv"

def get_cloud_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        if "日期" in df.columns:
            df = df.sort_values(by="日期", ascending=True)
        return df
    except Exception as e:
        return None

# 按鈕：手動重新整理
if st.button("🔄 查看登記表"):
    st.cache_data.clear()

# 抓取資料並顯示
all_data = get_cloud_data()
if all_data is not None and not all_data.empty:
    st.dataframe(
        all_data,
        use_container_width=True,
        hide_index=True
    )
    tw_time = datetime.utcnow() + timedelta(hours=8)
    st.caption(f"最後更新時間 (UTC+8)：{tw_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.info("目前雲端尚無資料，或尚未發佈到網路。")