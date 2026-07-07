import requests
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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

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

HISTORY_FILE = "daily_prices.json"


def build_google_flights_url(from_code, to_code, departure_date):
    date_obj = datetime.strptime(departure_date, "%Y-%m-%d")
    date_formatted = date_obj.strftime("%m/%d/%Y")
    return f"https://www.google.com/flights?flt={from_code}{date_formatted}{to_code}&curr=MYR"


def get_flight_details(from_code, to_code, route_name):
    try:
        departure_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_flights",
            "departure_id": from_code,
            "arrival_id": to_code,
            "outbound_date": departure_date,
            "currency": "MYR",
            "hl": "en",
            "type": "2",  # one-way
            "api_key": SERPAPI_KEY,
        }

        resp = requests.get(url, params=params, timeout=20)
        data = resp.json()

        flights = data.get("best_flights") or data.get("other_flights") or []

        if not flights:
            print(f"No flights returned for {route_name}")
            return None

        best = flights[0]
        price = best.get("price")
        if price is None:
            return None

        legs = best.get("flights", [])
        airline = legs[0].get("airline", "Unknown") if legs else "Unknown"
        duration_min = best.get("total_duration", 0)
        hours, mins = divmod(duration_min, 60)
        duration_str = f"{hours}h {mins}m" if hours else f"{mins}m"
        layovers = best.get("layovers", [])
        stops = len(layovers)

        date_obj = datetime.strptime(departure_date, "%Y-%m-%d")
        date_display = date_obj.strftime("%d %b %Y")
        booking_link = build_google_flights_url(from_code, to_code, departure_date)

        return {
            "price": int(price),
            "airline": airline,
            "duration": duration_str,
            "stops": stops,
            "date": date_display,
            "link": booking_link,
        }

    except Exception as e:
        print(f"Error {route_name}: {e}")
        return None


def save_daily_prices(all_flights):
    today = datetime.now(MYT).strftime("%Y-%m-%d")
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        else:
            history = {}

        if today not in history:
            history[today] = {}

        for route, flight in all_flights.items():
            if flight and flight["price"]:
                if route not in history[today]:
                    history[today][route] = {
                        "prices": [],
                        "airline": flight["airline"],
                        "duration": flight["duration"],
                    }
                current_time = datetime.now(MYT).strftime("%H:%M")
                history[today][route]["prices"].append(
                    {"time": current_time, "price": flight["price"]}
                )

        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)

    except Exception as e:
        print(f"Error saving history: {e}")


def commit_history_to_github():
    try:
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False, timeout=5)
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=False, timeout=5)
        subprocess.run(["git", "add", HISTORY_FILE], check=False, timeout=5)
        result = subprocess.run(
            ["git", "commit", "-m", f"Update price history - {datetime.now(MYT).strftime('%Y-%m-%d %H:%M')}"],
            check=False, timeout=10, capture_output=True, text=True
        )
        if "nothing to commit" in result.stdout + result.stderr:
            print("Nothing to commit")
            return
        subprocess.run(["git", "push"], check=False, timeout=15)
    except Exception as e:
        print(f"Git error: {e}")


def get_today_price_history():
    today = datetime.now(MYT).strftime("%Y-%m-%d")
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
            if today in history:
                return history[today]
    except Exception as e:
        print(f"Error loading history: {e}")
    return {}


def get_claude_daily_summary(price_history):
    try:
        if not CLAUDE_API_KEY:
            return "Claude API key not configured"
        if not price_history:
            return "No price history available"

        client = Anthropic(api_key=CLAUDE_API_KEY)

        history_text = ""
        for route, data in price_history.items():
            if "prices" in data and data["prices"]:
                prices = [p["price"] for p in data["prices"]]
                min_price = min(prices)
                max_price = max(prices)
                latest = prices[-1]
                first = prices[0]
                trend = "UP" if latest > first else "DOWN"
                change = abs(latest - first)
                history_text += f"\n{route}: RM{first}->RM{latest} ({change}RM {trend}) | Low:RM{min_price} High:RM{max_price}"

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyze today's flight price history in 3-4 sentences. Budget RM700 per route.\n{history_text}\nInclude: best deals, trends, booking recommendations.",
                }
            ],
        )
        return message.content[0].text

    except Exception as e:
        return f"Claude error: {e}"


def should_send_2hour_update():
    now = datetime.now(MYT)
    return now.hour % 2 == 0 and now.minute < 5


def should_send_daily_summary():
    now = datetime.now(MYT)
    return now.hour == 22 and now.minute < 5


def send_telegram_message(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=None))
    except Exception as e:
        print(f"Telegram error: {e}")


def check_all_routes():
    check_time = datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")

    all_flights = {}
    alert_sections = []
    force_send = should_send_2hour_update()
    send_summary = should_send_daily_summary()

    for i, route in enumerate(ROUTES, 1):
        print(f"Checking {route['name']}...")
        flight = get_flight_details(route["from"], route["to"], route["name"])

        if flight is None:
            print(f"  -> No data")
            continue

        all_flights[route["name"]] = flight
        price = flight["price"]
        budget = BUDGETS[route["name"]]
        print(f"  -> RM{price} via {flight['airline']}")

        if price is not None:
            if price < budget:
                status = "DEAL"
            elif price < budget * 1.10:
                status = "CLOSE"
            else:
                status = "HIGH"

            if price < budget * 1.10:
                section = f"\n{i}. {route['name'].upper()}\n"
                section += f"Status: {status} | RM{price}\n"
                section += f"Date: {flight['date']}\n"
                section += f"Airline: {flight['airline']} | {flight['duration']} | {flight['stops']} stop(s)\n"
                section += f"Book: {flight['link']}\n"
                alert_sections.append(section)

        time.sleep(1)

    save_daily_prices(all_flights)
    commit_history_to_github()

    final_message = f"FLIGHT PRICE ALERT\nChecked: {check_time} MYT\n{'='*35}\n"

    if alert_sections:
        final_message += "\n".join(alert_sections)
    else:
        final_message += "No deals below budget right now.\n"

    if force_send:
        final_message += f"\n{'='*35}\n2-HOUR UPDATE\n"
        for route_name, flight in all_flights.items():
            if flight.get("price"):
                final_message += f"  {route_name}: RM{flight['price']} | {flight['airline']}\n"

    if send_summary:
        final_message += f"\n{'='*35}\nCLAUDE DAILY SUMMARY\n"
        price_history = get_today_price_history()
        if price_history:
            summary = get_claude_daily_summary(price_history)
            final_message += summary
        else:
            final_message += "No price history today.\n"

    print("\n--- Sending message ---")
    print(final_message)
    send_telegram_message(final_message)


if __name__ == "__main__":
    check_all_routes()
