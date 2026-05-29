import machine
import dht
import time
import ujson
import network
from umqtt.simple import MQTTClient
import ssd1306

# Pin Constants
DHT_PIN = 15
PIR_PIN = 14
LDR_PIN = 34
SDA_PIN = 21
SCL_PIN = 22

# MQTT Cloud Gateway Configuration
MQTT_BROKER    = "broker.hivemq.com"
MQTT_PORT      = 1883
MQTT_CLIENT_ID = "abhiram_node_8829" 
MQTT_TOPIC     = "decodelabs/abhiram/telemetry"

def connect_wifi():
    """Establishes connection to Wokwi virtual Wi-Fi infrastructure."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("[NET] Connecting to Wi-Fi Gateway...")
        wlan.connect("Wokwi-GUEST", "")
        while not wlan.isconnected():
            time.sleep(0.5)
    print(f"[NET] Network Layer Ready. Assigned IP: {wlan.ifconfig()[0]}")
    return True

def init_hardware():
    """Maps and instantiates all physical peripherals."""
    try:
        th_dev = dht.DHT22(machine.Pin(DHT_PIN))
        pir_dev = machine.Pin(PIR_PIN, machine.Pin.IN)
        ldr_dev = machine.ADC(machine.Pin(LDR_PIN))
        ldr_dev.atten(machine.ADC.ATTN_11DB)
        
        i2c_bus = machine.I2C(0, sda=machine.Pin(SDA_PIN), scl=machine.Pin(SCL_PIN))
        oled_display = ssd1306.SSD1306_I2C(128, 64, i2c_bus)
        return th_dev, pir_dev, ldr_dev, oled_display
    except Exception as e:
        print(f"[FATAL] Hardware mapping exception: {e}")
        return None, None, None, None

def update_oled_view(display, data):
    """Refreshes the local screen view using structured UI hierarchies."""
    display.fill(0)
    if data["status"] == "SUCCESS":
        display.fill_rect(0, 0, 128, 13, 1)
        display.text("NODE ONLINE", 24, 3, 0)
        display.text(f"Temp : {data['temperature']:.1f} C", 4, 18, 1)
        display.text(f"Humid: {data['humidity']:.1f} %", 4, 29, 1)
        display.text(f"Light: {data['light_level']:.1f} %", 4, 40, 1)
        
        if data["motion"] == 1:
            display.fill_rect(0, 52, 128, 12, 1)
            display.text("[!] ACTIVE MOTION", 4, 54, 0)
        else:
            display.rect(0, 52, 128, 12, 1)
            display.text("ZONE SECURE", 20, 54, 1)
    else:
        display.text("SYSTEM ERROR", 16, 25, 1)
    display.show()

def main():
    print("[SYSTEM] Starting Industrial Node...")
    connect_wifi()
    th, pir, ldr, oled = init_hardware()
    
    if not oled: return

    # Connect to Cloud Message Broker
    print(f"[MQTT] Initializing handshake with upstream broker: {MQTT_BROKER}...")
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        client.connect()
        print("[MQTT] Pipeline connection handshake verified.")
    except Exception as e:
        print(f"[MQTT] Connection failed: {e}. Running local-only mode.")
        client = None

    while True:
        try:
            th.measure()
            temp = th.temperature()
            hum = th.humidity()
            motion_state = pir.value() # 1 or 0
            
            raw_analog = ldr.read()
            light_pct = ((4095 - raw_analog) / 4095) * 100
            
            # Construct serialized JSON message payload
            payload = {
                "status": "SUCCESS",
                "temperature": temp,
                "humidity": hum,
                "motion": motion_state,
                "light_level": light_pct,
                "device_id": MQTT_CLIENT_ID
            }
            
            update_oled_view(oled, payload)
            
            # Publish payload to cloud if broker is connected
            if client:
                client.publish(MQTT_TOPIC, ujson.dumps(payload))
                print(f"[TX Cloud] {ujson.dumps(payload)}")
                
        except Exception as e:
            print(f"[LOOP ERROR] {e}")
            
        time.sleep(2.0)

if __name__ == "__main__":
    main()