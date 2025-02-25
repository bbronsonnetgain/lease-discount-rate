from fastapi import FastAPI, Query, HTTPException
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

app = FastAPI()

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
                1: entry.find("d:BC_1YEAR"),
                2: entry.find("d:BC_2YEAR"),
                3: entry.find("d:BC_3YEAR"),
                5: entry.find("d:BC_5YEAR"),
                7: entry.find("d:BC_7YEAR"),
                10: entry.find("d:BC_10YEAR"),
                20: entry.find("d:BC_20YEAR"),
                30: entry.find("d:BC_30YEAR"),
            }

            # Convert data to float
            for key, value in treasury_data[date_str].items():
                if value and value.text:
                    treasury_data[date_str][key] = float(value.text)
                else:
                    treasury_data[date_str][key] = None

    return treasury_data

# **🔹 Function to Find Most Recent Valid Date**
def get_most_recent_date(requested_date: str):
    year = int(requested_date[:4])
    treasury_data = get_treasury_data(year)

    # **If no data in current year, check previous year**
    if not treasury_data:
        treasury_data = get_treasury_data(year - 1)

    if not treasury_data:
        raise HTTPException(status_code=404, detail="No valid Treasury data found for the given date.")

    # Convert date to datetime object
    req_date = datetime.strptime(requested_date, "%Y-%m-%d")

    # **Find the most recent available date before or on requested_date**
    available_dates = sorted(treasury_data.keys(), reverse=True)
    for date in available_dates:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        if date_obj <= req_date:
            return date, treasury_data[date]

    # **If no date found in the current year, check prior years**
    for past_year in range(year - 1, 2000, -1):  # Avoid infinite loops
        treasury_data_prev = get_treasury_data(past_year)
        if treasury_data_prev:
            available_dates_prev = sorted(treasury_data_prev.keys(), reverse=True)
            for date in available_dates_prev:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                if date_obj <= req_date:
                    return date, treasury_data_prev[date]

    raise HTTPException(status_code=404, detail="No valid Treasury data found for the given date.")

# **🔹 Function to Find the Correct Term with Interpolation**
def get_lease_rate_for_term(treasury_data, term):
    term_years = term / 12  # Convert months to years
    available_terms = sorted([t for t in treasury_data.keys() if treasury_data[t] is not None])

    # **Exact match? Return rate**
    if term_years in available_terms:
        return treasury_data[term_years]

    # **Find two closest terms**
    shorter_term = max([t for t in available_terms if t < term_years], default=None)
    longer_term = min([t for t in available_terms if t > term_years], default=None)

    # **If only one bound is found, return the closest rate**
    if shorter_term is None:
        return treasury_data[longer_term]
    if longer_term is None:
        return treasury_data[shorter_term]

    # **Apply Interpolation Formula**
    shorter_rate = treasury_data[shorter_term]
    longer_rate = treasury_data[longer_term]
    interpolated_rate = (((longer_rate - shorter_rate) / (longer_term - shorter_term)) * (term_years - shorter_term)) + shorter_rate

    return interpolated_rate

# **🔹 API Endpoint**
@app.get("/calculate")
def get_lease_rate(date: str = Query(..., description="Lease date (YYYY-MM-DD)"), term: int = Query(..., description="Lease term in months")):
    recent_date, treasury_data = get_most_recent_date(date)
    lease_rate = get_lease_rate_for_term(treasury_data, term)

    return {
        "date": recent_date,
        "term": term,
        "lease_rate": lease_rate
    }
