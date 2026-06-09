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

def should_send_6hour_update():
    """True only at 00:xx, 06:xx, 12:xx, 18:xx — no file state needed, works in CI"""
    from datetime import timezone, timedelta
    myt = timezone(timedelta(hours=8))
    now = datetime.now(myt)
    return now.hour % 6 == 0

def send_telegram_message(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
        print("Message sent to Telegram")
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")

def check_all_routes():
    from datetime import timezone, timedelta
    myt = timezone(timedelta(hours=8))
    check_time = datetime.now(myt).strftime("%Y-%m-%d %H:%M:%S")
    
    # Always send: Bot is checking
    status_message = f"Bot is looking for prices (22 min loop) - {check_time}\n\n"
    alert_message = ""
    has_alerts = False
    force_send = should_send_6hour_update()
    
    print(f"[{check_time}] Checking all routes...\n")
    
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
                print(f"{route['name']:<20} RM{current_price} (SILENT)")
        
        time.sleep(1)
    
    # Always send status message
    final_message = status_message
    
    if has_alerts:
        # Send price changes
        final_message += "PRICE CHANGES:\n" + alert_message
    else:
        # Send no changes message
        final_message += "No price changes detected"
    
    # Send 6-hour full update if needed
    if force_send:
        # Send all routes with full details
        final_message += "\n\n6-HOUR FULL UPDATE:\n"
        for route in ROUTES:
            current_price = get_serpapi_price(route["from"], route["to"], route["name"])
            if current_price:
                final_message += f"{route['name']:<20} RM{current_price}\n"
    # Always send message every 22 minutes
    send_telegram_message(final_message)
    
    return final_message


    
if __name__ == "__main__":
    print("Flight Price Bot - Started\n")
    check_all_routes()   # run once, then exit

