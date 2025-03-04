import streamlit as st
import requests
import time
from datetime import datetime
from fpdf import FPDF
import pandas as pd
import io

# Hide top-right buttons & collapse sidebar
st.set_page_config(
    page_title="Lease Rate Calculator",
    page_icon="netgain_favicon.ico",
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
            font-size: 16px !important;
            font-family: 'Poppins', sans-serif;
        }
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

# Function to generate PDF
def generate_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=18)
    pdf.cell(200, 10, "Lease Rate Calculation Report", ln=True, align='C')
    pdf.ln(8)
    pdf.set_font("Arial", size=12)
    pdf.cell(80, 8, f"Commencement Date: {selected_date.strftime('%m/%d/%Y')}", ln=True)
    pdf.cell(80, 8, f"Lease Term (Months): {term}", ln=True)
    pdf.cell(80, 8, f"Lease Rate: {lease_rate:.3f}%", ln=True)
    pdf.cell(80, 8, f"Date Query Was Ran: {query_date}", ln=True)
    pdf.cell(80, 8, f"Interest Rate Date Used: {interest_rate_date}", ln=True)
    pdf.cell(80, 8, f"Rate Calculation Formula: {data['calculation']}", ln=True)
    return pdf.output(dest="S").encode("latin1")

# Function to generate XLSX
def generate_xlsx():
    df = pd.DataFrame({
        "Field": ["Commencement Date", "Lease Term (Months)", "Lease Rate", "Date Query Was Ran", "Interest Rate Date Used", "Rate Calculation Formula"],
        "Value": [selected_date.strftime('%m/%d/%Y'), term, f"{lease_rate:.3f}%", query_date, interest_rate_date, data["calculation"]]
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Lease Report')
    return output.getvalue()

# Button to fetch lease rate
if st.button("Get Lease Rate"):
    if selected_date and term:
        with st.spinner("Fetching lease rate..."):
            time.sleep(1)
            params = {"date": selected_date.strftime("%Y-%m-%d"), "term": term}
            response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            lease_rate = round(data['lease_rate'], 3)
            query_date = datetime.now().strftime("%m/%d/%Y")
            interest_rate_date = datetime.strptime(data["date"], "%Y-%m-%d").strftime("%m/%d/%Y")
            st.markdown(
                f"""
                <div class="result-box">
                    <p class="lease-rate">Lease Rate: {lease_rate:.3f}%</p>
                    <p><b>Date Query Was Ran:</b> {query_date}</p>
                    <p><b>Interest Rate Date Used:</b> {interest_rate_date}</p>
                    <p><b>Rate Calculation Formula:</b> {data['calculation']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            pdf_bytes = generate_pdf()
            xlsx_bytes = generate_xlsx()
            st.download_button("Download PDF", data=pdf_bytes, file_name="Lease_Report.pdf", mime="application/pdf")
            st.download_button("Download XLSX", data=xlsx_bytes, file_name="Lease_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.error("Error fetching lease rate. Make sure FastAPI is running!")
    else:
        st.warning("Please enter both a date and lease term.")
