from fastapi import FastAPI, Query, HTTPException
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import os

app = FastAPI()

# Define Audit Log File
AUDIT_LOG_FILE = "audit_log.csv"

# Mapping Treasury terms to user-friendly labels (for Rate Calculation Formula only)
TREASURY_LABELS = {
    "BC_1MONTH": "1 Month", "BC_3MONTH": "3 Months", "BC_6MONTH": "6 Months",
    "BC_1YEAR": "1 Year", "BC_2YEAR": "2 Years", "BC_3YEAR": "3 Years",
    "BC_5YEAR": "5 Years", "BC_7YEAR": "7 Years", "BC_10YEAR": "10 Years",
    "BC_20YEAR": "20 Years", "BC_30YEAR": "30 Years"
}

# Treasury API Fetch Function
def get_treasury_data(year: int):
    url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
    response = requests.get(url)

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.content, "xml")
    entries = soup.find_all("entry")

    treasury_data = {}
    for entry in entries:
        date_tag = entry.find("d:NEW_DATE")
        if date_tag:
            date_str = date_tag.text[:10]  # Extract YYYY-MM-DD
            treasury_data[date_str] = {
                "BC_1MONTH": entry.find("d:BC_1MONTH"),
                "BC_3MONTH": entry.find("d:BC_3MONTH"),
                "BC_6MONTH": entry.find("d:BC_6MONTH"),
                "BC_1YEAR": entry.find("d:BC_1YEAR"),
                "BC_2YEAR": entry.find("d:BC_2YEAR"),
                "BC_3YEAR": entry.find("d:BC_3YEAR"),
                "BC_5YEAR": entry.find("d:BC_5YEAR"),
                "BC_7YEAR": entry.find("d:BC_7YEAR"),
                "BC_10YEAR": entry.find("d:BC_10YEAR"),
                "BC_20YEAR": entry.find("d:BC_20YEAR"),
                "BC_30YEAR": entry.find("d:BC_30YEAR"),
            }

            # Convert data to float
            for key, value in treasury_data[date_str].items():
                if value and value.text:
                    treasury_data[date_str][key] = float(value.text)
                else:
                    treasury_data[date_str][key] = None

    return treasury_data

# Find Most Recent Valid Treasury Date
def get_most_recent_date(requested_date: str):
    year = int(requested_date[:4])
    treasury_data = get_treasury_data(year)

    # If no data in current year, check previous year
    if not treasury_data:
        treasury_data = get_treasury_data(year - 1)

    if not treasury_data:
        raise HTTPException(status_code=404, detail="No valid Treasury data found for the given date.")

    # Convert requested date to datetime object
    req_date = datetime.strptime(requested_date, "%Y-%m-%d")

    # Find the most recent available date before or on requested_date
    available_dates = sorted(treasury_data.keys(), reverse=True)
    for date in available_dates:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        if date_obj <= req_date:
            return date, treasury_data[date]

    # If no date found, check prior years
    for past_year in range(year - 1, 2000, -1):  # Prevent infinite loops
        treasury_data_prev = get_treasury_data(past_year)
        if treasury_data_prev:
            available_dates_prev = sorted(treasury_data_prev.keys(), reverse=True)
            for date in available_dates_prev:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                if date_obj <= req_date:
                    return date, treasury_data_prev[date]

    raise HTTPException(status_code=404, detail="No valid Treasury data found for the given date.")

# Convert months into corresponding U.S. Treasury column names
def get_lease_rate_for_term(treasury_data, term):
    # Mapping lease terms (in months) to U.S. Treasury column names
    term_mapping = {
        1: "BC_1MONTH", 3: "BC_3MONTH", 6: "BC_6MONTH",
        12: "BC_1YEAR", 24: "BC_2YEAR", 36: "BC_3YEAR",
        60: "BC_5YEAR", 84: "BC_7YEAR", 120: "BC_10YEAR",
        240: "BC_20YEAR", 360: "BC_30YEAR"
    }

    # Extract available terms in treasury data (ignoring None values)
    available_terms = {key: value for key, value in treasury_data.items() if value is not None}

    # **Exact match case**
    if term in term_mapping and term_mapping[term] in available_terms:
        friendly_label = TREASURY_LABELS.get(term_mapping[term], term_mapping[term])  # Convert to user-friendly format
        return available_terms[term_mapping[term]], f"Exact match found for {friendly_label}"

    # **Find closest shorter and longer term**
    shorter_term = max(
        [t for t in term_mapping.keys() if t < term and term_mapping[t] in available_terms], default=None
    )
    longer_term = min(
        [t for t in term_mapping.keys() if t > term and term_mapping[t] in available_terms], default=None
    )

    # **Handle cases where only one bound exists**
    if shorter_term is None:
        friendly_label = TREASURY_LABELS.get(term_mapping[longer_term], term_mapping[longer_term])
        return available_terms[term_mapping[longer_term]], f"Closest match found: {friendly_label}"
    if longer_term is None:
        friendly_label = TREASURY_LABELS.get(term_mapping[shorter_term], term_mapping[shorter_term])
        return available_terms[term_mapping[shorter_term]], f"Closest match found: {friendly_label}"

    # **Apply Interpolation**
    shorter_rate = available_terms[term_mapping[shorter_term]]
    longer_rate = available_terms[term_mapping[longer_term]]
    interpolated_rate = (((longer_rate - shorter_rate) / (longer_term - shorter_term)) * (term - shorter_term)) + shorter_rate

    # Convert Treasury terms to user-friendly labels for formula output
    short_label = TREASURY_LABELS.get(term_mapping[shorter_term], term_mapping[shorter_term])
    long_label = TREASURY_LABELS.get(term_mapping[longer_term], term_mapping[longer_term])

    calculation_formula = f"(({longer_rate} - {shorter_rate}) / ({long_label} - {short_label})) * ({term} - {short_label}) + {shorter_rate}"

    return interpolated_rate, calculation_formula

# Audit Log Function
def log_audit_entry(query_date, rate_date, term, lease_rate, calculation):
    log_entry = {
        "Date Query Was Ran": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Interest Rate Date": rate_date,
        "Rate Calculation": calculation,
        "Lease Rate (%)": f"{lease_rate:.2f}%",
        "U.S. Treasury Table": f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value={rate_date[:4]}",
    }

    file_exists = os.path.isfile(AUDIT_LOG_FILE)

    with open(AUDIT_LOG_FILE, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=log_entry.keys())

        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)

# API Endpoint
@app.get("/calculate")
def get_lease_rate(date: str = Query(..., description="Lease date (YYYY-MM-DD)"), term: int = Query(..., description="Lease term in months")):
    recent_date, treasury_data = get_most_recent_date(date)
    lease_rate, calculation = get_lease_rate_for_term(treasury_data, term)

    log_audit_entry(datetime.now().strftime("%Y-%m-%d"), recent_date, term, lease_rate, calculation)

    return {
        "date": recent_date,
        "term": term,
        "lease_rate": lease_rate,
        "calculation": calculation
    }
