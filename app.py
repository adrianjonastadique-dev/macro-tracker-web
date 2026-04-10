import streamlit as st
import pandas as pd
import datetime
import time
import random
from streamlit_gsheets import GSheetsConnection

# 1. App Configuration
st.set_page_config(page_title="Macro Tracker", layout="centered")

# --- LOAD EXTERNAL CSS ---
try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.error("style.css not found. Please ensure the file exists in the same directory.")

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

# --- FUNCTIONS ---
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
# --- AUTHENTICATION GATE ---
# ==========================================
if not st.session_state.authenticated:
    st.title("🔒 Access")
    tab_login, tab_register = st.tabs(["Login", "Create Account"])
    
    with tab_login:
        with st.form("login_form"):
            entered_user = st.text_input("Username")
            entered_pwd = st.text_input("Password", type="password")
            st.markdown('<style>div[data-testid="stTextInput"]:has(input[aria-label="bot_trap"]) {display: none;}</style>', unsafe_allow_html=True)
            trap = st.text_input("bot_trap", label_visibility="collapsed")
            
            if st.form_submit_button("Sign In"):
                current_time = time.time()
                if current_time - st.session_state.last_request < 3.0:
                    st.error("⏳ Wait a moment...")
                    st.stop()
                st.session_state.last_request = current_time
                if trap != "": st.stop()
                
                if entered_user.strip() and entered_pwd.strip():
                    try:
                        users_db = conn.read(worksheet="Users", ttl=0).dropna(subset=["Username"])
                        user_match = users_db[users_db["Username"].astype(str) == entered_user.strip()]
                        if not user_match.empty and str(user_match.iloc[0]["Password"]).strip() == entered_pwd.strip():
                            st.session_state.authenticated = True
                            st.session_state.username = entered_user.strip()
                            if "TargetCalories" in user_match.columns and pd.notna(user_match.iloc[0]["TargetCalories"]):
                                st.session_state.target_calories = int(user_match.iloc[0]["TargetCalories"])
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")
                    except Exception as e:
                        st.error(f"Database error: {str(e)}")
    
    with tab_register:
        with st.form("reg_form", clear_on_submit=True):
            n_user = st.text_input("New Username")
            n_pwd = st.text_input("New Password", type="password")
            ans = st.number_input(f"Captcha: {st.session_state.num1} + {st.session_state.num2}", step=1, value=None)
            if st.form_submit_button("Register"):
                if ans == (st.session_state.num1 + st.session_state.num2) and n_user.strip() and n_pwd.strip():
                    u_db = conn.read(worksheet="Users", ttl=0).dropna(how="all")
                    if n_user.strip() in u_db["Username"].astype(str).values:
                        st.error("Taken.")
                    else:
                        new_acc = pd.DataFrame([{"Username": n_user.strip(), "Password": n_pwd.strip(), "TargetCalories": 2000}])
                        conn.update(worksheet="Users", data=pd.concat([u_db, new_acc], ignore_index=True))
                        st.success("Account created! Login now.")
    st.stop()

# ==========================================
# --- SIDEBAR & DATA ---
# ==========================================
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    st.divider()
    st.number_input("Daily Goal", min_value=1000, max_value=5000, step=50, 
                    value=st.session_state.target_calories, key="calorie_input_widget", on_change=update_calorie_goal)
    cal_goal = st.session_state.target_calories
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

# Load Main Data
global_db = conn.read(worksheet="Sheet1", ttl=0).dropna(how="all")
if "Username" not in global_db.columns:
    global_db = pd.DataFrame(columns=["Username", "Date", "Meal", "Food Item", "Amount (g)", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"])

global_db["Date"] = global_db["Date"].astype(str)
user_log = global_db[global_db["Username"] == st.session_state.username]

# ==========================================
# --- MAIN DASHBOARD ---
# ==========================================
col_title, col_date = st.columns([2, 1])
with col_title:
    st.title("Tracking")
with col_date:
    selected_date = st.date_input("Date", datetime.date.today(), label_visibility="collapsed")

date_str = selected_date.strftime("%Y-%m-%d")
todays_log = user_log[user_log["Date"] == date_str]

total_cals = todays_log["Calories"].sum() if not todays_log.empty else 0
total_prot = todays_log["Protein (g)"].sum() if not todays_log.empty else 0
total_carbs = todays_log["Carbs (g)"].sum() if not todays_log.empty else 0
total_fats = todays_log["Fats (g)"].sum() if not todays_log.empty else 0
remaining_cals = cal_goal - total_cals

# --- DYNAMIC GLOW CARD ---
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

# Macro Row
m2, m3, m4 = st.columns(3)
m2.metric("PROTEIN", f"{total_prot:.0f}g")
m3.metric("CARBS", f"{total_carbs:.0f}g")
m4.metric("FATS", f"{total_fats:.0f}g")

st.divider()

# ==========================================
# --- SMART QUICK-LOG (HABITS) ---
# ==========================================
st.write("### ⚡ Recently Logged")
if not user_log.empty:
    recent_items = user_log.sort_values(['Date'], ascending=False).drop_duplicates(subset=['Food Item']).head(5)
    if not recent_items.empty:
        cols = st.columns(len(recent_items))
        for i, (idx, row) in enumerate(recent_items.iterrows()):
            clean_label = row['Food Item'].replace("⚡ ", "")[:12]
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
else:
    st.caption("Start logging to see shortcuts.")

# ==========================================
# --- FOOD DATABASE ---
# ==========================================
if 'food_db' not in st.session_state:
    db_raw = [
        ["Chicken Breast (Boiled/Poached)", 165, 31.0, 0.0, 3.6],
        ["Chicken Breast (Grilled)", 151, 30.5, 0.0, 3.0],
        ["Chicken Breast (Pan-Fried in Oil)", 240, 24.0, 10.0, 12.0],
        ["Chicken Thigh (Boiled, Skinless)", 177, 24.0, 0.0, 8.0],
        ["Chicken Thigh (Grilled, Skinless)", 185, 23.0, 0.0, 9.0],
        ["Chicken Thigh (Fried with Skin)", 280, 16.0, 5.0, 21.0],
        ["Chicken Wings (Baked)", 254, 24.0, 0.0, 17.0],
        ["Chicken Wings (Fried)", 320, 18.0, 10.0, 22.0],
        ["Chicken Liver (Boiled)", 116, 17.0, 0.0, 5.0],
        ["Chicken Liver (Pan-Fried)", 165, 16.0, 4.0, 9.0],
        ["Pork Tenderloin (Boiled)", 143, 26.2, 0.0, 3.5],
        ["Pork Tenderloin (Grilled)", 160, 28.0, 0.0, 4.0],
        ["Pork Belly / Liempo (Boiled)", 518, 9.3, 0.0, 53.0],
        ["Pork Belly / Liempo (Grilled)", 450, 15.0, 0.0, 40.0],
        ["Pork Belly / Liempo (Deep Fried)", 550, 10.0, 0.0, 55.0],
        ["Pork Chop (Grilled, Lean Only)", 190, 28.0, 0.0, 8.0],
        ["Pork Chop (Pan-Fried with Fat)", 250, 24.0, 0.0, 16.0],
        ["Ground Pork (Boiled)", 260, 24.0, 0.0, 17.0],
        ["Ground Pork (Pan-Fried)", 297, 25.0, 0.0, 21.0],
        ["Pork Liver (Boiled)", 134, 21.0, 3.0, 4.0],
        ["Beef Sirloin (Grilled)", 244, 27.0, 0.0, 14.0],
        ["Beef Sirloin (Boiled)", 200, 28.0, 0.0, 9.0],
        ["Beef Brisket (Boiled)", 275, 25.0, 0.0, 19.0],
        ["Beef Shank / Laman (Boiled)", 201, 28.0, 0.0, 9.0],
        ["Ground Beef 90/10 (Pan-Fried)", 214, 26.0, 0.0, 11.0],
        ["Ground Beef 80/20 (Pan-Fried)", 254, 23.0, 0.0, 17.0],
        ["Beef Tripe / Tuwalya (Boiled)", 94, 12.0, 0.0, 5.0],
        ["Bangus / Milkfish (Boiled)", 150, 22.0, 0.0, 6.0],
        ["Bangus / Milkfish (Grilled)", 170, 24.0, 0.0, 7.0],
        ["Bangus / Milkfish (Pan-Fried)", 220, 20.0, 2.0, 14.0],
        ["Bangus Belly (Grilled)", 250, 18.0, 0.0, 20.0],
        ["Tilapia (Boiled / Steamed)", 100, 21.0, 0.0, 2.0],
        ["Tilapia (Grilled)", 110, 22.0, 0.0, 2.5],
        ["Tilapia (Deep Fried)", 200, 18.0, 5.0, 12.0],
        ["Salmon (Baked / Steamed)", 206, 22.0, 0.0, 12.0],
        ["Salmon (Pan-Fried)", 230, 20.0, 0.0, 15.0],
        ["Galunggong (Boiled)", 110, 20.0, 0.0, 3.0],
        ["Galunggong (Fried)", 280, 22.0, 0.0, 20.0],
        ["Tuna Steak (Grilled)", 130, 28.0, 0.0, 1.0],
        ["Canned Tuna (Drained, Water)", 86, 19.0, 0.0, 1.0],
        ["Canned Tuna (Drained, Oil)", 198, 29.0, 0.0, 8.0],
        ["Shrimp (Boiled / Steamed)", 99, 24.0, 0.2, 0.3],
        ["Shrimp (Pan-Fried in Butter)", 150, 20.0, 1.0, 7.0],
        ["Squid / Pusit (Boiled)", 92, 16.0, 3.0, 1.5],
        ["Squid / Pusit (Grilled)", 110, 18.0, 3.0, 2.0],
        ["Squid / Pusit (Fried/Calamari)", 175, 15.0, 8.0, 9.0],
        ["Egg (Whole, Boiled)", 155, 12.6, 1.1, 10.6],
        ["Egg (Whole, Fried)", 196, 13.0, 1.0, 15.0],
        ["Egg (Whole, Scrambled)", 160, 11.0, 2.0, 12.0],
        ["Egg White (Boiled)", 52, 10.9, 0.7, 0.2],
        ["Egg White (Fried)", 75, 10.0, 0.5, 3.5],
        ["Tofu / Tokwa (Raw)", 144, 15.8, 2.8, 8.7],
        ["Tofu / Tokwa (Fried)", 270, 16.0, 4.0, 20.0],
        ["Cow's Milk (Whole)", 61, 3.2, 4.8, 3.3],
        ["Cow's Milk (Skim)", 34, 3.4, 5.0, 0.1],
        ["Soy Milk (Unsweetened)", 33, 3.3, 1.8, 1.5],
        ["Cheddar Cheese", 402, 25.0, 1.3, 33.0],
        ["White Rice (Steamed)", 130, 2.7, 28.0, 0.3],
        ["White Rice (Garlic Fried)", 160, 3.0, 29.0, 3.5],
        ["Brown Rice (Steamed)", 112, 2.6, 24.0, 0.9],
        ["Quinoa (Cooked)", 120, 4.4, 21.3, 1.9],
        ["Oats (Cooked in Water)", 71, 2.5, 12.0, 1.5],
        ["White Potato (Boiled)", 87, 1.9, 20.0, 0.1],
        ["White Potato (Baked)", 93, 2.5, 21.0, 0.1],
        ["White Potato (Fried / Fries)", 312, 3.4, 41.0, 15.0],
        ["Sweet Potato / Kamote (Boiled)", 86, 1.6, 20.0, 0.1],
        ["Sweet Potato / Kamote (Baked)", 90, 2.0, 21.0, 0.2],
        ["Sweet Potato / Kamote (Fried)", 280, 2.0, 35.0, 14.0],
        ["Macaroni / Pasta (Boiled)", 158, 5.8, 31.0, 0.9],
        ["Corn on the Cob (Boiled)", 96, 3.4, 21.0, 1.5],
        ["Broccoli (Boiled)", 35, 2.4, 7.0, 0.4],
        ["Cauliflower (Boiled)", 23, 1.8, 4.1, 0.5],
        ["Cabbage / Repolyo (Boiled)", 23, 1.3, 5.5, 0.1],
        ["Kangkong (Boiled)", 20, 1.9, 3.8, 0.2],
        ["Pechay (Boiled)", 15, 1.2, 2.5, 0.2],
        ["Malunggay Leaves (Boiled)", 65, 6.7, 12.0, 1.4],
        ["Carrots (Boiled)", 35, 0.8, 8.0, 0.2],
        ["Carrots (Raw)", 41, 0.9, 10.0, 0.2],
        ["Eggplant / Talong (Boiled)", 35, 0.8, 9.0, 0.2],
        ["Eggplant / Talong (Grilled)", 40, 1.0, 10.0, 0.2],
        ["Eggplant / Talong (Fried)", 150, 1.0, 10.0, 12.0],
        ["Sitaw / String Beans (Boiled)", 35, 1.9, 8.0, 0.3],
        ["Kalabasa / Squash (Boiled)", 40, 1.0, 9.0, 0.2],
        ["Ampalaya / Bitter Gourd (Boiled)", 17, 1.0, 3.7, 0.2],
        ["Sayote (Boiled)", 19, 0.8, 4.5, 0.1],
        ["Okra (Boiled)", 22, 1.9, 4.0, 0.1],
        ["Monggo Beans (Boiled)", 105, 7.0, 19.0, 0.4],
        ["Mango (Ripe)", 60, 0.8, 15.0, 0.4],
        ["Mango (Green)", 50, 0.5, 12.0, 0.3],
        ["Banana (Lakatan)", 89, 1.1, 22.8, 0.3],
        ["Banana (Saba, Boiled)", 110, 1.2, 28.0, 0.3],
        ["Banana (Saba, Fried)", 220, 1.0, 30.0, 10.0],
        ["Papaya (Ripe)", 43, 0.5, 10.8, 0.3],
        ["Pineapple", 50, 0.5, 13.1, 0.1],
        ["Watermelon", 30, 0.6, 7.6, 0.2],
        ["Avocado", 160, 2.0, 8.5, 14.7],
        ["Apple", 52, 0.3, 13.8, 0.2],
        ["Coconut Meat (Mature)", 354, 3.3, 15.0, 33.0],
        ["Calamansi (Juice)", 25, 0.4, 7.0, 0.1],
        ["Olive Oil", 884, 0.0, 0.0, 100.0],
        ["Coconut Oil", 862, 0.0, 0.0, 100.0],
        ["Butter", 717, 0.8, 0.1, 81.0],
        ["Peanut Butter", 588, 25.0, 20.0, 50.0],
        ["Whey Protein Concentrate", 400, 80.0, 5.0, 6.0],
        ["Black Coffee", 3, 0, 0, 0.3],
    ]
    st.session_state.food_db = pd.DataFrame(db_raw, columns=["Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"])
    st.session_state.food_db = st.session_state.food_db.sort_values(by="Food Item").reset_index(drop=True)

# ==========================================
# --- ENTRY SECTION ---
# ==========================================
with st.expander("➕ Log Food", expanded=False):
    t1, t2 = st.tabs(["📚 Database", "✍️ Manual"])
    with t1:
        with st.form("db_log", clear_on_submit=True):
            f1, f2, f3 = st.columns([1, 2, 1])
            m_type = f1.selectbox("Meal", ["Meal 1", "Meal 2", "Meal 3", "Snack"])
            f_item = f2.selectbox("Food", st.session_state.food_db["Food Item"])
            f_qty = f3.number_input("Grams", value=100, step=10)
            if st.form_submit_button("Add"):
                row = st.session_state.food_db[st.session_state.food_db["Food Item"] == f_item].iloc[0]
                mult = f_qty / 100
                new = pd.DataFrame([{
                    "Username": st.session_state.username, "Date": date_str, "Meal": m_type, "Food Item": f_item,
                    "Amount (g)": f_qty, "Calories": row["Calories"]*mult, "Protein (g)": row["Protein (g)"]*mult,
                    "Carbs (g)": row["Carbs (g)"]*mult, "Fats (g)": row["Fats (g)"]*mult
                }])
                conn.update(worksheet="Sheet1", data=pd.concat([global_db, new], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
    with t2:
        with st.form("manual_log", clear_on_submit=True):
            c_f1, c_f2 = st.columns([1, 2])
            c_meal = c_f1.selectbox("Meal", ["Meal 1", "Meal 2", "Meal 3", "Snack"], key="c_meal")
            c_name = c_f2.text_input("Name")
            m1, m2, m3, m4 = st.columns(4)
            c_cal, c_pro, c_car, c_fat = m1.number_input("Kcals"), m2.number_input("P"), m3.number_input("C"), m4.number_input("F")
            if st.form_submit_button("Log Custom"):
                if c_name:
                    new_c = pd.DataFrame([{
                        "Username": st.session_state.username, "Date": date_str, "Meal": c_meal, "Food Item": f"⭐ {c_name}",
                        "Amount (g)": "Custom", "Calories": c_cal, "Protein (g)": c_pro, "Carbs (g)": c_car, "Fats (g)": c_fat
                    }])
                    conn.update(worksheet="Sheet1", data=pd.concat([global_db, new_c], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

# ==========================================
# --- HISTORY ---
# ==========================================
st.write("### Entries")
if not todays_log.empty:
    for idx, row in todays_log.iterrows():
        with st.container():
            ca, cb, cc = st.columns([4, 1.5, 0.5])
            with ca: st.markdown(f"**{row['Food Item']}** <br><span style='color:#8b949e; font-size:12px;'>{row['Meal']} • {row['Amount (g)']}g</span>", unsafe_allow_html=True)
            with cb: st.markdown(f"<p style='text-align:right;'><b>{row['Calories']:.0f} kcal</b><br><span style='font-size:11px;'>P:{row['Protein (g)']:.0f} C:{row['Carbs (g)']:.0f} F:{row['Fats (g)']:.0f}</span></p>", unsafe_allow_html=True)
            with cc:
                if st.button("×", key=f"del_{idx}"):
                    conn.update(worksheet="Sheet1", data=global_db.drop(idx))
                    st.cache_data.clear()
                    st.rerun()
        st.markdown("<hr style='margin:4px; border-top:1px solid #21262d;'>", unsafe_allow_html=True)
else:
    st.info("No entries.")
