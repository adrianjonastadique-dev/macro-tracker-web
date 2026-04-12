import streamlit as st
import pandas as pd
import datetime
import time
import random
import pytz
import uuid
from streamlit_gsheets import GSheetsConnection

# ==========================================
# --- 1. APP CONFIGURATION & STYLES ---
# ==========================================
st.set_page_config(page_title="Macro Tracker", layout="centered")

try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass 

# Establish connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "last_request" not in st.session_state:
    st.session_state.last_request = 0
if "num1" not in st.session_state:
    st.session_state.num1 = random.randint(1, 10)
    st.session_state.num2 = random.randint(1, 10)
if "target_calories" not in st.session_state:
    st.session_state.target_calories = 2000
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

def update_calorie_goal():
    new_goal = st.session_state.calorie_input_widget
    st.session_state.target_calories = new_goal
    try:
        users_db = conn.read(worksheet="Users", ttl=0)
        users_db.loc[users_db["Username"].astype(str) == st.session_state.username, "TargetCalories"] = new_goal
        conn.update(worksheet="Users", data=users_db)
    except Exception:
        pass

# ==========================================
# --- 2. AUTHENTICATION & PAYWALL GATE ---
# ==========================================
if not st.session_state.authenticated:
    st.title("🔒 Access")
    tab_login, tab_register = st.tabs(["Login", "Create Account (Free Trial)"])
    
    with tab_login:
        with st.form("login_form"):
            # Switched to Email for Login
            entered_user = st.text_input("Email Address")
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
                        # Fetch fresh data
                        users_db = conn.read(worksheet="Users", ttl=0).dropna(subset=["Username"])
                        
                        # Initialize columns if missing, and FORCE string type to prevent float64 crash
                        if "SessionID" not in users_db.columns:
                            users_db["SessionID"] = ""
                        users_db["SessionID"] = users_db["SessionID"].astype(str)
                        
                        # Match email (stored in Username column)
                        user_match = users_db[users_db["Username"].astype(str) == entered_user.strip()]
                        
                        if not user_match.empty and str(user_match.iloc[0]["Password"]).strip() == entered_pwd.strip():
                            
                            # --- 🛑 FREE TRIAL PAYWALL CHECK 🛑 ---
                            join_date_str = str(user_match.iloc[0].get("JoinDate", "2026-01-01"))
                            is_paid = str(user_match.iloc[0].get("IsPaid", "False")).strip().upper() == "TRUE"
                            
                            try:
                                join_date = datetime.datetime.strptime(join_date_str, "%Y-%m-%d").date()
                                days_active = (datetime.date.today() - join_date).days
                            except:
                                days_active = 0 
                                
                            if days_active > 7 and not is_paid:
                                st.error("⏳ Your 7-Day Free Trial has expired!")
                                st.markdown("[💳 Click here to purchase the Full Lifetime Version for $75](https://your-payment-link.com)")
                                st.stop() 
                            # --------------------------------------

                            # Cloud Session Lock: Kick out other devices
                            idx = user_match.index[0]
                            users_db.at[idx, "SessionID"] = str(st.session_state.session_id)
                            conn.update(worksheet="Users", data=users_db)
                            
                            # Finalize Login
                            st.session_state.authenticated = True
                            st.session_state.username = entered_user.strip()
                            if "TargetCalories" in users_db.columns and pd.notna(users_db.at[idx, "TargetCalories"]):
                                st.session_state.target_calories = int(users_db.at[idx, "TargetCalories"])
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")
                    except Exception as e:
                        st.error(f"Login error: {str(e)}")
    
    with tab_register:
        with st.form("reg_form", clear_on_submit=True):
            # ANTI-FREELOADER: Require Email
            n_user = st.text_input("Email Address")
            n_pwd = st.text_input("New Password", type="password")
            ans = st.number_input(f"Captcha: {st.session_state.num1} + {st.session_state.num2}", step=1, value=None)
            
            if st.form_submit_button("Start 7-Day Free Trial"):
                if ans == (st.session_state.num1 + st.session_state.num2) and n_user.strip() and n_pwd.strip():
                    
                    # Basic Email Validation
                    if "@" not in n_user or "." not in n_user:
                        st.error("❗ Please enter a valid email address.")
                    else:
                        u_db = conn.read(worksheet="Users", ttl=0).dropna(how="all")
                        if "SessionID" not in u_db.columns: u_db["SessionID"] = ""
                        u_db["SessionID"] = u_db["SessionID"].astype(str)
                        
                        if n_user.strip() in u_db["Username"].astype(str).values:
                            st.error("❗ Email already registered.")
                        else:
                            today_str = datetime.date.today().strftime("%Y-%m-%d")
                            new_acc = pd.DataFrame([{
                                "Username": n_user.strip(), 
                                "Password": n_pwd.strip(), 
                                "TargetCalories": 2000, 
                                "SessionID": "",
                                "JoinDate": today_str,
                                "IsPaid": False
                            }])
                            conn.update(worksheet="Users", data=pd.concat([u_db, new_acc], ignore_index=True))
                            st.success("Account created! Your 7-day free trial starts now. Please Login.")
    st.stop()

# ==========================================
# --- 3. SESSION LOCK MONITOR ---
# ==========================================
try:
    current_users = conn.read(worksheet="Users", ttl=0)
    current_users["SessionID"] = current_users["SessionID"].astype(str)
    cloud_sid = str(current_users.loc[current_users["Username"] == st.session_state.username, "SessionID"].values[0])
    
    if cloud_sid != str(st.session_state.session_id) and cloud_sid != "nan" and cloud_sid != "":
        st.session_state.authenticated = False
        st.warning("⚠️ Session expired. Account logged in from another device.")
        st.rerun()
except Exception:
    pass

# ==========================================
# --- 4. SIDEBAR & LOGOUT ---
# ==========================================
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    st.divider()
    st.number_input("Daily Goal", min_value=1000, max_value=5000, step=50, 
                    value=st.session_state.target_calories, key="calorie_input_widget", on_change=update_calorie_goal)
    cal_goal = st.session_state.target_calories
    
    if st.button("Logout"):
        try:
            users_db = conn.read(worksheet="Users", ttl=0)
            users_db["SessionID"] = users_db["SessionID"].astype(str)
            users_db.loc[users_db["Username"] == st.session_state.username, "SessionID"] = ""
            conn.update(worksheet="Users", data=users_db)
        except Exception:
            pass
        st.session_state.authenticated = False
        st.rerun()

# ==========================================
# --- 5. DATA LOADING ---
# ==========================================
global_db = conn.read(worksheet="Sheet1", ttl=0).dropna(how="all")
if "Username" not in global_db.columns:
    global_db = pd.DataFrame(columns=["Username", "Date", "Meal", "Food Item", "Amount (g)", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"])

global_db["Date"] = global_db["Date"].astype(str)
user_log = global_db[global_db["Username"] == st.session_state.username]

if 'food_db' not in st.session_state:
    try:
        food_library = conn.read(worksheet="FoodLibrary", ttl=3600)
        st.session_state.food_db = food_library.sort_values("Food Item")
    except Exception:
        st.error("Failed to load Food Library. Ensure 'FoodLibrary' tab exists.")
        st.stop()

# ==========================================
# --- 6. DASHBOARD & MANILA TIMEZONE ---
# ==========================================
ph_tz = pytz.timezone('Asia/Manila')
local_today = datetime.datetime.now(ph_tz).date()

col_title, col_date = st.columns([2, 1])
with col_title:
    st.title("Tracking")
with col_date:
    selected_date = st.date_input("Date", local_today, label_visibility="collapsed")

date_str = selected_date.strftime("%Y-%m-%d")
todays_log = user_log[user_log["Date"] == date_str]

total_cals = todays_log["Calories"].sum() if not todays_log.empty else 0
total_prot = todays_log["Protein (g)"].sum() if not todays_log.empty else 0
total_carbs = todays_log["Carbs (g)"].sum() if not todays_log.empty else 0
total_fats = todays_log["Fats (g)"].sum() if not todays_log.empty else 0
remaining_cals = cal_goal - total_cals

# --- GLOW CARD ---
st.progress(min(max(total_cals / cal_goal, 0.0), 1.0))
is_over = total_cals > cal_goal
glow_class = "glow-red" if is_over else "glow-green"
status_text = "OVER" if is_over else "LEFT"

st.markdown(f"""
    <div class="glow-card {glow_class}">
        <div class="glow-label">Daily Energy Status</div>
        <div class="glow-value">{total_cals:.0f} / {cal_goal} <span style="font-size:16px;">kcal</span></div>
        <div style="color: {'#da3633' if is_over else '#238636'}; font-weight: bold; font-size: 18px;">
            {abs(remaining_cals):.0f} kcal {status_text}
        </div>
    </div>
    <br>
""", unsafe_allow_html=True)

m2, m3, m4 = st.columns(3)
m2.metric("PROTEIN", f"{total_prot:.0f}g")
m3.metric("CARBS", f"{total_carbs:.0f}g")
m4.metric("FATS", f"{total_fats:.0f}g")
st.divider()

# ==========================================
# --- 7. SMART QUICK-LOG ---
# ==========================================
st.write("### ⚡ Recently Logged")
if not user_log.empty:
    recent_items = user_log.sort_values(['Date'], ascending=False).drop_duplicates(subset=['Food Item']).head(5)
    if not recent_items.empty:
        cols = st.columns(len(recent_items))
        for i, (idx, row) in enumerate(recent_items.iterrows()):
            clean_label = row['Food Item'].replace("⚡ ", "").replace("⭐ ", "")[:12]
            if cols[i].button(f"{clean_label}", key=f"smart_btn_{i}"):
                new_entry = pd.DataFrame([{
                    "Username": st.session_state.username, "Date": date_str, "Meal": row['Meal'], 
                    "Food Item": row['Food Item'] if "⚡" in row['Food Item'] else f"⚡ {row['Food Item']}",
                    "Amount (g)": row['Amount (g)'], "Calories": row['Calories'],
                    "Protein (g)": row['Protein (g)'], "Carbs (g)": row['Carbs (g)'], "Fats (g)": row['Fats (g)']
                }])
                conn.update(worksheet="Sheet1", data=pd.concat([global_db, new_entry], ignore_index=True))
                st.cache_data.clear()
                st.rerun()

# ==========================================
# --- 8. ENTRY FORMS ---
# ==========================================
with st.expander("➕ Log Food", expanded=False):
    t1, t2 = st.tabs(["📚 Cloud DB", "✍️ Manual"])
    
    with t1:
        with st.form("db_log", clear_on_submit=True):
            f1, f2, f3 = st.columns([1, 2, 1])
            m_type = f1.selectbox("Meal", ["Meal 1", "Meal 2", "Meal 3", "Snack"])
            f_item = f2.selectbox("Food", st.session_state.food_db["Food Item"])
            f_qty = f3.number_input("Grams", min_value=0.0, value=100.0, step=10.0)
            
            if st.form_submit_button("Add"):
                if f_qty <= 0: st.error("❗ Amount must be positive.")
                else:
                    row = st.session_state.food_db[st.session_state.food_db["Food Item"] == f_item].iloc[0]
                    mult = f_qty / 100
                    new = pd.DataFrame([{"Username": st.session_state.username, "Date": date_str, "Meal": m_type, "Food Item": f_item, "Amount (g)": f_qty, "Calories": row["Calories"]*mult, "Protein (g)": row["Protein (g)"]*mult, "Carbs (g)": row["Carbs (g)"]*mult, "Fats (g)": row["Fats (g)"]*mult}])
                    conn.update(worksheet="Sheet1", data=pd.concat([global_db, new], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

    with t2:
        with st.form("manual_log", clear_on_submit=True):
            c_f1, c_f2 = st.columns([1, 2])
            c_meal = c_f1.selectbox("Meal", ["Meal 1", "Meal 2", "Meal 3", "Snack"])
            c_name = c_f2.text_input("Name")
            c_weight = st.number_input("Amount (g)", min_value=0.0, value=100.0)
            
            st.caption("Enter macros per 100g:")
            m1, m2, m3, m4 = st.columns(4)
            c_cal, c_pro, c_car, c_fat = m1.number_input("Kcals", min_value=0.0), m2.number_input("P", min_value=0.0), m3.number_input("C", min_value=0.0), m4.number_input("F", min_value=0.0)
            
            if st.form_submit_button("Log Custom"):
                if not c_name: st.error("❗ Name required.")
                elif any(x < 0 for x in [c_cal, c_pro, c_car, c_fat]) or c_weight <= 0: st.error("❗ Invalid numbers.")
                else:
                    mult = c_weight / 100
                    new_c = pd.DataFrame([{"Username": st.session_state.username, "Date": date_str, "Meal": c_meal, "Food Item": f"⭐ {c_name}", "Amount (g)": c_weight, "Calories": c_cal * mult, "Protein (g)": c_pro * mult, "Carbs (g)": c_car * mult, "Fats (g)": c_fat * mult}])
                    conn.update(worksheet="Sheet1", data=pd.concat([global_db, new_c], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

# ==========================================
# --- 9. HISTORY VIEWER ---
# ==========================================
st.write("### Entries")
if not todays_log.empty:
    for idx, row in todays_log.iterrows():
        with st.container():
            ca, cb, cc = st.columns([4, 1.5, 0.5])
            with ca: 
                display_amt = f"{row['Amount (g)']}g" if str(row['Amount (g)']) != "Custom" else "Custom"
                st.markdown(f"**{row['Food Item']}** <br><span style='color:#8b949e; font-size:12px;'>{row['Meal']} • {display_amt}</span>", unsafe_allow_html=True)
            with cb: 
                st.markdown(f"<p style='text-align:right;'><b>{row['Calories']:.0f} kcal</b><br><span style='font-size:11px;'>P:{row['Protein (g)']:.0f} C:{row['Carbs (g)']:.0f} F:{row['Fats (g)']:.0f}</span></p>", unsafe_allow_html=True)
            with cc:
                if st.button("×", key=f"del_{idx}"):
                    conn.update(worksheet="Sheet1", data=global_db.drop(idx))
                    st.cache_data.clear(); st.rerun()
        st.markdown("<hr style='margin:4px; border-top:1px solid #21262d;'>", unsafe_allow_html=True)
else:
    st.info("No entries.")
