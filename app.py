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

# --- 雲端資料設定（移到最前面，確保隨時可用）---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1144015050&single=true&output=csv"

def get_cloud_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        if "日期" in df.columns:
            df = df.sort_values(by="日期", ascending=True)
        return df
    except Exception:
        return None

# === 改進版：檢查「休」班是否超過3人（唯一姓名計數）===
def check_rest_violations(cloud_df, selected_name, selected_shift, selected_dates):
    """檢查即將登記的「休」日期是否會使人數超過3人（支援唯一姓名計數）"""
    if selected_shift != "休" or cloud_df is None or cloud_df.empty or "日期" not in cloud_df.columns:
        return []

    # ==================== 改進欄位自動偵測 ====================
    # 1. 找班別欄位（優先精確比對「休」「早」「晚」等值）
    shift_col = None
    shift_options = {"早", "晚", "休", "不接組"}
    for col in cloud_df.columns:
        vals = cloud_df[col].dropna().astype(str).str.strip().unique()
        if shift_options & set(vals):
            shift_col = col
            break

    # 2. 若沒找到，再用欄位名稱 fallback
    if shift_col is None:
        for col in cloud_df.columns:
            if isinstance(col, str) and ("班" in col or "shift" in str(col).lower()):
                shift_col = col
                break

    if shift_col is None:
        return []  # 無法偵測班別欄位，不顯示警告

    # 3. 找姓名欄位
    name_col = next((col for col in cloud_df.columns if isinstance(col, str) and "姓名" in col), None)
    if name_col is None:
        for col in cloud_df.columns:
            if isinstance(col, str) and ("name" in str(col).lower()):
                name_col = col
                break

    # ==================== 篩選「休」班資料 ====================
    rest_df = cloud_df[cloud_df[shift_col].astype(str).str.strip() == "休"]
    if rest_df.empty:
        return []

    # 計算每個日期的「休」人數（唯一姓名）
    if name_col and name_col in rest_df.columns:
        date_to_count = rest_df.groupby("日期")[name_col].nunique().to_dict()
        date_to_names = {
            date: set(group[name_col].dropna().astype(str).str.strip())
            for date, group in rest_df.groupby("日期")
        }
    else:
        # 無姓名欄位時 fallback 成總筆數
        date_to_count = rest_df.groupby("日期").size().to_dict()
        date_to_names = {}

    # ==================== 檢查本次登記是否會超過3人 ====================
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
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox(
    "👤 1. 選擇姓名",
    staff_list,
    key=f"name_select_{st.session_state.global_reset_key}"
)

selected_shift = st.radio(
    "⏰ 2. 選擇班別",
    ["早", "晚", "休", "不接組"],
    horizontal=True,
    on_change=reset_dates
)

today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

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
        # === 關鍵修正：檢查「休」班是否超過3人 ===
        cloud_df = get_cloud_data()
        violating_dates = check_rest_violations(cloud_df, name, selected_shift, selected_dates)
        
        if violating_dates:
            st.warning(
                f"⚠️ **重要警示**：以下日期登記「休」將超過3人上限！\n"
                f"🚨 違規日期：{', '.join(violating_dates)}\n"
                f"（目前雲端已登記人數 + 您本次登記 > 3）\n"
                f"請與主管討論或調整班別。"
            )
        
        # 正常加入預覽（警示後仍可繼續登記）
        st.session_state.submitted = False
        for d in selected_dates:
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

# 按鈕：手動重新整理
if st.button("🔄 查看/重新整理登記表"):
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