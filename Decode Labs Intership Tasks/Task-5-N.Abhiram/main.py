import machine
import time
import math
import network
import ujson
from umqtt.simple import MQTTClient
from mpu6050 import MPU6050
from hcsr04 import HCSR04

# ============================================================
#  CONFIGURATION
# ============================================================
WIFI_SSID     = "Wokwi-GUEST"
WIFI_PASSWORD = ""

MQTT_BROKER   = "broker.hivemq.com"
MQTT_PORT     = 1883
MQTT_CLIENT_ID = "esp32_disaster_node_1"

# Matching Topics
TOPIC_EARTHQUAKE = b"my_custom_project_99/disaster/earthquake"
TOPIC_FLOOD      = b"my_custom_project_99/disaster/flood"
TOPIC_FIRE       = b"my_custom_project_99/disaster/fire"
TOPIC_STATUS     = b"my_custom_project_99/disaster/status"

EARTHQUAKE_THRESHOLD = 12.0
FLOOD_THRESHOLD_CM   = 15.0
GAS_THRESHOLD        = 2000
ZONE_ID = "Zone-1"

# ============================================================
#  HARDWARE
# ============================================================
i2c = machine.I2C(0, sda=machine.Pin(21), scl=machine.Pin(22), freq=400000)
mpu = MPU6050(i2c)
sonar = HCSR04(trigger_pin=5, echo_pin=18)
mq2 = machine.ADC(machine.Pin(34))
mq2.atten(machine.ADC.ATTN_11DB)

buzzer = machine.Pin(15, machine.Pin.OUT)
red_led = machine.Pin(2, machine.Pin.OUT)
green_led = machine.Pin(4, machine.Pin.OUT)

# ============================================================
#  WIFI & MQTT
# ============================================================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("\n✅ WiFi Connected. IP:", wlan.ifconfig()[0])
    return True

mqtt_client = None
def connect_mqtt():
    global mqtt_client
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        client.connect()
        mqtt_client = client
        print("✅ Connected to MQTT Broker\n")
        print("="*40)
        return True
    except Exception as e:
        print("❌ MQTT Connection failed:", e)
        return False

def publish(topic, payload_dict):
    global mqtt_client
    try:
        msg = ujson.dumps(payload_dict)
        mqtt_client.publish(topic, msg)
    except Exception as e:
        print("Publish error:", e)

# ============================================================
#  SENSORS
# ============================================================
def trigger_alert(duration_ms=1000):
    red_led.value(1)
    green_led.value(0)
    buzzer.value(1)
    time.sleep_ms(duration_ms)
    buzzer.value(0)
    red_led.value(0)
    green_led.value(1)

def read_earthquake():
    ax, ay, az = mpu.acceleration
    az_corrected = az - 9.8
    magnitude = math.sqrt(ax**2 + ay**2 + az_corrected**2)
    alert = magnitude > EARTHQUAKE_THRESHOLD
    return magnitude, alert, {"zone": ZONE_ID, "ax": ax, "ay": ay, "az": az, "magnitude": magnitude, "alert": alert}

def read_flood():
    distance = sonar.distance_cm()
    alert = distance < FLOOD_THRESHOLD_CM
    return distance, alert, {"zone": ZONE_ID, "distance_cm": distance, "alert": alert}

def read_gas():
    raw = mq2.read()
    ppm = raw * 0.5
    alert = raw > GAS_THRESHOLD
    return raw, alert, {"zone": ZONE_ID, "raw_adc": raw, "ppm_approx": ppm, "alert": alert}

# ============================================================
#  MAIN LOOP
# ============================================================
def main():
    wifi_ok = connect_wifi()
    mqtt_ok = connect_mqtt() if wifi_ok else False

    heartbeat_every = 1 # Publishes status every 1 second for fast testing
    cycle = 0

    while True:
        cycle += 1
        any_alert = False

        # Read all sensors
        mag, eq_alert, eq_data = read_earthquake()
        dist, fl_alert, fl_data = read_flood()
        raw, gas_alert, gas_data = read_gas()

        # --- LIVE SERIAL MONITOR OUTPUT ---
        print(f"[{cycle}] LIVE SENSOR DATA:")
        print(f" 🌍 Seismic: {mag:5.2f} m/s²  | Alert: {'🔴 YES' if eq_alert else '🟢 NO'}")
        print(f" 💧 Flood:   {dist:5.1f} cm   | Alert: {'🔴 YES' if fl_alert else '🟢 NO'}")
        print(f" 🔥 Gas/Fire:{gas_data['ppm_approx']:5.0f} ppm   | Alert: {'🔴 YES' if gas_alert else '🟢 NO'}")
        print("-" * 40)
        # ----------------------------------

        # Handle MQTT Publishing for Alerts
        if eq_alert: 
            any_alert = True
            publish(TOPIC_EARTHQUAKE, eq_data)

        if fl_alert: 
            any_alert = True
            publish(TOPIC_FLOOD, fl_data)

        if gas_alert: 
            any_alert = True
            publish(TOPIC_FIRE, gas_data)

        # Hardware Alarms
        if any_alert:
            trigger_alert()
        else:
            buzzer.value(0)
            red_led.value(0)
            green_led.value(1)

        # Handle MQTT Status Heartbeat
        if cycle % heartbeat_every == 0 and mqtt_ok:
            publish(TOPIC_STATUS, {"zone": ZONE_ID, "earthquake": eq_data, "flood": fl_data, "gas": gas_data})

        time.sleep(1) # Wait 1 second before the next reading

# Start the system
main()