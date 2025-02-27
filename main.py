from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import os
import json
import threading
import time

app = FastAPI()

# Define paths for cache & logs
CACHE_FILE = "treasury_data.json"
AUDIT_LOG_FILE = "audit_log.csv"

# Mapping Treasury terms to user-friendly labels (for Rate Calculation Formula only)
TREASURY_LABELS = {
    "BC_1MONTH": "1 month", "BC_3MONTH": "3 months", "BC_6MONTH": "6 months",
    "BC_1YEAR": "1 year", "BC_2YEAR": "2 years", "BC_3YEAR": "3 years",
    "BC_5YEAR": "5 years", "BC_7YEAR": "7 years", "BC_10YEAR": "10 years",
    "BC_20YEAR": "20 years", "BC_30YEAR": "30 years"
}

# Treasury API Fetch Function (Now Fetching Multiple Years)
def fetch_treasury_data():
    treasury_data = {}

    # Fetch last 10 years of data
    current_year = datetime.today().year
    for year in range(current_year, current_year - 20, -1):  # Last 10 years
        url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch data for {year}")
            continue  # Skip to next year if this fails

        soup = BeautifulSoup(response.content, "xml")
        entries = soup.find_all("entry")

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

                # Convert values to float
                for key, value in treasury_data[date_str].items():
                    if value and value.text:
                        treasury_data[date_str][key] = float(value.text)
                    else:
                        treasury_data[date_str][key] = None

    return treasury_data

# **🔹 Function to Load Cached Data**
def load_cached_treasury_data():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            return json.load(file)
    return None

# Function to Update Cache (Runs Every Hour)
def update_treasury_cache():
    while True:
        # Load existing data if it exists
        cached_data = load_cached_treasury_data() or {}

        # Fetch all years (not just the latest year)
        new_data = fetch_treasury_data()

        if new_data:
            # Merge new data with old cached data
            cached_data.update(new_data)

            # Save updated data back to cache
            with open(CACHE_FILE, "w") as file:
                json.dump(cached_data, file)
            print(f"✅ Treasury Data Updated: {datetime.today().strftime('%Y-%m-%d')}")

        else:
            print("❌ Failed to update Treasury Data")

        time.sleep(3600)  # **Wait 1 hour before next update**

# **🔹 Start the Background Caching Task**
def start_cache_updater():
    thread = threading.Thread(target=update_treasury_cache, daemon=True)
    thread.start()

# **🔹 Function to Get Most Recent Treasury Data**
def get_most_recent_date(requested_date: str):
    treasury_data = load_cached_treasury_data()

    if not treasury_data:
        raise HTTPException(status_code=404, detail="No cached Treasury data found. Try again later.")

    req_date = datetime.strptime(requested_date, "%Y-%m-%d")
    available_dates = sorted(treasury_data.keys(), reverse=True)

    for date in available_dates:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        if date_obj <= req_date:
            return date, treasury_data[date]

    raise HTTPException(status_code=404, detail="No valid Treasury data found for the given date.")

# **🔹 Function to Get Lease Rate**
def get_lease_rate_for_term(treasury_data, term):
    term_mapping = {
        1: "BC_1MONTH", 3: "BC_3MONTH", 6: "BC_6MONTH",
        12: "BC_1YEAR", 24: "BC_2YEAR", 36: "BC_3YEAR",
        60: "BC_5YEAR", 84: "BC_7YEAR", 120: "BC_10YEAR",
        240: "BC_20YEAR", 360: "BC_30YEAR"
    }

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
        return available_terms[term_mapping[longer_term]], f"Closest match found: {friendly_label}"Ma
    if longer_term is None:
        friendly_label = TREASURY_LABELS.get(term_mapping[shorter_term], term_mapping[shorter_term])
        return available_terms[term_mapping[shorter_term]], f"Closest match found: {friendly_label}"

    # **Apply Interpolation**
    shorter_rate = available_terms[term_mapping[shorter_term]]
    longer_rate = available_terms[term_mapping[longer_term]]
    interpolated_rate = (((longer_rate - shorter_rate) / (longer_term - shorter_term)) * (term - shorter_term)) + shorter_rate

    return interpolated_rate, "Interpolated Rate"

# **🔹 API Endpoint**
@app.get("/calculate")
def get_lease_rate(date: str = Query(..., description="Lease date (YYYY-MM-DD)"), term: int = Query(..., description="Lease term in months")):
    recent_date, treasury_data = get_most_recent_date(date)
    lease_rate, calculation = get_lease_rate_for_term(treasury_data, term)

    return {
        "date": recent_date,
        "term": term,
        "lease_rate": lease_rate,
        "calculation": calculation
    }

# **🔹 Start Cache Updating Task on Startup**
start_cache_updater()
