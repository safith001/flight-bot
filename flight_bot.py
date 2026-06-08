from serpapi import GoogleSearch
from telegram import Bot
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import time
import asyncio

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

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
    try:
        params = {
            "api_key": SERPAPI_KEY,
            "engine": "google_flights",
            "departure_id": from_code,
            "arrival_id": to_code,
            "outbound_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "currency": "MYR",
            "type": "2",
            "deep_search": "true"
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if results.get("best_flights") and len(results["best_flights"]) > 0:
            price = results["best_flights"][0]["price"]
            return int(price)
        
        return None
        
    except Exception as e:
        print(f"Error fetching {route_name}: {str(e)}")
        return None

def get_last_check_time():
    """Get the last time we sent a 6-hour update"""
    try:
        with open('last_6hour_check.txt', 'r') as f:
            return datetime.fromisoformat(f.read())
    except:
        return None

def save_last_check_time():
    """Save current time as last 6-hour update"""
    with open('last_6hour_check.txt', 'w') as f:
        f.write(datetime.now().isoformat())

def should_send_6hour_update():
    """Check if 6 hours have passed since last update"""
    last_check = get_last_check_time()
    if last_check is None:
        return True
    return (datetime.now() - last_check).total_seconds() >= 21600  # 6 hours = 21600 seconds

def send_telegram_message(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
        print("Message sent to Telegram")
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")

def check_all_routes():
    alert_message = "Price Updates:\n\n"
    has_alerts = False
    force_send = should_send_6hour_update()
    
    print("Checking all routes...\n")
    
    for route in ROUTES:
        current_price = get_serpapi_price(route["from"], route["to"], route["name"])
        budget = BUDGETS[route["name"]]
        
        if current_price is None:
            print(f"{route['name']:<20} Price not found")
        else:
            if current_price < budget:
                alert_message += f"RED {route['name']:<20} RM{current_price} BOOK NOW!\n"
                has_alerts = True
                print(f"{route['name']:<20} RM{current_price} (RED)")
            elif current_price < budget * 1.10:
                alert_message += f"YELLOW {route['name']:<20} RM{current_price} dropped!\n"
                has_alerts = True
                print(f"{route['name']:<20} RM{current_price} (YELLOW)")
            else:
                alert_message += f"SILENT {route['name']:<20} RM{current_price}\n"
                print(f"{route['name']:<20} RM{current_price} (SILENT)")
        
        time.sleep(1)
    
    # Send if: price dropped OR 6 hours passed
    if has_alerts or force_send:
        send_telegram_message(alert_message)
        if force_send:
            save_last_check_time()
    else:
        print("No alerts to send")
    
    return alert_message
    
    if has_alerts:
        send_telegram_message(alert_message)
    else:
        print("No alerts to send")
    
    return alert_message

if __name__ == "__main__":
    print("Flight Price Bot - Started\n")
    check_all_routes()