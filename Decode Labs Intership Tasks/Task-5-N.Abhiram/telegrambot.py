#!/usr/bin/env python3
import json
import time
import logging
import requests
import paho.mqtt.client as mqtt

# ============================================================
#  CONFIGURATION
# ============================================================
# PASTE YOUR WORKING CREDENTIALS HERE:
TELEGRAM_BOT_TOKEN = "8888869865:AAERkKTP4I05BZRN55LxyG51T0nNrgjkMuo"
TELEGRAM_CHAT_ID = "5729106136"

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPICS = [
    "my_custom_project_99/disaster/earthquake",
    "my_custom_project_99/disaster/flood",
    "my_custom_project_99/disaster/fire"
]

# Set to 0 for instant testing. Change to 60 later for real-world use!
COOLDOWN_SECONDS = 0 

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
last_alert_time = {"earthquake": 0.0, "flood": 0.0, "fire": 0.0}

def send_telegram_alert(disaster_type, data):
    icons = {
        "earthquake": "⚠️ 🔴 EARTHQUAKE DETECTED!",
        "flood": "🌊 🔵 FLOOD WARNING!",
        "fire": "🔥 🟠 GAS/FIRE DETECTED!"
    }
    
    header = icons.get(disaster_type, "🚨 ALERT!")
    zone = data.get("zone", "Unknown Zone")
    
    if disaster_type == "earthquake":
        details = f"Magnitude: {data.get('magnitude', 0):.2f} m/s²"
    elif disaster_type == "flood":
        details = f"Water Distance: {data.get('distance_cm', 0):.1f} cm"
    elif disaster_type == "fire":
        details = f"Gas Concentration: {data.get('ppm_approx', 0):.0f} PPM"
    else:
        details = str(data)

    message = f"{header}\n📍 Location: {zone}\n📊 {details}\n🕒 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info(f"Successfully sent Telegram alert for {disaster_type}")
        else:
            logging.error(f"Telegram API Error: {response.text}")
    except Exception as e:
        logging.error(f"Failed to connect to Telegram: {e}")

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logging.info(f"Connected to MQTT Broker: {MQTT_BROKER}")
        for topic in TOPICS:
            client.subscribe(topic)
    else:
        logging.error(f"Failed to connect. Code: {reason_code}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        return

    topic = msg.topic
    current_time = time.time()

    if "earthquake" in topic: d_type = "earthquake"
    elif "flood" in topic: d_type = "flood"
    elif "fire" in topic: d_type = "fire"
    else: return

    if data.get("alert") is True:
        if (current_time - last_alert_time[d_type]) >= COOLDOWN_SECONDS:
            logging.warning(f"CRITICAL {d_type.upper()} ALERT TRIGGERED! Sending Telegram notification...")
            send_telegram_alert(d_type, data)
            last_alert_time[d_type] = current_time
        else:
            logging.debug(f"Alert suppressed for {d_type} (Cooldown active)")

if __name__ == "__main__":
    logging.info("Starting Telegram Alert Worker...")
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="telegram_alerter_worker_99_final")
    except AttributeError:
        client = mqtt.Client(client_id="telegram_alerter_worker_99_final")
        
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logging.info("Worker stopped by user.")