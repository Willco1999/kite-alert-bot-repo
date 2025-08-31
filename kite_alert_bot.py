import os
import requests
import csv
import datetime
from collections import defaultdict

# === Secrets from GitHub Actions ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
OWM_API_KEY = os.environ.get("OWM_API_KEY")

# === Config ===
CSV_FILE = "spots_full.csv"
FORECAST_HOURS = [9, 12, 18]   # morning, midday, evening
OWM_MAX_CALLS = 200            # safeguard under free tier (1000/day)

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
    url = (
        f"https://api.openweathermap.org/data/2.5/forecast?"
        f"lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def pick_relevant_forecasts(data, target_day_offset=0):
    """Pick out forecasts for today (0) or tomorrow (1) at chosen hours."""
    out = {}
    target_date = datetime.datetime.utcnow().date() + datetime.timedelta(days=target_day_offset)
    for entry in data["list"]:
        dt = datetime.datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
        if dt.date() == target_date and dt.hour in FORECAST_HOURS:
            wind_ms = entry["wind"]["speed"]
            wind_deg = entry["wind"]["deg"]
            wind_knots = round(knots_from_ms(wind_ms))
            out[dt.hour] = {"knots": wind_knots, "deg": wind_deg}
    return out

def build_detailed_report(spots, target_day_offset=0):
    """Build detailed spot-by-spot report for today or tomorrow."""
    report_by_region = defaultdict(list)
    owm_calls = 0

    regions = defaultdict(list)
    for spot in spots:
        regions[spot["region"]].append(spot)

    for region, region_spots in regions.items():
        if owm_calls >= OWM_MAX_CALLS:
            report_by_region[region].append("⚠️ OWM API call limit reached")
            continue

        try:
            forecast = fetch_region_forecast(region_spots[0]["latitude"], region_spots[0]["longitude"])
            owm_calls += 1
        except Exception as e:
            report_by_region[region].append(f"⚠️ Forecast error: {e}")
            continue

        rel = pick_relevant_forecasts(forecast, target_day_offset)

        for spot in region_spots:
            lines = []
            for hour in sorted(rel.keys()):
                f = rel[hour]
                dir_str = deg_to_compass(f["deg"])
                good_dir = dir_str in spot["best_directions"].split(";")
                within_knots = spot["min_knots"] <= f["knots"] <= spot["max_knots"]
                status = "✅ ON" if good_dir and within_knots else "❌ OFF"
                lines.append(f"{status} {dir_str} {f['knots']} kt @ {hour:02d}:00")

            if lines:
                report_by_region[region].append(
                    f"- {spot['name']}\n   " + "\n   ".join(lines) + f"\n   🌊 Tide: {spot['tide_notes']}"
                )

    msg = "🌬 Kite Forecast\n"
    for region, spots_lines in report_by_region.items():
        if spots_lines:
            msg += f"\n🌍 {region}\n" + "\n".join(spots_lines) + "\n"
    return msg

def build_5day_outlook(spots):
    """Evening run: filtered 5-day outlook per region, sorted chronologically."""
    outlook_by_region = defaultdict(dict)  # region -> {date: (dir, knots)}
    owm_calls = 0

    regions = defaultdict(list)
    for spot in spots:
        regions[spot["region"]].append(spot)

    for region, region_spots in regions.items():
        if owm_calls >= OWM_MAX_CALLS:
            continue
        try:
            forecast = fetch_region_forecast(region_spots[0]["latitude"], region_spots[0]["longitude"])
            owm_calls += 1
        except:
            continue

        daily = defaultdict(list)
        for entry in forecast["list"]:
            dt = datetime.datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
            if dt.hour == 12:  # midday as representative
                wind_knots = round(knots_from_ms(entry["wind"]["speed"]))
                wind_dir = deg_to_compass(entry["wind"]["deg"])
                daily[dt.date()].append((wind_dir, wind_knots))

        for day, vals in daily.items():
            avg_knots = sum(v[1] for v in vals) // len(vals)
            avg_dir = vals[0][0]
            kiteable = any(
                (avg_knots >= s["min_knots"] and avg_knots <= s["max_knots"])
                for s in region_spots
            )
            if kiteable:
                outlook_by_region[region][day] = (avg_dir, avg_knots)

    # Format sorted by date
    msg = "📅 5-Day Kiteable Outlook\n"
    for region, day_map in outlook_by_region.items():
        if day_map:
            msg += f"\n🌍 {region}\n"
            for day in sorted(day_map.keys()):
                d_str = day.strftime('%a %d %b')
                dir_, knots = day_map[day]
                msg += f"- {d_str}: {dir_} {knots} kt\n"
    return msg

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def get_run_label():
    hour = datetime.datetime.utcnow().hour
    if hour < 12:
        return "🌅 Morning forecast"
    else:
        return "🌙 Evening forecast"

if __name__ == "__main__":
    label = get_run_label()
    spots = load_spots()

    if label == "🌅 Morning forecast":
        message = f"{label}\n\n" + build_detailed_report(spots, target_day_offset=0)
    else:
        detailed = build_detailed_report(spots, target_day_offset=1)
        outlook = build_5day_outlook(spots)
        message = f"{label}\n\n🌬 Detailed Kite Forecast for Tomorrow\n{detailed}\n{outlook}"

    # --- DEBUG TEST MESSAGE ---
send_message("✅ Test: Kite Alert Bot is alive and can send messages!")

