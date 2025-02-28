from fastapi import FastAPI, Query, HTTPException
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import json
import threading
import time

app = FastAPI()

# Define paths for cache & logs
CACHE_FILE = "treasury_data.json"

# Mapping Treasury terms to labels
TREASURY_LABELS = {
    "BC_1MONTH": "1 month", "BC_3MONTH": "3 months", "BC_6MONTH": "6 months",
    "BC_1YEAR": "1 year", "BC_2YEAR": "2 years", "BC_3YEAR": "3 years",
    "BC_5YEAR": "5 years", "BC_7YEAR": "7 years", "BC_10YEAR": "10 years",
    "BC_20YEAR": "20 years", "BC_30YEAR": "30 years"
}

# Fetch Treasury data
def fetch_treasury_data():
    treasury_data = {}
    current_year = datetime.today().year

    for year in range(current_year, current_year - 20, -1):
        url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"❌ Failed to fetch data for {year}")
            continue

        soup = BeautifulSoup(response.content, "xml")
        entries = soup.find_all("entry")

        for entry in entries:
            date_tag = entry.find("d:NEW_DATE")
            if date_tag:
                date_str = date_tag.text[:10]
                treasury_data[date_str] = {
                    key: (float(entry.find(f"d:{key}").text) if entry.find(f"d:{key}") and entry.find(f"d:{key}").text else None)
                    for key in TREASURY_LABELS.keys()
                }
    return treasury_data

# Load cached data
def load_cached_treasury_data():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as file:
                data = json.load(file)
                if data:
                    print(f"✅ Cached Treasury Data Loaded ({len(data)} records)")
                return data
        except json.JSONDecodeError:
            print("⚠️ Cache file corrupted. Fetching fresh data...")
            return None
    return {}

# Update Treasury cache
def update_treasury_cache():
    while True:
        try:
            print("🔄 Updating Treasury Data...")
            cached_data = load_cached_treasury_data() or {}
            new_data = fetch_treasury_data()

            if new_data:
                cached_data.update(new_data)
                with open(CACHE_FILE, "w") as file:
                    json.dump(cached_data, file, indent=4)
                print(f"✅ Treasury Data Updated: {datetime.today().strftime('%Y-%m-%d')}")
            else:
                print("❌ Failed to update Treasury Data")

        except Exception as e:
            print(f"⚠️ Error in cache update: {e}")

        time.sleep(3600)  # Update every hour

# Start background caching
def start_cache_updater():
    thread = threading.Thread(target=update_treasury_cache, daemon=True)
    thread.start()

# Get most recent Treasury data
def get_most_recent_date(requested_date: str):
    treasury_data = load_cached_treasury_data()

    if not treasury_data:
        print("⚠️ No new data fetched. Using last known treasury rates.")
        return max(treasury_data.keys()), treasury_data[max(treasury_data.keys())]

    req_date = datetime.strptime(requested_date, "%Y-%m-%d")
    available_dates = sorted(treasury_data.keys(), reverse=True)

    for date in available_dates:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        if date_obj <= req_date:
            return date, treasury_data[date]

    return max(treasury_data.keys()), treasury_data[max(treasury_data.keys())]

# Get lease rate based on term
def get_lease_rate_for_term(treasury_data, term):
    term_mapping = {
        1: "BC_1MONTH", 3: "BC_3MONTH", 6: "BC_6MONTH",
        12: "BC_1YEAR", 24: "BC_2YEAR", 36: "BC_3YEAR",
        60: "BC_5YEAR", 84: "BC_7YEAR", 120: "BC_10YEAR",
        240: "BC_20YEAR", 360: "BC_30YEAR"
    }

    available_terms = {key: value for key, value in treasury_data.items() if value is not None}

    if term in term_mapping and term_mapping[term] in available_terms:
        return available_terms[term_mapping[term]], f"Exact match for {TREASURY_LABELS[term_mapping[term]]}"

    shorter_term = max([t for t in term_mapping.keys() if t < term and term_mapping[t] in available_terms], default=None)
    longer_term = min([t for t in term_mapping.keys() if t > term and term_mapping[t] 
