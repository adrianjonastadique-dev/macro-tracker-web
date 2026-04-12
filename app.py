import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION ---
st.set_page_config(page_title="Macro Tracker", page_icon="🍳")
CHECKOUT_LINK = "https://your-store.lemonsqueezy.com/checkout/buy/YOUR_PRODUCT_ID" # Swap this

# --- INITIALIZE SESSION MEMORY ---
# This ensures the app remembers the user is logged in after they click buttons
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# --- DATABASE CONNECTION ---
# This safely pulls your live Google Sheet data
@st.cache_data(ttl=60) # Caches data for 60 seconds so it runs fast
def load_user_database():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Make sure your tab is actually named "Users"
    df = conn.read(worksheet="Users") 
    return df

# ==========================================
# 1. THE LOGIN SCREEN (Locks the app)
# ==========================================
if not st.session_state.logged_in:
    st.title("🍳 Welcome to Macro Tracker")
    st.write("Please log in to access your dashboard.")
    
    with st.form("login_form"):
        login_email = st.text_input("Email Address")
        submit_button = st.form_submit_button("Log In")
        
        if submit_button:
            if login_email:
                try:
                    df = load_user_database()
                    # Search the database for the entered email
                    user_row = df[df['Email'] == login_email]
                    
                    if not user_row.empty:
                        # Success! Save their data to the session
                        st.session_state.logged_in = True
                        st.session_state.user_data = user_row.iloc[0].to_dict()
                        st.rerun() # Refreshes the page to show the dashboard
                    else:
                        st.error("Email not found. Please check your spelling or register.")
                except Exception as e:
                    st.error(f"Could not connect to database. Check your secrets. Error: {e}")
            else:
                st.warning("Please enter an email.")
                
    st.stop() # This halts the script so logged-out users can't see the app below

# ==========================================
# 2. PAYWALL & TRIAL MATH
# ==========================================
user = st.session_state.user_data

# Clean up data coming from Google Sheets
is_paid_raw = str(user.get("IsPaid", "FALSE")).strip().upper()
is_paid = (is_paid_raw == "TRUE")

try:
    # Converts Google Sheet date into a Python date object
    join_date = pd.to_datetime(user.get("JoinDate")).date()
except:
    # Failsafe if the date column is blank or corrupted
    join_date = datetime.now().date()

today = datetime.now().date()
days_active = (today - join_date).days
trial_length = 7
days_left = trial_length - days_active

# ==========================================
# 3. THE SIDEBAR ROUTER
# ==========================================
with st.sidebar:
    st.header("👤 Account Status")
    st.write(f"Logged in as: **{user['Email']}**")
    
    if is_paid:
        st.success("Lifetime Premium Active 👑")
    elif not is_paid and days_left > 0:
        st.warning(f"Free Trial: **{days_left} days left**")
        st.progress(max(0, min(days_active / trial_length, 1.0)))
        st.divider()
        st.write("Love the app? Don't wait.")
        st.link_button("🚀 Upgrade to Premium ($75)", CHECKOUT_LINK, use_container_width=True)
    else:
        st.error("Free Trial Expired 🔒")
        st.write("Your 7-day trial has ended. Upgrade to lifetime Premium to unlock your macros!")
        st.link_button("🔓 Unlock Premium ($75)", CHECKOUT_LINK, use_container_width=True)
        
        # Give them a way to log out if they are expired
        if st.button("Log Out"):
            st.session_state.logged_in = False
            st.session_state.user_data = None
            st.rerun()
            
        st.stop() # The Bouncer
        
    st.divider()
    if st.button("Log Out", key="active_logout"):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

# ==========================================
# 4. THE ACTUAL APP DASHBOARD
# ==========================================
st.title("🍳 Daily Macro Tracker")
st.write("Welcome back! Here are your macros for today.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Calories", "0 / 2000")
col2.metric("Protein", "0g / 150g")
col3.metric("Carbs", "0g / 200g")
col4.metric("Fats", "0g / 65g")

st.divider()

st.subheader("Log a Meal")
food_choice = st.selectbox("Search Food Library", [
    "Chicken Breast (100g)", 
    "Potatoes (100g)", 
    "Carrots (100g)", 
    "Starbucks Cold Brew"
])

if st.button("Add to Daily Log"):
    st.success(f"Added {food_choice} to your log!")
