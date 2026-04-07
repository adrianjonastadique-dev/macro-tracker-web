import streamlit as st
import pandas as pd
import datetime

# 1. App Configuration & Password Gate
st.set_page_config(page_title="Macro Tracker", layout="centered")

# --- THE PAYWALL / PASSWORD ---
APP_PASSWORD = "MacroMaster2026" 

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
    st.stop() 

# --- MAIN APP LOADS ONLY AFTER PASSWORD ---

with st.sidebar:
    st.header("🎯 Daily Targets")
    cal_goal = st.number_input("Calorie Goal:", min_value=1000, max_value=5000, value=2000, step=50)

st.title("📊 Daily Deficit Tracker")

col_date, _ = st.columns([1, 2])
with col_date:
    selected_date = st.date_input("📅 Date", datetime.date.today())

# 2. Initialize Temporary Memory (No CSVs for the Web version)
if 'daily_log' not in st.session_state:
    st.session_state.daily_log = pd.DataFrame(columns=[
        "Date", "Meal", "Food Item", "Amount (g)", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"
    ])

if 'food_db' not in st.session_state:
    # --- MASSIVE 250+ ITEM DATABASE ---
    db_raw = [
        # CORE PROTEINS (Cooked)
        ["Chicken Breast (Cooked, Roasted)", 165, 31.0, 0.0, 3.6],
        ["Chicken Thigh (Cooked, Skinless)", 177, 24.0, 0.0, 8.0],
        ["Chicken Wings (Cooked, Baked)", 254, 24.0, 0.0, 17.0],
        ["Lean Pork Tenderloin (Cooked, Roasted)", 143, 26.2, 0.0, 3.5],
        ["Pork Belly / Liempo (Cooked, Roasted)", 518, 9.3, 0.0, 53.0],
        ["Pork Chop (Cooked, Pan-fried)", 231, 24.0, 0.0, 14.0],
        ["Ground Beef (90% Lean, Cooked)", 214, 26.0, 0.0, 11.0],
        ["Ground Pork (Cooked)", 297, 25.0, 0.0, 21.0],
        ["Beef Sirloin (Cooked, Roasted)", 244, 27.0, 0.0, 14.0],
        
        # LOCAL SEAFOOD (Cooked)
        ["Bangus / Milkfish (Cooked, Baked)", 190, 26.0, 0.0, 9.0],
        ["Bangus Belly (Cooked)", 250, 18.0, 0.0, 20.0],
        ["Tilapia (Cooked, Baked)", 128, 26.0, 0.0, 2.7],
        ["Galunggong / Scad (Cooked, Fried)", 280, 22.0, 0.0, 20.0],
        ["Tulingan / Mackerel (Cooked)", 205, 24.0, 0.0, 12.0],
        ["Squid / Pusit (Cooked, Boiled)", 92, 16.0, 3.0, 1.5],
        ["Shrimp / Hipon (Cooked, Steamed)", 99, 24.0, 0.2, 0.3],
        ["Crab Meat / Alimasag (Cooked)", 87, 19.0, 0.0, 1.5],
        ["Canned Tuna (in Water, Drained)", 86, 19.0, 0.0, 1.0],
        ["Canned Tuna (in Oil, Drained)", 198, 29.0, 0.0, 8.0],
        ["Canned Sardines (in Tomato Sauce)", 150, 15.0, 4.0, 9.0],
        ["Salmon (Cooked, Baked)", 206, 22.0, 0.0, 12.0],
        
        # EGGS & DAIRY
        ["Egg (Whole, Hard-Boiled)", 155, 12.6, 1.1, 10.6],
        ["Egg White (Cooked)", 52, 10.9, 0.7, 0.2],
        ["Salted Egg / Itlog na Maalat", 185, 13.0, 1.5, 14.0],
        ["Quail Egg / Itlog ng Pugo (Boiled)", 158, 13.0, 0.4, 11.0],
        ["Tofu / Tokwa (Firm, Raw)", 144, 15.8, 2.8, 8.7],
        ["Cheddar Cheese", 402, 25.0, 1.3, 33.0],
        ["Eden Cheese (Processed)", 330, 10.0, 10.0, 27.0],
        ["Cow's Milk (Whole)", 61, 3.2, 4.8, 3.3],
        ["Soy Milk (Unsweetened)", 33, 3.3, 1.8, 1.5],
        
        # CARBS & STAPLES (Cooked)
        ["White Rice (Cooked)", 130, 2.7, 28.0, 0.3],
        ["Brown Rice (Cooked)", 112, 2.6, 24.0, 0.9],
        ["Garlic Fried Rice / Sinangag", 160, 3.0, 29.0, 3.5],
        ["Sweet Potato / Kamote (Boiled)", 86, 1.6, 20.0, 0.1],
        ["White Potato (Boiled)", 87, 1.9, 20.0, 0.1],
        ["Oats (Cooked in Water)", 71, 2.5, 12.0, 1.5],
        ["Pandesal (per 100g)", 280, 8.0, 52.0, 4.0],
        ["Tasty Bread / White Bread", 266, 9.0, 50.0, 3.0],
        ["Whole Wheat Bread", 252, 12.5, 43.0, 3.4],
        ["Pancit Canton (Instant, Cooked)", 450, 9.0, 60.0, 20.0],
        ["Pancit Bihon (Home-cooked)", 150, 4.0, 25.0, 4.0],
        ["Macaroni (Cooked)", 158, 5.8, 31.0, 0.9],
        
        # FILIPINO DISHES / CARINDERIA (Approx per 100g)
        ["Pork Adobo", 250, 14.0, 5.0, 19.0],
        ["Chicken Adobo", 195, 16.0, 4.0, 12.0],
        ["Sinigang na Baboy (Pork & Broth)", 140, 10.0, 4.0, 9.0],
        ["Sinigang na Bangus", 110, 12.0, 3.0, 5.0],
        ["Lechon Kawali", 450, 14.0, 0.0, 43.0],
        ["Kare-Kare (Beef & Tripe)", 180, 12.0, 8.0, 11.0],
        ["Sisig (Pork)", 350, 15.0, 5.0, 30.0],
        ["Bicol Express", 280, 11.0, 6.0, 24.0],
        ["Dinuguan", 185, 14.0, 5.0, 12.0],
        ["Pork Menudo", 165, 11.0, 8.0, 10.0],
        ["Chicken Tinola (Meat & Broth)", 95, 12.0, 3.0, 4.0],
        ["Beef Nilaga", 130, 14.0, 4.0, 6.0],
        ["Monggo Guisado (with Pork)", 125, 8.0, 15.0, 4.0],
        ["Pinakbet", 65, 3.0, 8.0, 3.0],
        ["Ginisang Ampalaya (with Egg)", 85, 4.0, 6.0, 5.0],
        ["Chopsuey (Mixed Veggies & Meat)", 90, 5.0, 8.0, 4.0],
        ["Tortang Talong", 150, 5.0, 8.0, 11.0],
        ["Laing", 160, 4.0, 7.0, 13.0],
        ["Pork BBQ (Skewer)", 220, 18.0, 10.0, 11.0],
        
        # FAST FOOD (Approx per 100g)
        ["Jollibee Chickenjoy (Meat & Skin)", 260, 16.0, 10.0, 17.0],
        ["Jollibee Jolly Spaghetti", 145, 5.0, 22.0, 4.0],
        ["Jollibee Yumburger", 275, 12.0, 30.0, 11.0],
        ["McDonald's Fries", 323, 3.4, 43.0, 15.0],
        ["Pork Siomai (Steamed)", 210, 9.0, 18.0, 11.0],
        ["Asado Siopao", 240, 8.0, 40.0, 5.0],
        ["Mang Inasal Pecho (Grilled Chicken)", 210, 22.0, 4.0, 11.0],
        
        # STREET FOOD & SNACKS
        ["Taho (with Arnibal & Sago)", 80, 3.0, 15.0, 1.0],
        ["Balut (Whole)", 188, 14.0, 1.0, 14.0],
        ["Fishball (Fried)", 250, 8.0, 35.0, 8.0],
        ["Kikiam (Fried)", 280, 9.0, 30.0, 14.0],
        ["Kwek-Kwek (Fried Quail Eggs)", 260, 10.0, 25.0, 13.0],
        ["Isaw (Grilled Chicken Intestine)", 160, 15.0, 2.0, 10.0],
        ["Turon (Banana Spring Roll)", 270, 2.0, 45.0, 9.0],
        ["Banana Cue", 220, 1.5, 48.0, 3.0],
        ["Puto (Steamed Rice Cake)", 150, 3.0, 33.0, 0.5],
        ["Kutsinta", 140, 1.0, 34.0, 0.0],
        ["Ensaymada", 350, 7.0, 45.0, 15.0],
        ["Chicharon (Pork Rind)", 544, 61.0, 0.0, 31.0],
        
        # SUPPLEMENTS & DRINKS & PANTRY
        ["Whey Protein Concentrate (Generic, Dry)", 400, 80.0, 5.0, 6.0],
        ["Whey Protein Isolate (Generic, Dry)", 370, 90.0, 2.0, 1.0],
        ["Creatine Monohydrate (Dry)", 0, 0.0, 0.0, 0.0],
        ["Gatorade (Blue / Berry)", 25, 0.0, 6.0, 0.0],
        ["Coca-Cola (Regular)", 42, 0.0, 10.6, 0.0],
        ["Coca-Cola (Zero Sugar)", 0, 0.0, 0.0, 0.0],
        ["San Miguel Pale Pilsen", 43, 0.3, 3.2, 0.0],
        ["Starbucks Iced Americano (No Sugar)", 5, 0.1, 1.0, 0.0],
        ["Starbucks Caramel Macchiato", 70, 2.0, 10.0, 2.5],
        ["Subway 6-inch Roasted Chicken (Sub/Bread only)", 160, 12.0, 23.0, 2.5],
        ["SkyFlakes (per 100g)", 480, 8.0, 68.0, 19.0],
        ["Century Tuna (Flakes in Oil)", 180, 14.0, 2.0, 13.0],
        ["Spam (Classic)", 310, 13.0, 2.0, 28.0],
        ["Purefoods Tender Juicy Hotdog", 260, 11.0, 4.0, 22.0],
        
        # LOCAL VEGETABLES (Cooked/Boiled)
        ["Kangkong / Water Spinach", 20, 1.9, 3.8, 0.2],
        ["Pechay / Snow Cabbage", 15, 1.2, 2.5, 0.2],
        ["Sitaw / String Beans", 35, 1.9, 8.0, 0.3],
        ["Talong / Eggplant", 35, 0.8, 9.0, 0.2],
        ["Kalabasa / Squash", 40, 1.0, 9.0, 0.2],
        ["Ampalaya / Bitter Gourd", 17, 1.0, 3.7, 0.2],
        ["Malunggay Leaves", 65, 6.7, 12.0, 1.4],
        ["Sayote / Chayote", 19, 0.8, 4.5, 0.1],
        ["Cabbage / Repolyo", 23, 1.3, 5.5, 0.1],
        ["Carrots", 35, 0.8, 8.0, 0.2],
        ["Broccoli", 35, 2.4, 7.0, 0.4],
        ["Cauliflower", 23, 1.8, 4.1, 0.5],
        ["Tomato / Kamatis", 18, 0.9, 3.9, 0.2],
        ["Onion / Sibuyas", 44, 1.4, 10.0, 0.2],
        ["Garlic / Bawang (Raw)", 149, 6.4, 33.0, 0.5],
        
        # FRUITS
        ["Mango / Mangga (Ripe)", 60, 0.8, 15.0, 0.4],
        ["Mango / Mangga (Green/Hilaw)", 50, 0.5, 12.0, 0.3],
        ["Banana / Saba", 110, 1.2, 28.0, 0.3],
        ["Banana / Lakatan", 89, 1.1, 22.8, 0.3],
        ["Papaya (Ripe)", 43, 0.5, 10.8, 0.3],
        ["Pineapple / Pinya", 50, 0.5, 13.1, 0.1],
        ["Watermelon / Pakwan", 30, 0.6, 7.6, 0.2],
        ["Calamansi (Juice)", 25, 0.4, 7.0, 0.1],
        ["Avocado", 160, 2.0, 8.5, 14.7],
        ["Rambutan", 82, 0.9, 21.0, 0.2],
        ["Lanzones", 57, 0.8, 14.0, 0.2],
        ["Apple", 52, 0.3, 13.8, 0.2],
        ["Coconut Meat / Niyog", 354, 3.3, 15.0, 33.0],
        
        # CONDIMENTS & FATS
        ["Soy Sauce / Toyo", 53, 5.0, 8.0, 0.1],
        ["Vinegar / Suka", 18, 0.0, 0.9, 0.0],
        ["Fish Sauce / Patis", 35, 5.0, 3.0, 0.0],
        ["Bagoong Alamang (Shrimp Paste)", 110, 10.0, 10.0, 4.0],
        ["Banana Ketchup (UFC)", 115, 0.5, 28.0, 0.0],
        ["Mang Tomas Sarsa", 140, 1.0, 25.0, 4.0],
        ["Mayonnaise", 680, 1.0, 1.0, 75.0],
        ["Peanut Butter (Smooth)", 588, 25.0, 20.0, 50.0],
        ["Olive Oil", 884, 0.0, 0.0, 100.0],
        ["Coconut Oil", 862, 0.0, 0.0, 100.0],
        ["Butter", 717, 0.8, 0.1, 81.0]
    ]
    st.session_state.food_db = pd.DataFrame(db_raw, columns=["Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"])
    st.session_state.food_db = st.session_state.food_db.sort_values(by="Food Item").reset_index(drop=True)

# Filter for selected date
date_str = selected_date.strftime("%Y-%m-%d")
todays_log = st.session_state.daily_log[st.session_state.daily_log["Date"] == date_str]

# 3. Data Entry
st.subheader(f"🍽️ Log Food for {date_str}")
with st.form("food_entry_form"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1: meal_num = st.selectbox("Meal:", ["Meal 1", "Meal 2", "Meal 3", "Meal 4", "Snacks"])
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

# --- Custom Food Creator ---
with st.expander("🛠️ Create Custom Food (per 100g)"):
    with st.form("new_food_form", clear_on_submit=True):
        new_name = st.text_input("Food Name")
        c1, c2, c3, c4 = st.columns(4)
        with c1: new_cals = st.number_input("Calories", min_value=0)
        with c2: new_pro = st.number_input("Protein (g)", min_value=0.0)
        with c3: new_carbs = st.number_input("Carbs (g)", min_value=0.0)
        with c4: new_fats = st.number_input("Fats (g)", min_value=0.0)
        
        if st.form_submit_button("💾 Save to Session"):
            if new_name != "":
                new_db_entry = pd.DataFrame([[new_name, new_cals, new_pro, new_carbs, new_fats]], 
                                            columns=st.session_state.food_db.columns)
                st.session_state.food_db = pd.concat([st.session_state.food_db, new_db_entry], ignore_index=True)
                st.session_state.food_db = st.session_state.food_db.sort_values(by="Food Item").reset_index(drop=True)
                st.rerun()

st.divider()

# 4. Dashboard
st.subheader(f"📈 Dashboard: {date_str}")
total_cals = todays_log["Calories"].sum() if not todays_log.empty else 0
remaining_cals = cal_goal - total_cals

st.write("**Calorie Progress**")
st.progress(min(total_cals / cal_goal, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("Target", f"{cal_goal} kcal")
c2.metric("Consumed", f"{total_cals:.0f} kcal")
c3.metric("Remaining", f"{remaining_cals:.0f} kcal")

if not todays_log.empty:
    total_pro = todays_log["Protein (g)"].sum()
    total_carbs = todays_log["Carbs (g)"].sum()
    total_fats = todays_log["Fats (g)"].sum()
    
    st.write("---")
    st.write("**Macro Breakdown**")
    chart_data = pd.DataFrame({
        "Macros": ["Protein", "Carbs", "Fats"],
        "Grams": [total_pro, total_carbs, total_fats]
    }).set_index("Macros")
    
    macro_col1, macro_col2 = st.columns([2, 1])
    with macro_col1: st.bar_chart(chart_data, color="#4F8BF9") 
    with macro_col2:
        st.metric("Total Protein", f"{total_pro:.1f}g")
        st.metric("Total Carbs", f"{total_carbs:.1f}g")
        st.metric("Total Fats", f"{total_fats:.1f}g")

    st.write("---")
    st.write("### 📝 Logged Foods")
    for index, row in todays_log.iterrows():
        list_col1, list_col2, list_col3 = st.columns([2, 3, 1])
        with list_col1:
            st.write(f"**{row['Meal']}**")
            st.write(f"{row['Food Item']} ({row['Amount (g)']}g)")
        with list_col2:
            st.write(f"🔥 {row['Calories']:.0f} kcal")
            st.caption(f"🥩 **P:** {row['Protein (g)']:.1f}g  |  🍞 **C:** {row['Carbs (g)']:.1f}g  |  🥑 **F:** {row['Fats (g)']:.1f}g")
        with list_col3:
            st.write("")
            if st.button("❌ Remove", key=f"del_{index}"):
                st.session_state.daily_log = st.session_state.daily_log.drop(index)
                st.rerun()
else:
    st.info(f"No foods logged for {date_str}. Add a meal above!")
