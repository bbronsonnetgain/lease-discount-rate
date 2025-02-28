import streamlit as st
import requests
import time
from datetime import datetime
from fpdf import FPDF

# Streamlit UI
st.markdown("<h1 style='text-align: center;'>Lease Rate Calculator</h1>", unsafe_allow_html=True)

# User Input: Date (Formats as MM/DD/YYYY)
selected_date = st.date_input("Commencement Date", format="MM/DD/YYYY")

# Lease Term Input
term = st.number_input("Lease Term (Months)", min_value=1, step=1)

# API URL
api_url = "https://lease-discount-rate.onrender.com/calculate"

# Initialize lease rate data variable
lease_rate_data = None

# Button to fetch lease rate
if st.button("Get Lease Rate"):
    if selected_date and term:
        with st.spinner("Fetching lease rate..."):
            time.sleep(1)
            params = {"date": selected_date.strftime("%Y-%m-%d"), "term": term}
            try:
                response = requests.get(api_url, params=params, timeout=10)
                response.raise_for_status()
                lease_rate_data = response.json()
            except requests.exceptions.RequestException:
                st.error("⚠️ Unable to fetch lease rate. Using cached data if available.")
                lease_rate_data = None

        if lease_rate_data and "lease_rate" in lease_rate_data:
            query_date = datetime.now().strftime("%m/%d/%Y")
            interest_rate_date = datetime.strptime(lease_rate_data["date"], "%Y-%m-%d").strftime("%m/%d/%Y")
            treasury_link = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value={lease_rate_data['date'][:4]}"

            # Display results
            st.markdown(
                f"""
                <div class="result-box">
                    <p class="lease-rate">Lease Rate: {lease_rate_data['lease_rate']:.3f}%</p>
                    <p><b>Date Query Was Ran:</b> {query_date}</p>
                    <p><b>Interest Rate Date Used:</b> {interest_rate_date}</p>
                    <p><b>Rate Calculation Formula:</b> {lease_rate_data['calculation']}</p>
                    <p><b>U.S. Treasury Data:</b> <a href="{treasury_link}" target="_blank">View Here</a></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Generate PDF report
            def generate_pdf():
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font("Arial", style="B", size=16)
                pdf.cell(200, 10, "Lease Rate Calculator Report", ln=True, align="C")

                pdf.ln(10)
                pdf.set_font("Arial", size=12)

                pdf.cell(0, 10, f"Query Date: {query_date}", ln=True)
                pdf.cell(0, 10, f"Lease Term: {term} months", ln=True)
                pdf.cell(0, 10, f"Interest Rate Date Used: {interest_rate_date}", ln=True)
                pdf.cell(0, 10, f"Lease Rate: {lease_rate_data['lease_rate']:.3f}%", ln=True)
                
                pdf.ln(5)
                pdf.multi_cell(0, 10, f"Rate Calculation Formula:\n{lease_rate_data['calculation']}")
                pdf.ln(5)
                
                pdf.set_font("Arial", "I", 12)
                pdf.cell(0, 10, "For more details, visit the U.S. Treasury website:", ln=True)
                pdf.set_text_color(0, 0, 255)  # Blue color for hyperlink
                pdf.cell(0, 10, "Treasury Data Link", ln=True, link=treasury_link)

                return pdf.output(dest="S").encode("latin1")

            pdf_data = generate_pdf()

            # Provide download button for PDF
            st.download_button(
                label="Download Report as PDF",
                data=pdf_data,
                file_name=f"lease_rate_report_{selected_date.strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )

        else:
            st.error("⚠️ No lease rate found. Using last known value.")
    else:
        st.warning("Please enter both a date and lease term.")
