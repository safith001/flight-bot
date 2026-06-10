from telegram import Bot
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import time
import asyncio
from anthropic import Anthropic
import json
import subprocess

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
    "KL to CMB": 800,
    "CMB to KL": 800,
    "CMB to Chennai": 600,
    "Chennai to CMB": 600,
    "CMB to Dubai": 900,
    "Dubai to CMB": 900,
}

# Store in repo (will be committed to GitHub)
HISTORY_FILE = "daily_prices.json"

# ============= API FUNCTIONS =============

def build_google_flights_url(from_code, to_code, departure_date):
    """Build Google Flights URL"""
    date_obj = datetime.strptime(departure_date, "%Y-%m-%d")
    date_formatted = date_obj.strftime("%m/%d/%Y")
    return f"https://www.google.com/flights?flt={from_code}{date_formatted}{to_code}&curr=MYR"

def get_flight_details(from_code, to_code, route_name):
    """Get flight details: price, airline, duration, stops, date"""
    try:
        from fast_flights import FlightData, Passengers, get_flights
        
        departure_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        result = get_flights(
            flight_data=[
                FlightData(
                    date=departure_date,
                    from_airport=from_code,
                    to_airport=to_code
                )
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1)
        )
        
        if result and result.flights:
            flight = result.flights[0]
            
            # Extract price
            price = None
            if isinstance(flight.price, str) and 'MYR' in flight.price:
                price_num = ''.join(c for c in flight.price if c.isdigit())
                if price_num:
                    price = int(price_num)
            
            airline = flight.name if flight.name else "Unknown"
            duration = flight.duration if flight.duration else "Unknown"
            stops = flight.stops if flight.stops is not None else "Unknown"
            
            date_obj = datetime.strptime(departure_date, "%Y-%m-%d")
            date_display = date_obj.strftime("%d %b %Y")
            
            booking_link = build_google_flights_url(from_code, to_code, departure_date)
            
            return {
                "price": price,
                "airline": airline,
                "duration": duration,
                "stops": stops,
                "date": date_display,
                "link": booking_link
            }
        
        return None
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def format_fare_options(airline, price):
    """Generate fare tier options based on airline and price"""
    options = ""
    
    if airline.lower() in ["batik air", "malindo air", "flydubai"]:
        if price and price < 800:
            value_price = int(price * 1.09)
            premium_price = int(price * 1.50)
            options = f"📦 Value: RM{value_price} (20kg checked + 7kg cabin)\n"
            options += f"📦 Premium: RM{premium_price} (25kg checked + 7kg cabin)"
    elif airline.lower() in ["indigo"]:
        if price and price < 700:
            value_price = int(price * 1.15)
            premium_price = int(price * 1.70)
            options = f"📦 Value: RM{value_price} (15kg checked + 6kg cabin)\n"
            options += f"📦 Premium: RM{premium_price} (25kg checked + 7kg cabin)"
    
    return options

def save_daily_prices(all_flights):
    """Save today's prices to GitHub history file"""
    today = datetime.now(MYT).strftime("%Y-%m-%d")
    
    try:
        # Load existing history from GitHub
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        else:
            history = {}
        
        # Update today's data
        if today not in history:
            history[today] = {}
        
        for route, flight in all_flights.items():
            if flight and flight['price']:
                if route not in history[today]:
                    history[today][route] = {
                        "prices": [],
                        "airline": flight['airline'],
                        "duration": flight['duration']
                    }
                
                # Add price with timestamp
                current_time = datetime.now(MYT).strftime("%H:%M")
                history[today][route]["prices"].append({
                    "time": current_time,
                    "price": flight['price']
                })
        
        # Save back to file (will be committed to GitHub)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"[HISTORY] Saved prices to {HISTORY_FILE}")
    
    except Exception as e:
        print(f"[ERROR] History save failed: {str(e)}")

def commit_history_to_github():
    """Commit updated history to GitHub"""
    try:
        subprocess.run(['git', 'add', HISTORY_FILE], check=False)
        subprocess.run(['git', 'commit', '-m', f'Update price history - {datetime.now(MYT).strftime("%Y-%m-%d %H:%M")}'], check=False)
        subprocess.run(['git', 'push'], check=False)
        print("[GIT] History committed to GitHub")
    except Exception as e:
        print(f"[ERROR] Git commit failed: {str(e)}")

def get_today_price_history():
    """Get all prices collected today from GitHub history"""
    today = datetime.now(MYT).strftime("%Y-%m-%d")
    
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
            
            if today in history:
                return history[today]
    except Exception as e:
        print(f"[ERROR] History load failed: {str(e)}")
    
    return {}

def get_claude_daily_summary(price_history):
    """Use Claude to analyze full day's price history"""
    try:
        if not CLAUDE_API_KEY or not price_history:
            return None
        
        client = Anthropic(api_key=CLAUDE_API_KEY)
        
        # Format price history for Claude
        history_text = ""
        for route, data in price_history.items():
            if "prices" in data and data["prices"]:
                prices = [p["price"] for p in data["prices"]]
                min_price = min(prices)
                max_price = max(prices)
                latest_price = prices[-1]
                first_price = prices[0]
                trend = "📈 UP" if latest_price > first_price else "📉 DOWN"
                change = abs(latest_price - first_price)
                
                history_text += f"\n{route}:\n"
                history_text += f"  Morning: RM{first_price} → Evening: RM{latest_price} ({change}RM change) {trend}\n"
                history_text += f"  Low: RM{min_price} | High: RM{max_price}\n"
                history_text += f"  Checks: {len(prices)} times today\n"
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=350,
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze today's COMPLETE flight price history (multiple checks throughout day) and give a smart summary:

{history_text}

Budget: RM700 per route

Provide:
1. Best deals (which routes, which times)
2. Price trends (which went up/down, by how much)
3. Smart booking advice (book NOW or WAIT, and why)
4. Pattern insights (early day vs late day pricing)

Be specific with numbers and times."""
                }
            ]
        )
        
        return message.content[0].text
        
    except Exception as e:
        print(f"[ERROR] Claude: {str(e)}")
        return None

def should_send_2hour_update():
    """True only at 00:xx, 02:xx, 04:xx, 06:xx, 08:xx, 10:xx, 12:xx, 14:xx, 16:xx, 18:xx, 20:xx, 22:xx MYT"""
    now = datetime.now(MYT)
    return now.hour % 2 == 0

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

def check_all_routes():
    """Check all routes and send alerts"""
    check_time = datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n[{check_time}] Checking all routes...\n")
    
    all_flights = {}
    alert_sections = []
    force_send = should_send_2hour_update()
    send_summary = should_send_daily_summary()
    
    for i, route in enumerate(ROUTES, 1):
        print(f"  {i}. Fetching {route['name']}...", end=" ")
        flight = get_flight_details(route["from"], route["to"], route["name"])
        
        if flight is None:
            print("No price found")
            continue
        
        all_flights[route["name"]] = flight
        price = flight["price"]
        budget = BUDGETS[route["name"]]
        
        if price is None:
            print("No price found")
        else:
            if price < budget:
                status = "🔴 RED - BOOK NOW!"
                print(f"RM{price} (RED)")
            elif price < budget * 1.10:
                status = "🟡 YELLOW - Price dropped!"
                print(f"RM{price} (YELLOW)")
            else:
                status = "⚫ SILENT"
                print(f"RM{price} (SILENT)")
            
            # Build detailed section for this route
            if price < budget * 1.10:
                section = f"\n{i}. {route['name'].upper()}\n"
                section += f"{'─' * 50}\n"
                section += f"Status: {status}\n"
                section += f"Price: RM{price} (No checked baggage, 7kg cabin)\n"
                section += f"Date: {flight['date']}\n"
                section += f"Airline: {flight['airline']}\n"
                section += f"Duration: {flight['duration']}\n"
                section += f"Stops: {flight['stops']}\n\n"
                
                fare_options = format_fare_options(flight['airline'], price)
                if fare_options:
                    section += f"Other Fare Options:\n{fare_options}\n\n"
                
                section += f"Book Now: {flight['link']}\n"
                alert_sections.append(section)
        
        time.sleep(0.5)
    
    # Save prices to GitHub
    save_daily_prices(all_flights)
    commit_history_to_github()
    
    # Build final message
    final_message = f"✈️ FLIGHT PRICE ALERT\n"
    final_message += f"Check Time: {check_time}\n"
    final_message += f"{'═' * 50}\n"
    
    if alert_sections:
        final_message += "\n".join(alert_sections)
    else:
        final_message += "No price changes detected - all flights above budget.\n"
    
    # Add 2-hour full update
    if force_send:
        final_message += f"\n{'═' * 50}\n"
        final_message += "📊 2-HOUR FULL UPDATE\n"
        final_message += f"{'─' * 50}\n\n"
        
        for i, (route_name, flight) in enumerate(all_flights.items(), 1):
            final_message += f"{i}. {route_name}\n"
            final_message += f"   Price: RM{flight['price']} | Date: {flight['date']}\n"
            final_message += f"   {flight['airline']} | {flight['duration']} | {flight['stops']} stops\n"
            final_message += f"   {flight['link']}\n\n"
    
    # Add daily Claude summary at 10 PM with full day's history
    if send_summary:
        print("\n[CLAUDE] Generating AI summary from today's FULL price history...\n")
        price_history = get_today_price_history()
        if price_history:
            summary = get_claude_daily_summary(price_history)
            if summary:
                final_message += f"\n{'═' * 50}\n"
                final_message += "🤖 CLAUDE AI DAILY SUMMARY (10 PM)\n"
                final_message += f"{'─' * 50}\n"
                final_message += f"Analysis of {len(price_history)} routes throughout the day:\n\n"
                final_message += summary
        else:
            print("[CLAUDE] No price history available")
    
    send_telegram_message(final_message)
    return final_message

if __name__ == "__main__":
    print("Flight Price Bot - Started (GitHub-stored price history + Claude AI)\n")
    check_all_routes()