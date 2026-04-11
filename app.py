import streamlit as st
import pandas as pd
import datetime
import time
import random
import pytz
import uuid
from streamlit_gsheets import GSheetsConnection

# 1. App Configuration
st.set_page_config(page_title="Macro Tracker", layout="centered")

# --- LOAD EXTERNAL CSS ---
try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.error("style.css not found.")

# Establish connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "target_calories" not in st.session_state:
    st.session_state.target_calories = 2000

# ==========================================
# --- AUTHENTICATION & SESSION LOCK ---
# ==========================================
if not st.session_state.authenticated:
    st.title("🔒 Access")
    tab_login, tab_register = st.tabs(["Login", "Create Account"])
    
    with tab_login:
        with st.form("login_form"):
            entered_user = st.text_input("Username")
            entered_pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                if entered_user.strip() and entered_pwd.strip():
                    try:
                       with st.form("login_form"):
            entered_user = st.text_input("Username")
            entered_pwd = st.text_input("Password", type="password")
            st.markdown('<style>div[data-testid="stTextInput"]:has(input[aria-label="bot_trap"]) {display: none;}</style>', unsafe_allow_html=True)
            trap = st.text_input("bot_trap", label_visibility="collapsed")
            
            if st.form_submit_button("Sign In"):
                current_time = time.time()
                if current_time - st.session_state.last_request < 3.0:
                    st.error("⏳ Please wait...")
                    st.stop()
                st.session_state.last_request = current_time
                if trap != "": st.stop()
                
                if entered_user.strip() and entered_pwd.strip():
                    try:
                        # 1. Read data and immediately cast SessionID to string to avoid float64 errors
                        users_db = conn.read(worksheet="Users", ttl=0).dropna(subset=["Username"])
                        
                        if "SessionID" not in users_db.columns:
                            users_db["SessionID"] = ""
                            
                        # Force pandas to treat this as text
                        users_db["SessionID"] = users_db["SessionID"].astype(str)
                        
                        user_match = users_db[users_db["Username"].astype(str) == entered_user.strip()]
                        
                        if not user_match.empty and str(user_match.iloc[0]["Password"]).strip() == entered_pwd.strip():
                            # Update Session ID in Cloud
                            idx = user_match.index[0]
                            users_db.at[idx, "SessionID"] = str(st.session_state.session_id)
                            
                            conn.update(worksheet="Users", data=users_db)
                            
                            st.session_state.authenticated = True
                            st.session_state.username = entered_user.strip()
                            if "TargetCalories" in user_match.columns and pd.notna(user_match.iloc[0]["TargetCalories"]):
                                st.session_state.target_calories = int(user_match.iloc[0]["TargetCalories"])
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")
                    except Exception as e:
                        st.error(f"Login error: {str(e)}")
                            
                            st.session_state.authenticated = True
                            st.session_state.username = entered_user.strip()
                            # ... rest of your login logic

# --- HARD ANTI-SHARING CHECK ---
try:
    current_users = conn.read(worksheet="Users", ttl=0)
    cloud_sid = str(current_users.loc[current_users["Username"] == st.session_state.username, "SessionID"].values[0])
    if cloud_sid != st.session_state.session_id:
        st.session_state.authenticated = False
        st.warning("⚠️ Session expired. Account logged in from another device.")
        st.rerun()
except:
    pass

# ==========================================
# --- DATA LOADING (NOW FROM CLOUD) ---
# ==========================================
# Fetch Master Database
global_db = conn.read(worksheet="Sheet1", ttl=0).dropna(how="all")
user_log = global_db[global_db["Username"] == st.session_state.username]

# Fetch Food Library from Google Sheets (cached for 1 hour for speed)
if 'food_db' not in st.session_state:
    try:
        food_library = conn.read(worksheet="FoodLibrary", ttl=3600)
        st.session_state.food_db = food_library.sort_values("Food Item")
    except:
        st.error("Failed to load Food Library from Cloud.")
        st.stop()

# ==========================================
# --- DASHBOARD & LOGGING ---
# ==========================================
ph_tz = pytz.timezone('Asia/Manila')
local_today = datetime.datetime.now(ph_tz).date()

col_title, col_date = st.columns([2, 1])
with col_title: st.title("Tracking")
with col_date: selected_date = st.date_input("Date", local_today, label_visibility="collapsed")

date_str = selected_date.strftime("%Y-%m-%d")
todays_log = user_log[user_log["Date"].astype(str) == date_str]

# Calculate Totals
total_cals = todays_log["Calories"].sum()
total_prot = todays_log["Protein (g)"].sum()
total_carbs = todays_log["Carbs (g)"].sum()
total_fats = todays_log["Fats (g)"].sum()
cal_goal = st.session_state.target_calories

# --- GLOW CARD ---
st.progress(min(max(total_cals / cal_goal, 0.0), 1.0))
glow_class = "glow-red" if total_cals > cal_goal else "glow-green"
st.markdown(f'<div class="glow-card {glow_class}"><div class="glow-label">Energy Status</div><div class="glow-value">{total_cals:.0f} / {cal_goal} kcal</div></div><br>', unsafe_allow_html=True)

# Metrics Row
m2, m3, m4 = st.columns(3)
m2.metric("PROTEIN", f"{total_prot:.0f}g")
m3.metric("CARBS", f"{total_carbs:.0f}g")
m4.metric("FATS", f"{total_fats:.0f}g")

st.divider()

# ==========================================
# --- SMART QUICK LOG & ENTRY FORMS ---
# ==========================================
st.write("### ⚡ Recently Logged")
if not user_log.empty:
    recent = user_log.sort_values(['Date'], ascending=False).drop_duplicates(subset=['Food Item']).head(5)
    cols = st.columns(len(recent))
    for i, (idx, row) in enumerate(recent.iterrows()):
        label = row['Food Item'].replace("⚡ ", "").replace("⭐ ", "")[:12]
        if cols[i].button(label, key=f"q_{i}"):
            new = pd.DataFrame([{"Username": st.session_state.username, "Date": date_str, "Meal": row['Meal'], "Food Item": f"⚡ {row['Food Item']}", "Amount (g)": row['Amount (g)'], "Calories": row['Calories'], "Protein (g)": row['Protein (g)'], "Carbs (g)": row['Carbs (g)'], "Fats (g)": row['Fats (g)']}])
            conn.update(worksheet="Sheet1", data=pd.concat([global_db, new], ignore_index=True))
            st.cache_data.clear(); st.rerun()

with st.expander("➕ Log Food"):
    t1, t2 = st.tabs(["📚 Cloud DB", "✍️ Manual"])
    with t1:
        with st.form("db_log", clear_on_submit=True):
            f1, f2, f3 = st.columns([1, 2, 1])
            m_type = f1.selectbox("Meal", ["Meal 1", "Meal 2", "Meal 3", "Snack"])
            f_item = f2.selectbox("Food", st.session_state.food_db["Food Item"])
            f_qty = f3.number_input("Grams", min_value=0.1, value=100.0)
            if st.form_submit_button("Add"):
                row = st.session_state.food_db[st.session_state.food_db["Food Item"] == f_item].iloc[0]
                mult = f_qty / 100
                new = pd.DataFrame([{"Username": st.session_state.username, "Date": date_str, "Meal": m_type, "Food Item": f_item, "Amount (g)": f_qty, "Calories": row["Calories"]*mult, "Protein (g)": row["Protein (g)"]*mult, "Carbs (g)": row["Carbs (g)"]*mult, "Fats (g)": row["Fats (g)"]*mult}])
                conn.update(worksheet="Sheet1", data=pd.concat([global_db, new], ignore_index=True))
                st.cache_data.clear(); st.rerun()
    with t2:
        with st.form("manual_log", clear_on_submit=True):
            c_f1, c_f2 = st.columns([1, 2])
            c_meal, c_name = c_f1.selectbox("Meal", ["Meal 1", "Meal 2", "Meal 3", "Snack"]), c_f2.text_input("Name")
            c_weight = st.number_input("Amount (g)", min_value=0.1, value=100.0)
            m1, m2, m3, m4 = st.columns(4)
            c_cal, c_pro, c_car, c_fat = m1.number_input("Kcal", min_value=0.0), m2.number_input("P", min_value=0.0), m3.number_input("C", min_value=0.0), m4.number_input("F", min_value=0.0)
            if st.form_submit_button("Log Custom"):
                if c_name:
                    mult = c_weight / 100
                    new_c = pd.DataFrame([{"Username": st.session_state.username, "Date": date_str, "Meal": c_meal, "Food Item": f"⭐ {c_name}", "Amount (g)": c_weight, "Calories": c_cal*mult, "Protein (g)": c_pro*mult, "Carbs (g)": c_car*mult, "Fats (g)": c_fat*mult}])
                    conn.update(worksheet="Sheet1", data=pd.concat([global_db, new_c], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

# ==========================================
# --- HISTORY ---
# ==========================================
st.write("### Entries")
for idx, row in todays_log.iterrows():
    ca, cb, cc = st.columns([4, 1.5, 0.5])
    with ca: st.markdown(f"**{row['Food Item']}** <br><span style='color:#8b949e; font-size:12px;'>{row['Meal']} • {row['Amount (g)']}g</span>", unsafe_allow_html=True)
    with cb: st.markdown(f"<p style='text-align:right;'><b>{row['Calories']:.0f} kcal</b><br><span style='font-size:11px;'>P:{row['Protein (g)']:.0f} C:{row['Carbs (g)']:.0f} F:{row['Fats (g)']:.0f}</span></p>", unsafe_allow_html=True)
    with cc:
        if st.button("×", key=f"del_{idx}"):
            conn.update(worksheet="Sheet1", data=global_db.drop(idx))
            st.cache_data.clear(); st.rerun()
