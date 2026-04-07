import streamlit as st
import pandas as pd
import datetime

# 1. App Configuration & Password Gate
st.set_page_config(page_title="Macro Tracker", layout="centered")

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

# 2. Initialize Temporary Memory
if 'daily_log' not in st.session_state:
    st.session_state.daily_log = pd.DataFrame(columns=[
        "Date", "Meal", "Food Item", "Amount (g)", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"
    ])

if 'food_db' not in st.session_state:
    # --- INGREDIENT-ONLY DATABASE (Cooked Options) ---
    db_raw = [
        # POULTRY
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
        
        # PORK
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
        
        # BEEF
        ["Beef Sirloin (Grilled)", 244, 27.0, 0.0, 14.0],
        ["Beef Sirloin (Boiled)", 200, 28.0, 0.0, 9.0],
        ["Beef Brisket (Boiled)", 275, 25.0, 0.0, 19.0],
        ["Beef Shank / Laman (Boiled)", 201, 28.0, 0.0, 9.0],
        ["Ground Beef 90/10 (Pan-Fried)", 214, 26.0, 0.0, 11.0],
        ["Ground Beef 80/20 (Pan-Fried)", 254, 23.0, 0.0, 17.0],
        ["Beef Tripe / Tuwalya (Boiled)", 94, 12.0, 0.0, 5.0],
        
        # SEAFOOD
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
        
        # EGGS, DAIRY, SOY
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
        
        # RICE, GRAINS & POTATOES
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
        
        # VEGETABLES (Cooked / Boiled)
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
        
        # AROMATICS & RAW VEG (For recipe building)
        ["Garlic (Raw)", 149, 6.4, 33.0, 0.5],
        ["Garlic (Fried)", 350, 7.0, 40.0, 20.0],
        ["Onion (Raw)", 40, 1.1, 9.0, 0.1],
        ["Onion (Sautéed)", 120, 1.5, 14.0, 7.0],
        ["Tomato (Raw)", 18, 0.9, 3.9, 0.2],
        ["Bell Pepper (Raw)", 20, 1.0, 4.6, 0.2],
        ["Cucumber (Raw)", 15, 0.7, 3.6, 0.1],
        ["Mushroom (Boiled)", 28, 2.2, 5.3, 0.3],
        
        # FRUITS
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
        
        # OILS, FATS & CONDIMENTS (For recipe building)
        ["Olive Oil", 884, 0.0, 0.0, 100.0],
        ["Coconut Oil", 862, 0.0, 0.0, 100.0],
        ["Vegetable Oil", 884, 0.0, 0.0, 100.0],
        ["Butter", 717, 0.8, 0.1, 81.0],
        ["Mayonnaise", 680, 1.0, 1.0, 75.0],
        ["Peanut Butter (Smooth)", 588, 25.0, 20.0, 50.0],
        ["Soy Sauce / Toyo", 53, 5.0, 8.0, 0.1],
        ["Vinegar / Suka", 18, 0.0, 0.9, 0.0],
        ["Fish Sauce / Patis", 35, 5.0, 3.0, 0.0],
        ["Bagoong Alamang", 110, 10.0, 10.0, 4.0],
        ["Banana Ketchup", 115, 0.5, 28.0, 0.0],
        ["Oyster Sauce", 50, 1.0, 11.0, 0.0],
        
        # BREAD & SUPPLEMENTS
        ["Tasty Bread / White Bread", 266, 9.0, 50.0, 3.0],
        ["Whole Wheat Bread", 252, 12.5, 43.0, 3.4],
        ["Pandesal (per 100g)", 280, 8.0, 52.0, 4.0],
        ["Whey Protein Concentrate (Dry)", 400, 80.0, 5.0, 6.0],
        ["Whey Protein Isolate (Dry)", 370, 90.0, 2.0, 1.0],
        ["Creatine Monohydrate (Dry)", 0, 0.0, 0.0, 0.0]
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
    with col2: selected_food = st.selectbox("Select Ingredient:", st.session_state.food_db["Food Item"])
    with col3: weight = st.number_input("Amount (g):", min_value=0, value=100, step=10)
    
    if st.form_submit_button("➕ Add Ingredient"):
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
with st.expander("🛠️ Create Custom Recipe / Food (per 100g)"):
    with st.form("new_food_form", clear_on_submit=True):
        new_name = st.text_input("Recipe / Brand Name")
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
    st.write("### 📝 Logged Ingredients")
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
    st.info(f"No ingredients logged for {date_str}. Build your meal above!")
