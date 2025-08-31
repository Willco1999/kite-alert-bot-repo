# 🌬 Kite Alert Bot
A Telegram bot that automatically posts **kite-surfing forecasts** for UK spots into your Telegram group **twice daily**.

- 🌅 Morning forecast (06:00 UK): **today’s forecast** at 09:00, 12:00, 18:00.  
- 🌙 Evening forecast (19:00 UK): **tomorrow’s detailed forecast** + a **5-day kiteable outlook** (filtered & sorted).  
- ✅ Includes tide notes (from CSV).  
- 📩 Messages sent directly to Telegram group.  

---

## 🚀 Features
- Forecasts per **spot** (wind direction, knots, ON/OFF status, tide notes).  
- Grouped by **region** for easy scanning.  
- 5-day outlook shows **only kiteable days/regions** (no noise).  
- Safe API usage: capped under free tier (OWM).  
- Fully automated with **GitHub Actions** (no server needed).  

---

## 📂 Repository Structure
.github/workflows/alerts.yml # GitHub Actions workflow (runs bot twice daily)
kite_alert_bot.py # Main bot script
requirements.txt # Python dependencies
spots_full.csv # List of kite spots with config
README.md # This file

markdown
Copy code

---

## ⚙️ Setup

### 1. Create Telegram Bot
1. Open Telegram, search for `@BotFather`.  
2. Run `/newbot` → name your bot → copy the **token**.  
3. Add the bot to your group.  
4. Get your group `CHAT_ID` (via bot or API).  

### 2. Get Weather API Key
- Sign up at [OpenWeatherMap](https://openweathermap.org/forecast5).  
- Copy your **API key**.  

### 3. Add Secrets in GitHub
Go to:  
**Repo → Settings → Secrets and variables → Actions** → **New repository secret**.  

Add:
- `TELEGRAM_TOKEN` = your BotFather token  
- `CHAT_ID` = your Telegram group ID  
- `OWM_API_KEY` = your OpenWeather API key  

### 4. Upload Spot List
- Add/update `spots_full.csv` in repo root.  
- CSV fields:
```csv
name,region,latitude,longitude,min_knots,max_knots,best_directions,tide_notes
Exmouth,South Devon,50.617,-3.423,12,35,W;SW,Best 2hrs before and after low tide
Bantham,South Devon,50.284,-3.879,12,35,W;NW;SW,Needs mid–outgoing tide, avoid full low
🕒 Schedule
The bot runs twice daily via cron:

yaml
Copy code
schedule:
  - cron: "0 5 * * *"   # 05:00 UTC = 06:00 UK (BST)
  - cron: "0 18 * * *"  # 18:00 UTC = 19:00 UK (BST)
⚠️ Note: In winter (GMT), this shifts to 05:00 & 18:00 UK.
For exact UK times year-round, add timezone handling in Python.

You can also trigger manually via GitHub Actions → Run workflow.

📩 Example Messages
Morning run (06:00 UK)

pgsql
Copy code
🌅 Morning forecast

🌬 Kite Forecast

🌍 South Devon
- Exmouth
   ❌ OFF SW 7 kt @ 09:00
   ✅ ON W 16 kt @ 12:00
   ✅ ON W 19 kt @ 18:00
   🌊 Tide: Best 2hrs before and after low tide
Evening run (19:00 UK)

pgsql
Copy code
🌙 Evening forecast

🌬 Detailed Kite Forecast for Tomorrow

🌍 Cornwall North
- Gwithian
   ❌ OFF S 8 kt @ 09:00
   ✅ ON NW 18 kt @ 12:00
   ✅ ON NW 20 kt @ 18:00
   🌊 Tide: Works best 2hrs after high tide

📅 5-Day Kiteable Outlook

🌍 Cornwall North
- Mon 01 Sep: NW 18 kt
- Thu 04 Sep: W 22 kt
🔧 Updating / Customising
To change forecast times → edit FORECAST_HOURS in kite_alert_bot.py.

To add spots → edit spots_full.csv.

To change run times → update alerts.yml cron schedule.

📜 License
Free to use & adapt. Built for UK kiteboarders 🤙
