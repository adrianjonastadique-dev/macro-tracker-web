import streamlit as st
import pandas as pd
import datetime
import time
import random
from streamlit_gsheets import GSheetsConnection

# 1. App Configuration
st.set_page_config(page_title="Macro Tracker", layout="centered")
# --- MINIMALIST STYLING ---
st.markdown("""
    <style>
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Global Background & Font */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Minimalist Metric Cards */
    [data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
    }
    
    /* Clean Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        padding: 8px 16px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #161b22 !important;
        color: #58a6ff !important;
    }

    /* Slick Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #0d1117;
        border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)
# Establish the master connection early so the login screen can use it
conn = st.connection("gsheets", type=GSheetsConnection)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Security state initialization
if "last_request" not in st.session_state:
    st.session_state.last_request = 0

# Generate a random math problem once per session for the CAPTCHA
if "num1" not in st.session_state:
    st.session_state.num1 = random.randint(1, 10)
    st.session_state.num2 = random.randint(1, 10)

# Initialize the target calories in global memory (Fallback)
if "target_calories" not in st.session_state:
    st.session_state.target_calories = 2000

# ==========================================
# --- THE FIX: CLOUD-SYNCED CALLBACK ---
# ==========================================
def update_calorie_goal():
    new_goal = st.session_state.calorie_input_widget
    st.session_state.target_calories = new_goal
    
    # Silently save the new goal directly to the user's profile in Google Sheets
    try:
        users_db = conn.read(worksheet="Users", ttl=0)
        # Ensure the column exists for older accounts
        if "TargetCalories" not in users_db.columns:
            users_db["TargetCalories"] = 2000
            
        # Find the logged-in user and update their specific goal
        users_db.loc[users_db["Username"].astype(str) == st.session_state.username, "TargetCalories"] = new_goal
        conn.update(worksheet="Users", data=users_db)
    except Exception as e:
        pass # Failsafe so it doesn't interrupt the user experience

# ==========================================
# --- TRUE AUTHENTICATION GATE ---
# ==========================================
if not st.session_state.authenticated:
    st.title("🔒 Premium Deficit Tracker")
    st.info("Log in to your dashboard or create a new account below.")
    
    tab_login, tab_register = st.tabs(["🔐 Secure Login", "📝 Create Account"])
    
    # --- TAB 1: LOGIN ---
    with tab_login:
        with st.form("login_form"):
            entered_user = st.text_input("Username / Client ID")
            entered_pwd = st.text_input("Password", type="password")
            
            # Honeypot: Invisible to humans, traps bots that auto-fill everything
            st.markdown('<style>div[data-testid="stTextInput"]:has(input[aria-label="bot_trap"]) {display: none;}</style>', unsafe_allow_html=True)
            trap = st.text_input("bot_trap", label_visibility="collapsed")
            
            if st.form_submit_button("Login"):
                current_time = time.time()
                
                # Layer 1: Cooldown Timer (3 seconds)
                if current_time - st.session_state.last_request < 3.0:
                    st.error("⏳ Please wait a few seconds before trying again.")
                    st.stop()
                st.session_state.last_request = current_time
                
                # Layer 2: Honeypot Trap
                if trap != "":
                    st.warning("Automated behavior detected. Request blocked.")
                    st.stop()
                
                if entered_user.strip() != "" and entered_pwd.strip() != "":
                    try:
                        # Fetch the Users database tab
                        users_db = conn.read(worksheet="Users", ttl=0)
                        users_db = users_db.dropna(subset=["Username"]) # Ignore empty rows
                        
                        # Check if the username exists in the sheet
                        user_match = users_db[users_db["Username"].astype(str) == entered_user.strip()]
                        
                        if not user_match.empty:
                            # Grab the correct password from the database
                            correct_pwd = str(user_match.iloc[0]["Password"]).strip()
                            
                            if entered_pwd.strip() == correct_pwd:
                                # Success! Let them in.
                                st.session_state.authenticated = True
                                st.session_state.username = entered_user.strip()
                                
                                # FETCH SAVED CALORIE GOAL FROM CLOUD
                                if "TargetCalories" in user_match.columns and pd.notna(user_match.iloc[0]["TargetCalories"]):
                                    st.session_state.target_calories = int(user_match.iloc[0]["TargetCalories"])
                                else:
                                    st.session_state.target_calories = 2000
                                    
                                st.rerun()
                            else:
                                st.error("❌ Incorrect password.")
                        else:
                            st.error("❌ Username not found. Please check your credentials.")
                    except Exception as e:
                        # Prints the exact error if Google Sheets rejects the connection
                        st.error(f"🚨 Database error: {str(e)}") 
                else:
                    st.warning("Please enter both a Username and Password.")
                    
    # --- TAB 2: REGISTRATION ---
    with tab_register:
        with st.form("registration_form", clear_on_submit=True):
            st.write("**Register a New Account**")
            new_user = st.text_input("New Username")
            new_pwd = st.text_input("New Password", type="password")
            
            # The CAPTCHA challenge
            captcha_ans = st.number_input(f"Prove you are human: What is {st.session_state.num1} + {st.session_state.num2}?", step=1, value=None)
            
            if st.form_submit_button("Create Account"):
                # 1. Verify the math
                if captcha_ans != (st.session_state.num1 + st.session_state.num2):
                    st.error("❌ Incorrect CAPTCHA. Try again.")
                    st.stop()
                
                # 2. Ensure fields aren't blank
                if not new_user.strip() or not new_pwd.strip():
                    st.error("⚠️ Username and Password cannot be blank.")
                    st.stop()
                    
                # 3. Check database and register
                try:
                    users_db = conn.read(worksheet="Users", ttl=0).dropna(how="all")
                    
                    # Ensure columns exist if the sheet is completely blank
                    if "Username" not in users_db.columns:
                        users_db = pd.DataFrame(columns=["Username", "Password", "TargetCalories"])
                        
                    if new_user.strip() in users_db["Username"].astype(str).values:
                        st.error("⚠️ That Username is already taken. Please choose another.")
                    else:
                        # Register new user with a default goal of 2000
                        new_account = pd.DataFrame([{
                            "Username": new_user.strip(), 
                            "Password": new_pwd.strip(),
                            "TargetCalories": 2000
                        }])
                        updated_users = pd.concat([users_db, new_account], ignore_index=True)
                        conn.update(worksheet="Users", data=updated_users)
                        
                        st.success("✅ Account created successfully! You can now switch to the Login tab.")
                        
                        # Reset CAPTCHA for the next person
                        st.session_state.num1 = random.randint(1, 10)
                        st.session_state.num2 = random.randint(1, 10)
                except Exception as e:
                    # Prints the exact error if Google Sheets rejects the connection
                    st.error(f"🚨 Database error during registration: {str(e)}")

    st.stop() # Stops the rest of the app from loading until unlocked

# ==========================================
# --- MAIN APP LOADS ONLY AFTER LOGIN ---
# ==========================================

with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    st.divider()
    st.header("🎯 Daily Targets")
    
    # Connected to the memory vault and the cloud-sync callback
    st.number_input(
        "Calorie Goal:", 
        min_value=1000, 
        max_value=5000, 
        step=50, 
        value=st.session_state.target_calories, 
        key="calorie_input_widget",
        on_change=update_calorie_goal
    )
    
    cal_goal = st.session_state.target_calories

st.title("📊 Daily Deficit Tracker")

col_date, _ = st.columns([1, 2])
with col_date:
    selected_date = st.date_input("📅 Date", datetime.date.today())

# ==========================================
# --- THE CLOUD DATABASE (MAIN LOG) ---
# ==========================================

# Fetch the ENTIRE master food database from Sheet1
global_db = conn.read(worksheet="Sheet1", ttl=0)
global_db = global_db.dropna(how="all")

# Armor: If the sheet is completely blank, build the columns so Python doesn't crash
if "Username" not in global_db.columns:
    global_db = pd.DataFrame(columns=[
        "Username", "Date", "Meal", "Food Item", "Amount (g)", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"
    ])

# Force dates to be text to prevent matching bugs
global_db["Date"] = global_db["Date"].astype(str)

# THE BOUNCER: Filter the database so this user ONLY sees their own data
user_log = global_db[global_db["Username"] == st.session_state.username]

# Filter the user's data for the specific day they selected
date_str = selected_date.strftime("%Y-%m-%d")
todays_log = user_log[user_log["Date"] == date_str]

# ==========================================
# --- CORE FOOD DATABASE ---
# ==========================================
if 'food_db' not in st.session_state:
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
        
        # AROMATICS & RAW VEG
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
        
        # OILS, FATS & CONDIMENTS
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
        ["Creatine Monohydrate (Dry)", 0, 0.0, 0.0, 0.0],

        # NUTS & SEEDS
        ["Almonds (Dry Roasted)", 598, 21.0, 21.0, 53.0],
        ["Walnuts (Raw)", 654, 15.0, 14.0, 65.0],
        ["Peanuts (Dry Roasted)", 585, 24.0, 21.0, 50.0],
        ["Cashews (Dry Roasted)", 574, 15.0, 33.0, 46.0],
        ["Chia Seeds", 486, 17.0, 42.0, 31.0],

        # PROTEIN BARS
        ["Quest Protein Bar (1 Bar)", 200, 21.0, 22.0, 8.0],
        ["Barebells Protein Bar (1 Bar)", 200, 20.0, 16.0, 7.0],
        ["Kirkland Protein Bar (1 Bar)", 190, 21.0, 22.0, 7.0]
    ]
    st.session_state.food_db = pd.DataFrame(db_raw, columns=["Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"])
    st.session_state.food_db = st.session_state.food_db.sort_values(by="Food Item").reset_index(drop=True)

# ==========================================
# --- DATA ENTRY TABS ---
# ==========================================
st.subheader("🍽️ Log Food")
tab1, tab2 = st.tabs(["📚 From Database", "✍️ Custom Recipe"])

with tab1:
    with st.form("food_entry_form", clear_on_submit=False):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1: meal_num = st.selectbox("Meal:", ["Meal 1", "Meal 2", "Meal 3", "Snacks"])
        with col2: selected_food = st.selectbox("Select Food:", st.session_state.food_db["Food Item"])
        with col3: weight = st.number_input("Amount (g):", min_value=0, value=100, step=10)
        
        if st.form_submit_button("➕ Add Food"):
            food_row = st.session_state.food_db[st.session_state.food_db["Food Item"] == selected_food].iloc[0]
            multiplier = weight / 100
            
            new_entry = pd.DataFrame([{
                "Username": st.session_state.username,
                "Date": date_str, "Meal": meal_num, "Food Item": selected_food,
                "Amount (g)": weight, "Calories": food_row["Calories"] * multiplier,
                "Protein (g)": food_row["Protein (g)"] * multiplier,
                "Carbs (g)": food_row["Carbs (g)"] * multiplier,
                "Fats (g)": food_row["Fats (g)"] * multiplier
            }])
            
            updated_db = pd.concat([global_db, new_entry], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_db)
            st.cache_data.clear()
            st.rerun()

with tab2:
    with st.form("custom_recipe_form", clear_on_submit=True):
        st.caption("Enter the total macros for your custom meal or recipe.")
        col1, col2 = st.columns([1, 2])
        with col1: custom_meal_num = st.selectbox("Meal:", ["Meal 1", "Meal 2", "Meal 3", "Snacks"], key="custom_meal")
        with col2: custom_name = st.text_input("Recipe / Food Name:", placeholder="e.g., Mom's Spaghetti")
        
        c1, c2, c3, c4 = st.columns(4)
        c_cals = c1.number_input("Calories", min_value=0, step=10)
        c_prot = c2.number_input("Protein (g)", min_value=0, step=1)
        c_carb = c3.number_input("Carbs (g)", min_value=0, step=1)
        c_fat = c4.number_input("Fats (g)", min_value=0, step=1)
        
        if st.form_submit_button("➕ Log Custom Recipe"):
            if custom_name:
                new_entry = pd.DataFrame([{
                    "Username": st.session_state.username,
                    "Date": date_str, "Meal": custom_meal_num, "Food Item": f"⭐ {custom_name}",
                    "Amount (g)": "Custom", 
                    "Calories": c_cals, "Protein (g)": c_prot, "Carbs (g)": c_carb, "Fats (g)": c_fat
                }])
                
                updated_db = pd.concat([global_db, new_entry], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_db)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Please enter a name for your custom recipe!")

st.divider()

# ==========================================
# --- DASHBOARD & MACRO TRACKING ---
# ==========================================
total_cals = todays_log["Calories"].sum() if not todays_log.empty else 0
total_prot = todays_log["Protein (g)"].sum() if not todays_log.empty else 0
total_carbs = todays_log["Carbs (g)"].sum() if not todays_log.empty else 0
total_fats = todays_log["Fats (g)"].sum() if not todays_log.empty else 0
remaining_cals = cal_goal - total_cals

st.write("**Calorie Progress**")
st.progress(min(max(total_cals / cal_goal, 0.0), 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("Target", f"{cal_goal}")
c2.metric("Consumed", f"{total_cals:.0f}")
c3.metric("Remaining", f"{remaining_cals:.0f}")

st.write("") 
st.write("**Total Macros Today**")
m1, m2, m3 = st.columns(3)
m1.metric("Protein", f"{total_prot:.0f}g")
m2.metric("Carbs", f"{total_carbs:.0f}g")
m3.metric("Fats", f"{total_fats:.0f}g")

st.divider()

if not todays_log.empty:
    st.write("### 📝 Logged Foods")
    for original_index, row in todays_log.iterrows():
        list_col1, list_col2, list_col3 = st.columns([2, 3, 1])
        with list_col1: st.write(f"**{row['Meal']}**\n{row['Food Item']}")
        with list_col2: st.write(f"🔥 {row['Calories']:.0f} kcal (P: {row['Protein (g)']:.1f}g | C: {row['Carbs (g)']:.1f}g | F: {row['Fats (g)']:.1f}g)")
        with list_col3:
            if st.button("❌", key=f"del_{original_index}"):
                global_db = global_db.drop(original_index)
                conn.update(worksheet="Sheet1", data=global_db)
                st.cache_data.clear()
                st.rerun()
