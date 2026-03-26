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

# --- 雲端資料設定 ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1144015050&single=true&output=csv"

@st.cache_data(ttl=30)  # 每30秒自動更新一次
def get_cloud_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        # 強制把所有欄位轉成字串，避免型別問題
        df = df.astype(str).apply(lambda x: x.str.strip())
        return df
    except Exception as e:
        st.error(f"❌ 無法讀取雲端資料: {e}")
        return None

# === 強力版「休」班檢查（已加入完整除錯資訊）===
def check_rest_violations(cloud_df, selected_name, selected_shift, selected_dates):
    if selected_shift != "休" or cloud_df is None or cloud_df.empty:
        return [], None  # 回傳違規日期 + 除錯資訊

    # ====================== 自動偵測欄位（超強版）======================
    df_cols = list(cloud_df.columns)

    # 1. 日期欄位
    date_col = None
    for possible in ["日期", "Date", "日期 ", "日期(YYYY-MM-DD)", "date"]:
        if possible in df_cols:
            date_col = possible
            break
    if date_col is None:
        # 找含有「日」或看起來像日期的欄位
        for col in df_cols:
            if any(char in str(col) for char in ["日", "date", "Date"]):
                date_col = col
                break

    # 2. 班別欄位
    shift_col = None
    shift_keywords = {"早", "晚", "休", "不接組"}
    for col in df_cols:
        unique_vals = set(cloud_df[col].dropna().astype(str).str.strip().unique())
        if shift_keywords & unique_vals:
            shift_col = col
            break
    if shift_col is None:
        for col in df_cols:
            if "班" in str(col) or "shift" in str(col).lower():
                shift_col = col
                break

    # 3. 姓名欄位
    name_col = None
    for possible in ["姓名", "Name", "name", "員工姓名"]:
        if possible in df_cols:
            name_col = possible
            break
    if name_col is None:
        for col in df_cols:
            if "姓名" in str(col) or "name" in str(col).lower():
                name_col = col
                break

    # ====================== 除錯資訊打包 ======================
    debug_info = {
        "所有欄位": df_cols,
        "偵測到的日期欄位": date_col,
        "偵測到的班別欄位": shift_col,
        "偵測到的姓名欄位": name_col,
        "雲端總筆數": len(cloud_df),
        "休班總筆數": 0,
    }

    if date_col is None or shift_col is None:
        debug_info["錯誤原因"] = "無法找到日期或班別欄位"
        return [], debug_info

    # ====================== 篩選休班資料 ======================
    rest_df = cloud_df[cloud_df[shift_col].str.strip() == "休"].copy()
    debug_info["休班總筆數"] = len(rest_df)

    if rest_df.empty or date_col not in rest_df.columns:
        return [], debug_info

    # 計算每個日期的休班人數（唯一姓名）
    if name_col and name_col in rest_df.columns:
        date_to_count = rest_df.groupby(date_col)[name_col].nunique().to_dict()
        date_to_names = {
            d: set(group[name_col].astype(str).str.strip())
            for d, group in rest_df.groupby(date_col)
        }
    else:
        date_to_count = rest_df.groupby(date_col).size().to_dict()
        date_to_names = {}

    # ====================== 檢查本次是否違規 ======================
    violating_dates = []
    for d in selected_dates:
        current_count = date_to_count.get(d, 0)
        already = False
        if name_col and d in date_to_names:
            already = selected_name in date_to_names[d]
        projected = current_count if already else current_count + 1
        if projected > 3:
            violating_dates.append(d)

    return violating_dates, debug_info

# 當班別改變時重置日期
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

if st.button("➕ 加入預覽清單", use_container_width=True, type="primary"):
    if name == "請選擇":
        st.error("⚠️ 請先選擇姓名")
    elif not selected_dates:
        st.warning("⚠️ 請選擇日期")
    else:
        cloud_df = get_cloud_data()
        
        # === 執行休班檢查 ===
        violating_dates, debug_info = check_rest_violations(cloud_df, name, selected_shift, selected_dates)
        
        # === 顯示警示（如果有違規）===
        if violating_dates:
            st.error(
                f"🚨 **休班超過3人上限！**\n\n"
                f"以下日期登記「休」後將超過3人：\n"
                f"**{', '.join(violating_dates)}**\n\n"
                f"目前雲端人數 + 您本次登記 > 3\n"
                f"請調整日期或與主管討論！"
            )
        elif selected_shift == "休":
            st.success("✅ 本次登記「休」未超過3人上限")
        
        # === 加入預覽（無論是否違規都允許）===
        st.session_state.submitted = False
        for d in selected_dates:
            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})
        st.success(f"已加入預覽：{len(selected_dates)} 筆 ({selected_shift}班)")

        # === 顯示除錯資訊（僅當選擇休班時出現）===
        if selected_shift == "休":
            with st.expander("🔍 休班檢查除錯資訊（點我展開）", expanded=False):
                st.write("**雲端資料欄位：**", debug_info["所有欄位"])
                st.write("**偵測到的日期欄位：**", debug_info["偵測到的日期欄位"])
                st.write("**偵測到的班別欄位：**", debug_info["偵測到的班別欄位"])
                st.write("**偵測到的姓名欄位：**", debug_info["偵測到的姓名欄位"])
                st.write(f"**雲端總休班筆數：** {debug_info['休班總筆數']}")
                if debug_info.get("錯誤原因"):
                    st.error(f"❌ 檢查失敗原因：{debug_info['錯誤原因']}")

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

# --- 5. 雲端總表 ---
st.write("---")
st.subheader("📊 雲端預班總表")

if st.button("🔄 查看/重新整理登記表", use_container_width=True):
    st.cache_data.clear()

all_data = get_cloud_data()
if all_data is not None and not all_data.empty:
    st.dataframe(all_data, use_container_width=True, hide_index=True)
    tw_time = datetime.utcnow() + timedelta(hours=8)
    st.caption(f"最後更新時間 (UTC+8)：{tw_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.info("目前雲端尚無資料，或尚未發佈到網路。")