from telegram import Bot
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import time
import asyncio

load_dotenv()

# API Keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

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

def should_send_6hour_update():
    """True only at 00:xx, 06:xx, 12:xx, 18:xx MYT"""
    now = datetime.now(MYT)
    return now.hour % 6 == 0

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
    force_send = should_send_6hour_update()
    
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
            if price < budget * 1.10:  # Show details only for RED/YELLOW
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
    
    # Build final message
    final_message = f"✈️ FLIGHT PRICE ALERT\n"
    final_message += f"Check Time: {check_time}\n"
    final_message += f"{'═' * 50}\n"
    
    if alert_sections:
        final_message += "\n".join(alert_sections)
    else:
        final_message += "No price changes detected - all flights above budget.\n"
    
    # Add 6-hour full update
    if force_send:
        final_message += f"\n{'═' * 50}\n"
        final_message += "📊 6-HOUR FULL UPDATE\n"
        final_message += f"{'─' * 50}\n\n"
        
        for i, (route_name, flight) in enumerate(all_flights.items(), 1):
            final_message += f"{i}. {route_name}\n"
            final_message += f"   Price: RM{flight['price']} | Date: {flight['date']}\n"
            final_message += f"   {flight['airline']} | {flight['duration']} | {flight['stops']} stops\n"
            final_message += f"   {flight['link']}\n\n"
    
    send_telegram_message(final_message)
    return final_message

if __name__ == "__main__":
    print("Flight Price Bot - Started (Clean Format)\n")
    check_all_routes()
