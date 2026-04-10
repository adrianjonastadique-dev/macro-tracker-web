import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import time
import random
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Macro Tracker", layout="wide")

# ==========================================
# --- ISOLATED DATABASE CONNECTION ---
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

if "auth" not in st.session_state:
    st.session_state.auth = False

# ==========================================
# --- SECURE LOGIN & REGISTRATION ---
# ==========================================
if "last_request" not in st.session_state:
    st.session_state.last_request = 0

# Generate a random math problem once per session for the CAPTCHA
if "num1" not in st.session_state:
    st.session_state.num1 = random.randint(1, 10)
    st.session_state.num2 = random.randint(1, 10)

if not st.session_state.auth:
    st.title("📊 Daily Deficit Tracker")
    st.info("Log in to your dashboard or create a new account below.")
    
    tab_login, tab_register = st.tabs(["🔐 Secure Login", "📝 Create Account"])
    
    # --- TAB 1: LOGIN ---
    with tab_login:
        with st.form("login_form"):
            entered_user = st.text_input("Username")
            entered_pwd = st.text_input("Password", type="password")
            
            # Honeypot: Invisible to humans, traps bots that auto-fill everything
            st.markdown('<style>div[data-testid="stTextInput"]:has(input[aria-label="bot_trap"]) {display: none;}</style>', unsafe_allow_html=True)
            trap = st.text_input("bot_trap", label_visibility="collapsed")
            
            if st.form_submit_button("Login"):
                current_time = time.time()
                
                # Layer 1: Cooldown Timer
                if current_time - st.session_state.last_request < 3.0:
                    st.error("⏳ Please wait a few seconds before trying again.")
                    st.stop()
                st.session_state.last_request = current_time
                
                # Layer 2: Honeypot Trap
                if trap != "":
                    st.warning("Automated behavior detected. Request blocked.")
                    st.stop()
                
                if entered_user and entered_pwd:
                    try:
                        users_db = conn.read(worksheet="Users", ttl=0).dropna(subset=["Username"])
                        user_match = users_db[users_db["Username"].astype(str) == entered_user.strip()]
                        
                        if not user_match.empty and str(user_match.iloc[0]["Password"]).strip() == entered_pwd.strip():
                            st.session_state.auth = True
                            st.session_state.username = entered_user.strip()
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials.")
                    except Exception as e:
                        st.error(f"🚨 Database error: Ensure the 'Users' tab is set up correctly.")
                        
    # --- TAB 2: REGISTRATION ---
    with tab_register:
        with st.form("registration_form", clear_on_submit=True):
            st.write("**Register a New Account**")
            new_user = st.text_input("New Username")
            new_pwd = st.text_input("New Password", type="password")
            
            captcha_ans = st.number_input(f"Prove you are human: What is {st.session_state.num1} + {st.session_state.num2}?", step=1, value=None)
            
            if st.form_submit_button("Create Account"):
                if captcha_ans != (st.session_state.num1 + st.session_state.num2):
                    st.error("❌ Incorrect CAPTCHA. Try again.")
                    st.stop()
                
                if not new_user or not new_pwd:
                    st.error("⚠️ Username and Password cannot be blank.")
                    st.stop()
                    
                try:
                    users_db = conn.read(worksheet="Users", ttl=0).dropna(how="all")
                    if "Username" not in users_db.columns:
                        users_db = pd.DataFrame(columns=["Username", "Password"])
                        
                    if new_user.strip() in users_db["Username"].astype(str).values:
                        st.error("⚠️ That Username is already taken. Please choose another.")
                    else:
                        new_account = pd.DataFrame([{"Username": new_user.strip(), "Password": new_pwd.strip()}])
                        updated_users = pd.concat([users_db, new_account], ignore_index=True)
                        conn.update(worksheet="Users", data=updated_users)
                        
                        st.success("✅ Account created successfully! You can now switch to the Login tab.")
                        st.session_state.num1 = random.randint(1, 10)
                        st.session_state.num2 = random.randint(1, 10)
                except Exception as e:
                    st.error(f"🚨 Database error during registration. Ensure 'Users' tab exists.")
    st.stop()

# ==========================================
# --- MACRO TRACKER DASHBOARD ---
# ==========================================
st.title("📊 Daily Deficit Tracker")

with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    st.divider()
    st.write("🎯 **Daily Targets**")
    target_cal = st.number_input("Target Calories (kcal)", min_value=1000, value=2000, step=50)
    target_pro = st.number_input("Target Protein (g)", min_value=0, value=150, step=5)
    
    if st.button("🚪 Logout"):
        st.session_state.auth = False
        st.rerun()

col_date, _ = st.columns([1, 2])
with col_date:
    selected_date = st.date_input("📅 Date", datetime.date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# Fetch Data
global_db = conn.read(worksheet="Sheet1", ttl=0).dropna(how="all")
if "Username" not in global_db.columns:
    global_db = pd.DataFrame(columns=["Username", "Date", "Food", "Calories", "Protein", "Carbs", "Fat"])

global_db["Date"] = pd.to_datetime(global_db["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
user_log = global_db[global_db["Username"] == st.session_state.username]
day_log = user_log[user_log["Date"] == date_str]

# Display Metrics
total_cal = day_log["Calories"].sum() if not day_log.empty else 0
total_pro = day_log["Protein"].sum() if not day_log.empty else 0
total_carbs = day_log["Carbs"].sum() if not day_log.empty else 0
total_fat = day_log["Fat"].sum() if not day_log.empty else 0

st.write("### 📈 Daily Summary")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Calories", f"{total_cal:,.0f} / {target_cal}", delta=int(target_cal - total_cal), delta_color="inverse")
m2.metric("Protein", f"{total_pro:,.0f}g / {target_pro}g", delta=int(total_pro - target_pro))
m3.metric("Carbs", f"{total_carbs:,.0f}g")
m4.metric("Fat", f"{total_fat:,.0f}g")

# Food Entry Form
st.write("---")
st.write("### 🍎 Log Food")
with st.form("food_form", clear_on_submit=True):
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
    with c1: food_name = st.text_input("Food Item")
    with c2: cals = st.number_input("Calories", min_value=0, step=10)
    with c3: pro = st.number_input("Protein (g)", min_value=0, step=1)
    with c4: carbs = st.number_input("Carbs (g)", min_value=0, step=1)
    with c5: fat = st.number_input("Fat (g)", min_value=0, step=1)
    
    if st.form_submit_button("➕ Add Food"):
        if food_name and cals > 0:
            new_entry = pd.DataFrame([{
                "Username": st.session_state.username,
                "Date": date_str,
                "Food": food_name,
                "Calories": cals,
                "Protein": pro,
                "Carbs": carbs,
                "Fat": fat
            }])
            updated_db = pd.concat([global_db, new_entry], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_db)
            st.cache_data.clear()
            st.rerun()
        else:
            st.warning("Please enter a food name and calories.")

# Display Today's Log
if not day_log.empty:
    st.write("---")
    st.write("### 🍽️ Today's Meals")
    
    display_df = day_log[["Food", "Calories", "Protein", "Carbs", "Fat"]].copy()
    st.dataframe(display_df, hide_index=True, use_container_width=True)
