import streamlit as st
import pandas as pd
import datetime

# 1. App Configuration & Password Gate
st.set_page_config(page_title="Macro Tracker", layout="centered")

# --- THE PAYWALL / PASSWORD ---
# Buyers will find this password inside the PDF they purchase from you
APP_PASSWORD = "raket" 

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Premium Deficit Tracker")
    st.info("Please enter the password provided in your purchase PDF.")
    entered_pwd = st.text_input("Password", type="password")
    if st.button("Unlock Dashboard"):
        if entered_pwd == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop() # Stops the rest of the app from loading until unlocked

# --- MAIN APP LOADS ONLY AFTER PASSWORD ---

with st.sidebar:
    st.header("🎯 Daily Targets")
    cal_goal = st.number_input("Calorie Goal:", min_value=1000, max_value=5000, value=2000, step=50)

st.title("📊 Daily Deficit Tracker")

col_date, _ = st.columns([1, 2])
with col_date:
    selected_date = st.date_input("📅 Date", datetime.date.today())

# Initialize Temporary Memory (No CSVs for the Web version)
if 'daily_log' not in st.session_state:
    st.session_state.daily_log = pd.DataFrame(columns=[
        "Date", "Meal", "Food Item", "Amount (g)", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"
    ])

if 'food_db' not in st.session_state:
    # Core Database
    db_raw = [
        ["Chicken Breast (Cooked, Roasted)", 165, 31.0, 0.0, 3.6],
        ["Chicken Thigh (Cooked, Skinless)", 177, 24.0, 0.0, 8.0],
        ["White Rice (Cooked)", 130, 2.7, 28.0, 0.3],
        ["Egg (Whole, Hard-Boiled)", 155, 12.6, 1.1, 10.6],
        ["Jollibee Chickenjoy (Meat & Skin)", 260, 16.0, 10.0, 17.0],
        ["Whey Protein Isolate", 370, 90.0, 2.0, 1.0],
        ["Pork Adobo", 250, 14.0, 5.0, 19.0],
        ["Oats (Cooked in Water)", 71, 2.5, 12.0, 1.5]
        # You can paste the rest of your 250 items here later!
    ]
    st.session_state.food_db = pd.DataFrame(db_raw, columns=["Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"])
    st.session_state.food_db = st.session_state.food_db.sort_values(by="Food Item").reset_index(drop=True)

# Filter for selected date
date_str = selected_date.strftime("%Y-%m-%d")
todays_log = st.session_state.daily_log[st.session_state.daily_log["Date"] == date_str]

# Data Entry
st.subheader(f"🍽️ Log Food")
with st.form("food_entry_form"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1: meal_num = st.selectbox("Meal:", ["Meal 1", "Meal 2", "Meal 3", "Snacks"])
    with col2: selected_food = st.selectbox("Select Food:", st.session_state.food_db["Food Item"])
    with col3: weight = st.number_input("Amount (g):", min_value=0, value=100, step=10)
    
    if st.form_submit_button("➕ Add Food"):
        food_row = st.session_state.food_db[st.session_state.food_db["Food Item"] == selected_food].iloc[0]
        multiplier = weight / 100
        new_entry = pd.DataFrame([{
            "Date": date_str, "Meal": meal_num, "Food Item": selected_food,
            "Amount (g)": weight, "Calories": food_row["Calories"] * multiplier,
            "Protein (g)": food_row["Protein (g)"] * multiplier,
            "Carbs (g)": food_row["Carbs (g)"] * multiplier,
            "Fats (g)": food_row["Fats (g)"] * multiplier
        }])
        st.session_state.daily_log = pd.concat([st.session_state.daily_log, new_entry], ignore_index=True)
        st.rerun()

st.divider()

# Dashboard
total_cals = todays_log["Calories"].sum() if not todays_log.empty else 0
remaining_cals = cal_goal - total_cals

st.write("**Calorie Progress**")
st.progress(min(total_cals / cal_goal, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("Target", f"{cal_goal}")
c2.metric("Consumed", f"{total_cals:.0f}")
c3.metric("Remaining", f"{remaining_cals:.0f}")

if not todays_log.empty:
    st.write("### 📝 Logged Foods")
    for index, row in todays_log.iterrows():
        list_col1, list_col2, list_col3 = st.columns([2, 3, 1])
        with list_col1: st.write(f"**{row['Meal']}**\n{row['Food Item']}")
        with list_col2: st.write(f"🔥 {row['Calories']:.0f} kcal (P: {row['Protein (g)']:.1f}g)")
        with list_col3:
            if st.button("❌", key=f"del_{index}"):
                st.session_state.daily_log = st.session_state.daily_log.drop(index)
                st.rerun()
