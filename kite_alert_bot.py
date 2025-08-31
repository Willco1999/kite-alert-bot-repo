import os
import requests
import csv
from collections import defaultdict

# === Secrets from GitHub Actions ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
OWM_API_KEY = os.environ.get("OWM_API_KEY")

# === Config ===
CSV_FILE = "spots_full.csv"
FORECAST_HOURS = [12, 18]   # midday & evening snapshots
OWM_MAX_CALLS = 200         # safeguard under free tier (1000/day)

# === Helpers ===
def load_spots():
    spots = []
    with open(CSV_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["latitude"] = float(row["latitude"])
            row["longitude"] = float(row["longitude"])
            row["min_knots"] = int(row["min_knots"])
            row["max_knots"] = int(row["max_knots"])
            spots.append(row)
    return spots

def knots_from_ms(ms):
    return ms * 1.94384

def deg_to_compass(deg):
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    ix = round(deg / 45) % 8
    return dirs[ix]

def fetch_region_forecast(lat, lon):
    """Fetch forecast for a region (shared by spots nearby)."""
    url = (
        f"https://api.openweathermap.org/data/2.5/forecast?"
        f"lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def pick_relevant_forecasts(data):
    """Pick out midday/evening forecasts."""
    out = {}
    for entry in data["list"]:
        dt_txt = entry["dt_txt"]  # format "YYYY-MM-DD HH:MM:SS"
        hour = int(dt_txt.split(" ")[1].split(":")[0])
        if hour in FORECAST_HOURS:
            wind_ms = entry["wind"]["speed"]
            wind_deg = entry["wind"]["deg"]
            wind_knots = round(knots_from_ms(wind_ms))
            out[hour] = {"knots": wind_knots, "deg": wind_deg}
    return out

def build_report(spots):
    report_by_region = defaultdict(list)
    owm_calls = 0

    # Group by region for efficiency
    regions = defaultdict(list)
    for spot in spots:
        regions[spot["region"]].append(spot)

    for region, region_spots in regions.items():
        if owm_calls >= OWM_MAX_CALLS:
            report_by_region[region].append("⚠️ OWM API call limit reached")
            continue

        # Use first spot in region as representative forecast
        try:
            forecast = fetch_region_forecast(region_spots[0]["latitude"], region_spots[0]["longitude"])
            owm_calls += 1
        except Exception as e:
            report_by_region[region].append(f"⚠️ Forecast error: {e}")
            continue

        rel = pick_relevant_forecasts(forecast)

        for spot in region_spots:
            lines = []
            for hour, f in rel.items():
                dir_str = deg_to_compass(f["deg"])
                good_dir = dir_str in spot["best_directions"].split(";")
                within_knots = spot["min_knots"] <= f["knots"] <= spot["max_knots"]
                status = "✅ ON" if good_dir and within_knots else "❌ OFF"
                lines.append(f"{status} {dir_str} {f['knots']} kt @ {hour}:00")

            report_by_region[region].append(
                f"- {spot['name']}\n   " + "\n   ".join(lines) + f"\n   🌊 Tide: {spot['tide_notes']}"
            )

    # Format final message
    msg = "🌬 Kite Forecast\n"
    for region, spots_lines in report_by_region.items():
        msg += f"\n🌍 {region}\n" + "\n".join(spots_lines) + "\n"
    return msg

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

if __name__ == "__main__":
    # Always send test message first
    send_message("✅ Kite Alert Bot started — test OK")

    try:
        spots = load_spots()
        message = build_report(spots)
        send_message(message)
    except Exception as e:
        send_message(f"⚠️ Error in bot: {e}")
