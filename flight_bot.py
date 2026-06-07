import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
from datetime import datetime, timedelta
import json
import time

# Your credentials (keep these private)
CLAUDE_API_KEY = "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"
SERPAPI_KEY = "756a367a6cc667747c3a1a6b32e8f90f5f789ece49578a4cfbd83454a41d55bc"
TELEGRAM_TOKEN = "8683064180:AAGGcVoreJGdC6eobJfhFR7BfS1uDE8bSgE"
TELEGRAM_CHAT_ID = 6858857261  # just the number
GOOGLE_SHEET_NAME = "Flight Price Tracker"

# Your 10 routes
ROUTES = [
    {"from": "KUL", "to": "CMB", "name": "KL to CMB"},
    {"from": "CMB", "to": "KUL", "name": "CMB to KL"},
    {"from": "CMB", "to": "MSR", "name": "CMB to Belarus"},
    {"from": "MSR", "to": "CMB", "name": "Belarus to CMB"},
    {"from": "CMB", "to": "MAA", "name": "CMB to Chennai"},
    {"from": "MAA", "to": "CMB", "name": "Chennai to CMB"},
    {"from": "CMB", "to": "BER", "name": "CMB to Berlin"},
    {"from": "BER", "to": "CMB", "name": "Berlin to CMB"},
    {"from": "CMB", "to": "DXB", "name": "CMB to Dubai"},
    {"from": "DXB", "to": "CMB", "name": "Dubai to CMB"},
]

# Default budgets per route (update with Sunday form)
BUDGETS = {
    "KL to CMB": 700,
    "CMB to KL": 700,
    "CMB to Belarus": 700,
    "Belarus to CMB": 700,
    "CMB to Chennai": 700,
    "Chennai to CMB": 700,
    "CMB to Berlin": 700,
    "Berlin to CMB": 700,
    "CMB to Dubai": 700,
    "Dubai to CMB": 700,
}

def get_serpapi_price(from_code, to_code, route_name):
    """Fetch price from SerpAPI"""
    try:
        departure_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://api.serpapi.com/search"
        params = {
            "engine": "google_flights",
            "departure_id": from_code,
            "arrival_id": to_code,
            "outbound_date": departure_date,
            "currency": "MYR",
            "api_key": SERPAPI_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "best_flights" in data and len(data["best_flights"]) > 0:
            price = data["best_flights"][0]["price"]
            return int(price)
        
        return None
        
    except Exception as e:
        print(f"Error fetching {route_name}: {str(e)}")
        return None

def send_telegram_message(message):
    """Send message to Telegram"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"Message sent to Telegram")
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")

def save_to_sheets(prices):
    """Save prices to Google Sheets"""
    try:
        scope = ["https://spreadsheets.google.com/auth/spreadsheets",
                 "https://www.googleapis.com/auth/drive"]
        
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        sheet = client.open(GOOGLE_SHEET_NAME)
        today = datetime.now().strftime("%Y-%m")
        
        try:
            worksheet = sheet.worksheet(today)
        except:
            worksheet = sheet.add_worksheet(title=today, rows=1000, cols=5)
            worksheet.append_row(["Timestamp", "Route", "Price (RM)", "Last Price (RM)", "Status"])
        
        for price_data in prices:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            row = [
                timestamp,
                price_data["route"],
                price_data["current_price"],
                price_data["last_price"],
                price_data["status"]
            ]
            worksheet.append_row(row)
        
        print("Data saved to Google Sheets")
        
    except Exception as e:
        print(f"Error saving to sheets: {str(e)}")

def check_all_routes():
    """Check all routes and return prices with alerts"""
    results = []
    alert_message = "Price Updates:\n\n"
    has_alerts = False
    
    print("Checking all routes...\n")
    
    for route in ROUTES:
        current_price = get_serpapi_price(route["from"], route["to"], route["name"])
        budget = BUDGETS[route["name"]]
        
        # For now, assume last price same as current (first run)
        # Later this will come from Google Sheets
        last_price = current_price
        
        if current_price is None:
            status = "N/A"
            print(f"{route['name']:<20} Price not found")
        else:
            # Determine status
            if current_price < budget:
                status = "RED"
                alert_message += f"RED {route['name']:<20} RM{current_price} BOOK NOW!\n"
                has_alerts = True
            elif current_price < budget * 1.10 and current_price < last_price:
                status = "YELLOW"
                alert_message += f"YELLOW {route['name']:<20} RM{current_price} dropped!\n"
                has_alerts = True
            else:
                status = "SILENT"
            
            print(f"{route['name']:<20} RM{current_price} ({status})")
        
        results.append({
            "route": route["name"],
            "current_price": current_price if current_price else "N/A",
            "last_price": last_price if last_price else "N/A",
            "status": status
        })
        
        time.sleep(1)  # Be nice to API
    
    # Save to sheets
    save_to_sheets(results)
    
    # Send alert if needed
    if has_alerts:
        send_telegram_message(alert_message)
    
    return results

if __name__ == "__main__":
    print("Flight Price Bot - Started\n")
    prices = check_all_routes()
    print("\nCheck complete!")