import streamlit as st
import requests
import time
from datetime import datetime

# Hide top-right buttons & collapse sidebar
st.set_page_config(
    page_title="Lease Rate Calculator",
    page_icon="🔢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS for styling
st.markdown(
    """
    <style>
        /* Import Poppins Font */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

        /* Apply Poppins font globally */
        html, body, [class*="st-"] {
            font-family: 'Poppins', sans-serif;
        }

        /* Hide top-right Streamlit menu */
        header { visibility: hidden; }

        /* Hide "Manage App" button */
        .stDeployButton { display: none !important; }

        /* Style input field labels */
        .st-emotion-cache-10trblm {
            font-size: 18px !important;
            font-weight: bold;
            font-family: 'Poppins', sans-serif;
        }

        /* Style the Get Lease Rate button */
        div.stButton > button {
            background-color: #1E3A8A !important;
            color: white !important;
            font-size: 16px;
            font-weight: bold;
            padding: 8px 20px;
            border-radius: 8px;
            border: none;
            font-family: 'Poppins', sans-serif;
        }
        div.stButton > button:hover {
            background-color: #1E40AF !important;
        }

        /* Results box styling */
        .result-box {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #ddd;
            margin-top: 15px;
        }

        /* Lease Rate Styling - Changed to Black */
        .lease-rate {
            font-size: 16px;
            font-weight: bold;
            color: black !important;
        }

        /* Ensure all result text matches input labels */
        .result-box p {
            font-size: 18px !important;
            font-family: 'Poppins', sans-serif;
        }

    </style>
    """,
    unsafe_allow_html=True,
)

# Custom CSS to Hide Bottom-Right Icons (Streamlit Branding)
st.markdown(
    """
    <style>
        /* Hide bottom-right icons */
        .viewerBadge_container__1QSob { display: none !important; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Streamlit UI
st.markdown("<h1 style='text-align: center;'>Lease Rate Calculator</h1>", unsafe_allow_html=True)

# User Input: Date (Formats as MM/DD/YYYY)
selected_date = st.date_input("Commencement Date", format="MM/DD/YYYY")

# Lease Term Input
term = st.number_input("Lease Term (Months)", min_value=1, step=1)

# API URL
api_url = "https://lease-discount-rate.onrender.com/calculate"

# Button to fetch lease rate
if st.button("Get Lease Rate"):
    if selected_date and term:
        # Display overlay spinner
        with st.spinner("Fetching lease rate..."):
            time.sleep(1)

            # API request (formats date correctly)
            params = {"date": selected_date.strftime("%Y-%m-%d"), "term": term}
            response = requests.get(api_url, params=params)

        # Display results
        if response.status_code == 200:
            data = response.json()
            if "lease_rate" in data:
                # Format dates to MM/DD/YYYY
                query_date = datetime.now().strftime("%m/%d/%Y")
                interest_rate_date = datetime.strptime(data["date"], "%Y-%m-%d").strftime("%m/%d/%Y")
                treasury_link = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value={data['date'][:4]}"

                # Results Box
                st.markdown(
                    f"""
                    <div class="result-box">
                        <p class="lease-rate">Lease Rate: {data['lease_rate']}%</p>
                        <p><b>Date Query Was Ran:</b> {query_date}</p>
                        <p><b>Interest Rate Date Used:</b> {interest_rate_date}</p>
                        <p><b>Rate Calculation Formula:</b> {data['calculation']}</p>
                        <p><b>U.S. Treasury Data:</b> <a href="{treasury_link}" target="_blank">View Here</a></p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.error("No lease rate found for the selected date and term.")
        else:
            st.error("Error fetching lease rate. Make sure FastAPI is running!")

    else:
        st.warning("Please enter both a date and lease term.")
