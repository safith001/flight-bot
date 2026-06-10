from telegram import Bot
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import time
import asyncio
from anthropic import Anthropic

load_dotenv()

# API Keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Timezone for Malaysia
MYT = timezone(timedelta(hours=8))

ROUTES = [
    {"from": "KUL", "to": "CMB", "name": "KL to CMB"},
    {"from": "CMB", "to": "KUL", "name": "CMB to KL"},
    {"from": "CMB", "to": "MAA", "name": "CMB to Chennai"},
    {"from": "MAA", "to": "CMB", "name": "Chennai to CMB"},
    {"from": "CMB", "to": "DXB", "name": "CMB to Dubai"},
    {"from": "DXB", "to": "CMB", "name": "Dubai to CMB"},
]

BUDGETS = {
    "KL to CMB": 700,
    "CMB to KL": 700,
    "CMB to Chennai": 700,
    "Chennai to CMB": 700,
    "CMB to Dubai": 700,
    "Dubai to CMB": 700,
}

# Store daily prices for summaries
daily_prices = {}

# ============= API FUNCTIONS =============

def get_price_fastflights(from_code, to_code):
    """Get price using fast-flights (unlimited, free, no API key)"""
    try:
        from fast_flights import FlightData, Passengers, get_flights
        
        result = get_flights(
            flight_data=[
                FlightData(
                    date=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                    from_airport=from_code,
                    to_airport=to_code
                )
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1)
        )
        
        if result and result.flights:
            first_flight = result.flights[0]
            price_str = first_flight.price
            
            if isinstance(price_str, str) and 'MYR' in price_str:
                price_num = ''.join(c for c in price_str if c.isdigit())
                if price_num:
                    return int(price_num)
        
        return None
        
    except Exception:
        return None

def should_send_6hour_update():
    """True only at 00:xx, 06:xx, 12:xx, 18:xx MYT"""
    now = datetime.now(MYT)
    return now.hour % 6 == 0

def should_send_daily_summary():
    """True at 10 PM (22:00) MYT"""
    now = datetime.now(MYT)
    return now.hour == 22

def send_telegram_message(message):
    """Send message via Telegram Bot API"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
        print("[OK] Message sent to Telegram")
    except Exception as e:
        print(f"[ERROR] Telegram: {str(e)}")

def get_claude_summary(all_prices):
    """Get AI summary of flight prices using Claude"""
    try:
        client = Anthropic()
        
        # Format prices for Claude
        price_text = "\n".join([
            f"{route}: RM{price}" 
            for route, price in all_prices.items() 
            if price is not None
        ])
        
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze these flight prices and provide a brief 2-3 sentence summary with the best booking opportunity:

{price_text}

Budget: RM700 per route

Keep it concise and actionable."""
                }
            ]
        )
        
        return message.content[0].text
        
    except Exception as e:
        print(f"[ERROR] Claude: {str(e)}")
        return "Could not generate summary"

def check_all_routes():
    """Check all routes and send alerts"""
    global daily_prices
    
    check_time = datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")
    
    status_message = f"Bot is looking for prices (22 min loop) - {check_time}\n\n"
    alert_message = ""
    has_alerts = False
    force_send = should_send_6hour_update()
    send_summary = should_send_daily_summary()
    
    print(f"\n[{check_time}] Checking all routes...\n")
    
    all_prices = {}
    
    for route in ROUTES:
        print(f"  Fetching {route['name']}...", end=" ")
        current_price = get_price_fastflights(route["from"], route["to"])
        all_prices[route["name"]] = current_price
        daily_prices[route["name"]] = current_price
        budget = BUDGETS[route["name"]]
        
        if current_price is None:
            print("No price found")
        else:
            if current_price < budget:
                alert_message += f"RED {route['name']:<20} RM{current_price} BOOK NOW!\n"
                has_alerts = True
                print(f"RM{current_price} (RED)")
            elif current_price < budget * 1.10:
                alert_message += f"YELLOW {route['name']:<20} RM{current_price} dropped!\n"
                has_alerts = True
                print(f"RM{current_price} (YELLOW)")
            else:
                print(f"RM{current_price} (SILENT)")
        
        time.sleep(0.5)
    
    # Build final message
    final_message = status_message
    
    if has_alerts:
        final_message += "PRICE CHANGES:\n" + alert_message
    else:
        final_message += "No price changes detected"
    
    # 6-hour full update
    if force_send:
        final_message += "\n\n6-HOUR FULL UPDATE:\n"
        for route_name, price in all_prices.items():
            if price:
                final_message += f"{route_name:<20} RM{price}\n"
    
    # Daily summary at 10 PM
    if send_summary:
        print("\n[SUMMARY] Generating Claude AI summary...")
        summary = get_claude_summary(all_prices)
        final_message += f"\n\nDAILY SUMMARY (Claude AI):\n{summary}"
    
    send_telegram_message(final_message)
    return final_message

if __name__ == "__main__":
    print("Flight Price Bot - Started (fast-flights + Claude AI)\n")
    check_all_routes()