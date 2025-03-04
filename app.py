import streamlit as st
import requests
import time
from datetime import datetime
from fpdf import FPDF

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

        /* Style input labels */
        label {
            font-size: 18px !important;
            font-weight: bold;
            font-family: 'Poppins', sans-serif;
        }

        /* Style input fields */
        div[data-baseweb="input"] {
            text-align: left !important;
        }

        /* Style the Get Lease Rate button */
        div.stButton > button {
            background-color: #1E3A8A !important;
            color: white !important;
            font-size: 18px;
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
            font-size: 22px;
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
st.title("Lease Rate Calculator")

# User Input: Date (Formats as MM/DD/YYYY)
selected_date = st.date_input("Commencement Date", format="MM/DD/YYYY")

# Lease Term Input
term = st.number_input("Lease Term (Months)", min_value=1, step=1)

# API URL
api_url = "https://lease-discount-rate.onrender.com/calculate"

# Button to fetch lease rate
if st.button("Get Lease Rate"):
    if selected_date and term:
        with st.spinner("Fetching lease rate..."):
            time.sleep(1)

            # API request
            params = {"date": selected_date.strftime("%Y-%m-%d"), "term": term}
            response = requests.get(api_url, params=params)

        if response.status_code == 200:
            data = response.json()
            if "lease_rate" in data:
                lease_rate = round(data['lease_rate'], 3)

                query_date = datetime.now().strftime("%m/%d/%Y")
                interest_rate_date = datetime.strptime(data["date"], "%Y-%m-%d").strftime("%m/%d/%Y")
                treasury_link = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value={data['date'][:4]}"

                # Display results
                st.markdown(
                    f"""
                    <div class="result-box">
                        <p class="lease-rate">Lease Rate: {lease_rate}%</p>
                        <p><b>Date Query Was Ran:</b> {query_date}</p>
                        <p><b>Interest Rate Date Used:</b> {interest_rate_date}</p>
                        <p><b>Rate Calculation Formula:</b> {data['calculation']}</p>
                        <p><b>U.S. Treasury Data:</b> <a href="{treasury_link}" target="_blank">View Here</a></p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # ✅ Export to PDF & XLSX Buttons
                from fpdf import FPDF
                import pandas as pd
                import io

                def generate_pdf():
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()

                    # Set title
                    pdf.set_font("Arial", style="B", size=18)
                    pdf.cell(200, 10, "Lease Rate Calculation Report", ln=True, align='C')
                    pdf.ln(8)  # Reduced space

                    # Set font for content
                    pdf.set_font("Arial", size=12)

                    # Function to add bold labels with values on the same line
                    def add_label_value(label, value, link=None):
                        pdf.set_font("Arial", style="B", size=12)
                        pdf.cell(80, 8, label, ln=False)
                        pdf.set_font("Arial", size=12)
                        if link:
                            pdf.set_text_color(0, 0, 255)  # Blue color for hyperlink
                            pdf.set_font("Arial", size=12, style="U")  # Underline for link effect
                            pdf.cell(0, 8, value, ln=True, link=link)
                            pdf.set_text_color(0, 0, 0)  # Reset color to black
                        else:
                            pdf.cell(0, 8, value, ln=True)

                    # Standard Key-Value Pairs
                    add_label_value("Commencement Date:", selected_date.strftime('%m/%d/%Y'))
                    add_label_value("Lease Term (Months):", str(term))
                    add_label_value("Lease Rate:", f"{lease_rate}%")
                    add_label_value("Date Query Was Ran:", query_date)
                    add_label_value("Interest Rate Date Used:", interest_rate_date)
                    add_label_value("Rate Calculation Formula:", data["calculation"])  # Moved to standard format
                    add_label_value("U.S. Treasury Data:", "Treasury Link", link=treasury_link)

                    return pdf.output(dest="S").encode("latin1")
                
                def generate_xlsx():
                    df = pd.DataFrame({
                        "Field": ["Commencement Date", "Lease Term (Months)", "Lease Rate", "Date Query Was Ran", "Interest Rate Date Used", "Rate Calculation Formula", "U.S. Treasury Data"],
                        "Value": [selected_date.strftime('%m/%d/%Y'), term, f"{lease_rate}%", query_date, interest_rate_date, data["calculation"], treasury_link]
                    })
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Lease Report')
                    return output.getvalue()
                
                pdf_bytes = generate_pdf()
                xlsx_bytes = generate_xlsx()

                # Display buttons with icons
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("📄 Download PDF", data=pdf_bytes, file_name="Lease_Report.pdf", mime="application/pdf")
                with col2:
                    st.download_button("📊 Download XLSX", data=xlsx_bytes, file_name="Lease_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            else:
                st.error("No lease rate found for the selected date and term.")
        else:
            st.error("Error fetching lease rate. Make sure FastAPI is running!")

    else:
        st.warning("Please enter both a date and lease term.")

