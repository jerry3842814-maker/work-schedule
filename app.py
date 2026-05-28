import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")
st.title("📅 員工預班登記表")

# --- 1. Google 表單設定 ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"
ENTRY_NAME = "entry.2117462394"  # 姓名
ENTRY_DATE = "entry.1676285197"  # 日期
ENTRY_SHIFT = "entry.193877192"  # 班別

# --- 2. Google Sheet CSV 設定 ---
REST_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1672423289&single=true&output=csv"
TOTAL_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1144015050&single=true&output=csv"
REST_LIMIT = 3   # 提醒門檻（超過3人仍可登記）

# =========================
# 工具函式
# =========================
def clean_columns(df):
    """清理欄位名稱，避免 BOM / 空白問題"""
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df

def normalize_text(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def normalize_date(val):
    """將日期統一轉成 YYYY-MM-DD"""
    text = normalize_text(val)
    if not text:
        return None
    dt = pd.to_datetime(text, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.strftime("%Y-%m-%d")

def reset_dates():
    st.session_state.reset_key += 1

@st.cache_data(ttl=30)
def get_rest_data():
    """讀取休班檢查資料"""
    try:
        df = pd.read_csv(REST_CSV_URL)
        df = clean_columns(df)
        return df
    except Exception as e:
        st.error(f"❌ 無法讀取休班檢查資料：{e}")
        return None

@st.cache_data(ttl=30)
def get_total_data():
    """讀取總表資料"""
    try:
        df = pd.read_csv(TOTAL_CSV_URL)
        df = clean_columns(df)
        return df
    except Exception as e:
        st.error(f"❌ 無法讀取總表資料：{e}")
        return None

def build_simulated_records(current_records, selected_dates, selected_shift):
    """模擬加入後的預覽資料"""
    new_records = [r for r in current_records if r["date"] not in selected_dates]
    for d in selected_dates:
        new_records.append({"date": d, "shift": selected_shift})
    return new_records

def analyze_rest_data(cloud_df):
    """從雲端資料中分析休班狀況"""
    if cloud_df is None or cloud_df.empty:
        return {}
    df = cloud_df.copy()
    df = clean_columns(df)
    date_col = "請選擇日期" if "請選擇日期" in df.columns else None
    shift_col = "請選擇班別或休假" if "請選擇班別或休假" in df.columns else None
    name_col = "姓名" if "姓名" in df.columns else None
    if not date_col or not shift_col or not name_col:
        return {}
    df[date_col] = df[date_col].apply(normalize_text)
    df[shift_col] = df[shift_col].apply(normalize_text)
    df[name_col] = df[name_col].apply(normalize_text)
    rest_df = df[df[shift_col] == "休"].copy()
    if rest_df.empty:
        return {}
    rest_df["normalized_date"] = rest_df[date_col].apply(normalize_date)
    rest_df = rest_df[rest_df["normalized_date"].notna()].copy()
    date_to_names = (
        rest_df.groupby("normalized_date")[name_col]
        .apply(lambda x: set(v for v in x if v))
        .to_dict()
    )
    return date_to_names

def get_full_rest_dates(cloud_df):
    """取得目前『休』已達或超過3人的日期（用來提醒）"""
    date_to_names = analyze_rest_data(cloud_df)
    full_dates = sorted([d for d, names in date_to_names.items() if len(names) >= REST_LIMIT])
    return full_dates

def check_rest_violations(cloud_df, selected_name, records_to_check):
    """檢查預覽中的『休』是否超過3人（僅提醒，不阻擋）"""
    date_to_names = analyze_rest_data(cloud_df)
    violating_dates = []
    for r in records_to_check:
        if r["shift"] != "休":
            continue
        d = r["date"]
        existing_names = date_to_names.get(d, set())
        projected_count = len(existing_names) if selected_name in existing_names else len(existing_names) + 1
        if projected_count > REST_LIMIT:
            violating_dates.append(d)
    violating_dates = sorted(list(set(violating_dates)))
    return violating_dates

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
                    st.error("❌ 提交失敗：表單要求登入。請關閉 Google 表單的「限制填寫一次」。")
                    return -1
                success_count += 1
            else:
                st.error(f"❌ 日期 {r['date']} 提交失敗，代碼：{res.status_code}")
        except Exception as e:
            st.error(f"❌ 網路錯誤：{e}")
    return success_count

# =========================
# Session 初始化
# =========================
if "records" not in st.session_state:
    st.session_state.records = []
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "global_reset_key" not in st.session_state:
    st.session_state.global_reset_key = 0

# =========================
# 介面
# =========================
staff_list = [
    "請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志",
    "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"
]
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

# 先抓休班已滿日期（用來提醒）
cloud_rest_df = get_rest_data()
full_rest_dates = get_full_rest_dates(cloud_rest_df) if cloud_rest_df is not None else []

# 當選「休」時，直接顯示提醒（功能保留）
if selected_shift == "休":
    if full_rest_dates:
        st.warning("⚠️ 以下日期「休」已達或超過 3 人：" + "、".join(full_rest_dates))
        st.caption("日期選單中標示「（休已滿）」的日期仍可登記，但請注意人數。")
    else:
        st.info("✅ 目前沒有日期的「休」達到 3 人。")

selected_dates = st.multiselect(
    "🗓️ 3. 選擇日期 (選好班別再選日期