#!/usr/bin/env python3
"""
job_scraper.py (Template)
Multi-platform job aggregator using python-jobspy and RSS feeds.
Scrapes Indeed, LinkedIn, ZipRecruiter, and Glassdoor, and outputs
new job discoveries to tracking.csv as 'Status: Unscreened'.
"""

import csv
import os
import sys
from datetime import datetime
import pandas as pd

try:
    from jobspy import scrape_jobs
except ImportError:
    print("Error: python-jobspy not installed. Run: pip install python-jobspy")
    sys.exit(1)

# --- CONFIGURATION (Customize for your specific search) ---
CSV_FILE = "tracking.csv"

# Primary search queries (e.g. your target job titles)
# Phase 1: Moonlighting & Consulting + Phase 2: Senior Leadership Roles
SEARCH_QUERIES = [
    # Primary Target Roles (Current Level - Senior)
    "Senior PACS Administrator",
    "Senior Imaging Systems Analyst",
    "Enterprise Imaging Engineer",
    "Health IT Integration Engineer",
    "Implementation Engineer",
    
    # Next-Level Roles (Phase 2 - Senior Leadership)
    "Principal Imaging Systems Engineer",
    "Principal PACS Engineer",
    "IT Infrastructure Lead Healthcare",
    "Enterprise Imaging Program Manager",
    "Technical Product Manager Healthcare",
    "Senior Solutions Architect Healthcare",
    
    # Vendor-Specific Searches
    "Mach7 VNA",
    "Hyland Acuo VNA",
    "Intelerad IntelePACS",
    "Sectra IDS7",
    "Nuance PowerScribe",
    "Epic Radiant",
    
    # Healthcare IT Infrastructure & Automation
    "Healthcare Infrastructure Consultant",
    "Enterprise Imaging Infrastructure",
    "Health IT Systems Engineer"
]

# Supported job boards
SITE_NAMES = ["indeed", "linkedin", "zip_recruiter", "glassdoor"]

# Target locations to cycle through
SEARCH_LOCATIONS = [
    "Remote, United States",
    "United States"
]

# Time window in hours (e.g., 72 hours = 3 days; 168 hours = 7 days)
HOURS_LOOKBACK = 168

# Basic negative keywords to skip early in titles
TITLE_BLACKLIST = [
    "intern", "internship", "volunteer", "co-op", "student"
]

def get_existing_urls():
    """Reads tracking.csv to prevent inserting duplicate links."""
    existing = set()
    if not os.path.exists(CSV_FILE):
        return existing
    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "Link" in row and row["Link"].strip():
                existing.add(row["Link"].strip())
    return existing

def append_jobs_to_csv(new_jobs):
    """Appends discovered jobs to tracking.csv with 'Unscreened' status."""
    file_exists = os.path.isfile(CSV_FILE)
    fieldnames = ["Company", "Role", "Link", "Date Posted", "Date Applied", "Status", "Notes"]
    
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for job in new_jobs:
            writer.writerow({
                "Company": job.get("company", "Unknown Company"),
                "Role": job.get("title", "Unknown Role"),
                "Link": job.get("url", ""),
                "Date Posted": job.get("date_posted", datetime.now().strftime("%Y-%m-%d")),
                "Date Applied": "",
                "Status": "Unscreened",
                "Notes": f"Found on {job.get('site', 'JobSpy')}"
            })

def main():
    existing_urls = get_existing_urls()
    print(f"[{datetime.now()}] Starting scrape across {SITE_NAMES}...")
    collected_jobs = []

    for loc in SEARCH_LOCATIONS:
        for query in SEARCH_QUERIES:
            print(f"  -> Scraping: '{query}' in '{loc}'...")
            try:
                jobs_df = scrape_jobs(
                    site_name=SITE_NAMES,
                    search_term=query,
                    location=loc,
                    results_wanted=30,
                    hours_old=HOURS_LOOKBACK,
                    country_indeed="USA"
                )
                if jobs_df is None or jobs_df.empty:
                    continue

                for _, row in jobs_df.iterrows():
                    url = str(row.get("job_url", "")).strip()
                    title = str(row.get("title", "Unknown")).strip()
                    company = str(row.get("company", "Unknown")).strip()
                    site = str(row.get("site", "Web")).strip()

                    if not url or url in existing_urls:
                        continue

                    # Basic title check
                    if any(bad in title.lower() for bad in TITLE_BLACKLIST):
                        continue

                    date_val = row.get("date_posted")
                    date_str = str(date_val.date()) if pd.notnull(date_val) and hasattr(date_val, "date") else str(date_val) if pd.notnull(date_val) else datetime.now().strftime("%Y-%m-%d")

                    collected_jobs.append({
                        "company": company,
                        "title": title,
                        "url": url,
                        "site": site,
                        "date_posted": date_str
                    })
                    existing_urls.add(url)
            except Exception as e:
                print(f"Warning: Failed to scrape '{query}' in '{loc}': {e}")

    if collected_jobs:
        print(f"Found {len(collected_jobs)} new listings. Appending to {CSV_FILE}...")
        append_jobs_to_csv(collected_jobs)
    else:
        print("No new unique listings found.")
    print(f"[{datetime.now()}] Scraping finished successfully.")

if __name__ == "__main__":
    main()
