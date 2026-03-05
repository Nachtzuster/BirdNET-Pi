import sqlite3
import requests
import os
import logging
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from helpers import DB_PATH, get_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('weather')

def update_weather():
    conf = get_settings()
    lat = conf.get('LATITUDE', None)
    lon = conf.get('LONGITUDE', None)
    
    if lat is None or lon is None or lat == '' or lon == '':
        log.error("Latitude or Longitude not set. Cannot fetch weather.")
        return

    # Use Open-Meteo to fetch the past day and current forecast day
    # We use fahrenheit here because the UI logic can convert it later if needed, or we just display it natively. 
    # To be universally robust, let's fetch in Celsius internally and convert on frontend or rely on user settings. Wait, many users prefer F. We will fetch F for now to match the tooltip pitch.
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weather_code&temperature_unit=fahrenheit&past_days=1&forecast_days=1&timezone=auto"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        log.error(f"Failed to fetch weather: {e}")
        return

    # Parse data
    times = data['hourly']['time']
    temps = data['hourly']['temperature_2m']
    codes = data['hourly']['weather_code']

    # Connect to the SQLite DB
    # Note: Using uri=True to match db operations elsewhere, though standard path is fine.
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        
        # Ensure the weather table exists isolated from the detections table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS weather (
                Date DATE,
                Hour INT,
                Temp FLOAT,
                ConditionCode INT,
                PRIMARY KEY(Date, Hour)
            )
        ''')
        
        # Insert or replace hourly metrics
        for t, temp, code in zip(times, temps, codes):
            if temp is None:
                continue
            dt = datetime.fromisoformat(t)
            date_str = dt.strftime('%Y-%m-%d')
            hour = dt.hour
            
            cur.execute("INSERT OR REPLACE INTO weather (Date, Hour, Temp, ConditionCode) VALUES (?, ?, ?, ?)",
                        (date_str, hour, temp, code))
                        
        con.commit()
        con.close()
        log.info("Hourly weather data synced successfully to birds.db.")
    except Exception as e:
        log.error(f"Database error writing weather: {e}")

if __name__ == '__main__':
    update_weather()
