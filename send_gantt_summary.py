import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# --- 1. Configuration ---
# ודא ששם הקובץ הזה תואם בדיוק לשם הקובץ בריפוזיטורי שלך
FILE_NAME = "GANTT TAI.xlsx" 

# --- 2. Date Configuration ---
TODAY = pd.to_datetime(datetime.today().date())
# TODAY = pd.to_datetime('2026-06-01') # For testing with future data

# --- 3. Helper Function to Format Tasks ---
def format_tasks_to_html(tasks_df, title):
    """Formats a DataFrame of tasks into an HTML table."""
    if tasks_df.empty:
        return f"<h2>{title}</h2><p>No tasks found for this period.</p>"
    
    html = f"<h2>{title}</h2>" # תיקון טעות קטנה: F-string חסר
    html += "<table>"
    html += "<tr><th>Task</th><th>Start Date</th><th>End Date</th></tr>"
    
    tasks_df = tasks_df.sort_values(by='Start')
    
    for _, row in tasks_df.iterrows():
        task_name = row['Task'] if pd.notna(row['Task']) else "Unnamed Task"
        html += f"<tr><td>{task_name}</td><td>{row['Start'].strftime('%Y-%m-%d')}</td><td>{row['Finish'].strftime('%Y-%m-%d')}</td></tr>"
        
    html += "</table>"
    return html

# --- 4. Data Loading and Processing ---
def create_task_report():
    """Loads data, filters tasks, and generates an HTML report."""
    try:
        # ---
        # !!! השינוי המרכזי כאן !!!
        # קוראים קובץ אקסל במקום CSV, ומשתמשים בספריית openpyxl
        df = pd.read_excel(FILE_NAME, header=8, engine='openpyxl')
        # ---
        
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = df.columns.str.strip()
        
        relevant_cols = ['Milestone description', 'Start', 'Days']
        if not all(col in df.columns for col in relevant_cols):
            print("Error: Missing essential columns.")
            return None
        
        df = df[relevant_cols].copy()
        df = df.dropna(subset=['Start', 'Days'])
        df = df.rename(columns={'Milestone description': 'Task'})
        
        df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
        df['Days'] = pd.to_numeric(df['Days'], errors='coerce')
        df = df.dropna(subset=['Start', 'Days'])
        
        df['Finish'] = df.apply(lambda row: row['Start'] + timedelta(days=max(0, row['Days'] - 1)), axis=1)

        # --- Task Filtering ---
        start_of_week = TODAY - pd.to_timedelta(TODAY.dayofweek, unit='d')
        end_of_week = start_of_week + pd.to_timedelta(6, unit='d')

        tasks_active_today = df[(df['Start'] <= TODAY) & (df['Finish'] >= TODAY)]
        tasks_ending_today = df[df['Finish'].dt.date == TODAY.date()]
        tasks_starting_today = df[df['Start'].dt.date == TODAY.date()]
        tasks_ending_this_week = df[(df['Finish'] >= start_of_week) & (df['Finish'] <= end_of_week)]
        tasks_starting_this_week = df[(df['Start'] >= start_of_week) & (df['Start'] <= end_of_week)]
        tasks_active_this_week = df[(df['Start'] <= end_of_week) & (df['Finish'] >= start_of_week)]

        # --- Generate HTML Report ---
        html_style = """
        <style>
            body { font-family: 'Arial', sans-serif; margin: 20px; background-color: #f9f9f9; color: #333; }
            h1 { color: #005A9C; border-bottom: 2px solid #005A9C; padding-bottom: 5px; }
            h2 { color: #333; margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 3px; }
            table { width: 90%; border-collapse: collapse; margin-top: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            th, td { padding: 10px 15px; border: 1px solid #ddd; text-align: left; }
            th { background-color: #f2f2f2; color: #333; font-weight: bold; }
            tr:nth-child(even) { background-color: #fcfcfc; }
            tr:hover { background-color: #f1f1f1; }
            p { font-style: italic; color: #777; }
        </style>
        """
        
        html_body = f"""
        <html>
        <head><meta charset="UTF-8">{html_style}</head>
        <body>
            <h1>Daily Task Summary: {TODAY.strftime('%A, %B %d, %Y')}</h1>
            {format_tasks_to_html(tasks_starting_today, "Tasks Starting Today")}
            {format_tasks_to_html(tasks_ending_today, "Tasks Ending Today")}
            {format_tasks_to_html(tasks_active_today, "All Tasks Active Today (Ongoing)")}
            
            <h1 style="margin-top: 40px;">Weekly Summary: {start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}</h1>
            {format_tasks_to_html(tasks_starting_this_week, "Tasks Starting This Week")}
            {format_tasks_to_html(tasks_ending_this_week, "Tasks Ending This Week")}
            {format_tasks_to_html(tasks_active_this_week, "All Tasks Active This Week (Ongoing)")}
        </body>
        </html>
        """
        return html_body
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        return None

# --- 5. Function to Send Email ---
def send_email(html_content):
    # --- קורא את הפרטים ממשתני הסביבה (Secrets) ---
    SENDER_EMAIL = os.environ.get('GMAIL_USER')
    SENDER_PASSWORD = os.environ.get('GMAIL_PASS')
    RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')
    
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("Error: Missing environment variables (GMAIL_USER, GMAIL_PASS, or RECIPIENT_EMAIL).")
        return

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Gantt Task Summary - {TODAY.strftime('%Y-%m-%d')}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    try:
        print(f"Connecting to {SMTP_SERVER}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        print("Login successful.")
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print(f"Email sent successfully to {RECIPIENT_EMAIL}!")
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

# --- 6. Main execution ---
if __name__ == "__main__":
    report_html = create_task_report()
    
    if report_html:
        print("Report generated successfully.")
        send_email(report_html)
    else:
        print("Failed to generate task report.")
