import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
import re
import json
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

TARGET_LOCATIONS = {
    "Calgary",
    "Remote in Canada"
}

URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md"

response = requests.get(URL)
raw_md = response.text

response.raise_for_status()

load_dotenv()
app_password = os.getenv("GMAIL_APP_PASSWORD")
gmail_address = os.getenv("GMAIL_ADDRESS")

if not app_password:
    raise ValueError("GMAIL_APP_PASSWORD is not set in the environment variables.")

if not gmail_address:
    raise ValueError("GMAIL_ADDRESS is not set in the environment variables.")

soup = BeautifulSoup(raw_md, "html.parser")
tables = soup.find_all("table")[:3]

jobs = []
current_job_ids = set()

for table in tables:
    rows = table.find_all("tr")[1:]

    prev_company = None

    for row in rows:
        cells = row.find_all("td") 

        company = cells[0].get_text(strip=True)
        role = cells[1].get_text(strip=True)
        location = cells[2].get_text(strip=True)
        application_url = cells[3].find("a")["href"] if cells[3].find("a") else None 
        age = cells[4].get_text(strip=True)

        age = re.sub(r"[^0-9]", "", age)

        date_added = date.today() - timedelta(days=int(age))


        if "↳" in company:
            company = prev_company
        else:
            prev_company = company

        if any (loc in location for loc in TARGET_LOCATIONS):
            jobs.append(
                {"job_id": application_url, "company": company, "role": role, "location": location, "date_added": str(date_added)}
            )
            current_job_ids.add(application_url)

with open("seen_jobs.json", "r") as f:
    seen_jobs = json.load(f)
    seen_jobs = set(seen_jobs)

new_job_ids = current_job_ids - seen_jobs
new_jobs = [job for job in jobs if job["job_id"] in new_job_ids]

if new_jobs:
    print(f"Found {len(new_jobs)} new internships.")
    
    email_message = EmailMessage()
    email_message["Subject"] = "New Internship Opportunities"
    email_message["From"] = "Simplify Internship Monitor <" + gmail_address + ">"
    email_message["To"] = gmail_address

    text_body = """
New internships found:

| Company | Role | Location | Date Added | Apply |
"""

    html_body = """
<html>
    <body style="font-family: Arial, sans-serif;">
        <h2>New internships found!</h2>

        <table style="border-collapse: collapse; width: 100%;">
            <tr>
                <th style="padding: 8px; border-bottom: 1px solid #ccc; background-color: #f2f2f2; text-align: left;">Company</th>
                <th style="padding: 8px; border-bottom: 1px solid #ccc; background-color: #f2f2f2; text-align: left; min-width: 200px;">Role</th>
                <th style="padding: 8px; border-bottom: 1px solid #ccc; background-color: #f2f2f2; text-align: left;">Location</th>
                <th style="padding: 8px; border-bottom: 1px solid #ccc; background-color: #f2f2f2; text-align: left;">Date Added</th>
                <th style="padding: 8px; border-bottom: 1px solid #ccc; background-color: #f2f2f2; text-align: left;">Apply</th>
            </tr>
"""

    for job in new_jobs:
        text_body += (
            f"| {job['company']} | {job['role']} | "
            f"{job['location']} | {job['date_added']} | {job['job_id']} |\n"
        )

        html_body += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ccc; vertical-align: top;">
                    {job['company']}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #ccc; vertical-align: top; min-width: 200px;">
                    {job['role']}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #ccc; vertical-align: top;">
                    {job['location']}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #ccc; vertical-align: top;">
                    {job['date_added']}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #ccc; vertical-align: top;">
                    <a href="{job['job_id']}"
                       style="display: inline-block; padding: 6px 12px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 4px;">
                        Apply
                    </a>
                </td>
            </tr>
"""

    html_body += """
        </table>
    </body>
</html>
"""

    email_message.set_content(text_body)
    email_message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_address, app_password)
        smtp.send_message(email_message)

    seen_jobs = seen_jobs.union(new_job_ids)

    with open("seen_jobs.json", "w") as f:
        json.dump(list(seen_jobs), f)