import streamlit as st
import requests
import time

import streamlit as st

# Hide top-right buttons & collapse sidebar
st.set_page_config(
    page_title="Lease Rate Calculator",
    page_icon="🔢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Streamlit UI
st.title("Lease Rate Calculator")

# Custom CSS to Left-Align Input Fields & Style Button
st.markdown(
    """
    <style>
        /* Left align input fields */
        div[data-baseweb="input"] {
            text-align: left !important;
        }
        /* Style the Get Lease Rate button */
        div.stButton > button {
            background-color: #1E3A8A !important; /* Dark Blue */
            color: white !important;
            font-size: 16px;
            font-weight: bold;
            padding: 8px 20px;
            border-radius: 8px;
            border: none;
        }
        div.stButton > button:hover {
            background-color: #1E40AF !important; /* Slightly lighter blue on hover */
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# User Input: Date (Formats as MM/DD/YYYY)
selected_date = st.date_input("Select Lease Date", format="MM/DD/YYYY")

# Lease Term Input
term = st.number_input("Enter Lease Term (Months)", min_value=1, step=1)

# API URL
api_url = "https://lease-discount-rate.onrender.com/calculate"

# Custom CSS for Full-Screen Loading Overlay
spinner_style = """
    <style>
        .overlay {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.6);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }
        .spinner {
            border: 6px solid rgba(255, 255, 255, 0.2);
            border-top: 6px solid #3498db;
            border-radius: 50%;
            width: 80px;
            height: 80px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
"""

# Button to fetch lease rate
if st.button("Get Lease Rate"):
    if selected_date and term:
        # Display overlay spinner
        st.markdown(spinner_style, unsafe_allow_html=True)
        st.markdown('<div class="overlay"><div class="spinner"></div></div>', unsafe_allow_html=True)

        # Simulate processing time
        time.sleep(1)

        # API request (Still sends YYYY-MM-DD to match FastAPI format)
        params = {"date": selected_date.strftime("%Y-%m-%d"), "term": term}
        response = requests.get(api_url, params=params)

        # Remove spinner overlay effect
        st.markdown('<style>.overlay { display: none; }</style>', unsafe_allow_html=True)

        # Display results
        if response.status_code == 200:
            data = response.json()
            if "lease_rate" in data:
                st.success(f"Lease Rate: {data['lease_rate']}%")
            else:
                st.error("No lease rate found for the selected date and term.")
        else:
            st.error("Error fetching lease rate. Make sure FastAPI is running!")
    else:
        st.warning("Please enter both a date and lease term.")
