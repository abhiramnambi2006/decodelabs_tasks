import machine
import dht
import time
import ssd1306

# Pin Constants
DHT_PIN = 15
PIR_PIN = 14
LDR_PIN = 34
SDA_PIN = 21
SCL_PIN = 22

READ_INTERVAL = 2.0

def init_hardware():
    """Initializes and connects all sensor and display peripherals."""
    print("[INIT] Initializing multi-sensor node array...")
    try:
        # Sensors
        th_dev = dht.DHT22(machine.Pin(DHT_PIN))
        pir_dev = machine.Pin(PIR_PIN, machine.Pin.IN)
        ldr_dev = machine.ADC(machine.Pin(LDR_PIN))
        ldr_dev.atten(machine.ADC.ATTN_11DB)
        
        # I2C Bus & OLED Initialization - Using SoftI2C for Wokwi stability
        i2c_bus = machine.SoftI2C(sda=machine.Pin(SDA_PIN), scl=machine.Pin(SCL_PIN))
        oled_display = ssd1306.SSD1306_I2C(128, 64, i2c_bus)
        
        print("[SUCCESS] Hardware interfaces perfectly mapped.")
        return th_dev, pir_dev, ldr_dev, oled_display
    except Exception as e:
        print(f"[CRITICAL] Peripheral initialization mapping fault: {e}")
        return None, None, None, None

def update_oled_view(display, data):
    """Draws a premium, structured dashboard onto the OLED display."""
    display.fill(0) # Clear previous frame buffer
    
    if data["status"] == "SUCCESS":
        # 1. UI HEADER: Inverted solid block with clean text alignment
        display.fill_rect(0, 0, 128, 13, 1)          # Draw white banner
        display.text("SENSOR READINGS", 4, 3, 0)      # Draw black text on top
        
        # 2. DATA GRID: Left-aligned labels, right-aligned telemetry values
        # Temperature Row (Y=18)
        display.text("TEMP  :", 6, 18, 1)
        display.text(f"{data['temperature']:.1f} C", 64, 18, 1)
        
        # Humidity Row (Y=29)
        display.text("HUMID :", 6, 29, 1)
        display.text(f"{data['humidity']:.1f} %", 64, 29, 1)
        
        # Light Intensity Row (Y=40)
        display.text("LIGHT :", 6, 40, 1)
        display.text(f"{data['light_level']:.1f} %", 64, 40, 1)
        
        # 3. DYNAMIC FOOTER: Context-aware hardware notification banner
        if data["motion"] == "ALERT-MOVING":
            # Critical Alert state: Flashes a solid white box with black text
            display.fill_rect(0, 52, 128, 12, 1)
            display.text("!! MOTION ALERT !!", 4, 54, 0)
        else:
            # Standard Idle state: Sleek bounding box with centered text
            display.rect(0, 52, 128, 12, 1)
            display.text("SYSTEM SECURE", 12, 54, 1)
            
    else:
        # System Error Screen
        display.fill_rect(0, 0, 128, 13, 1)
        display.text("SYSTEM CRITICAL", 4, 3, 0)
        display.text("HARDWARE FAULT", 8, 32, 1)
        display.rect(0, 52, 128, 12, 1)
        display.text("CHECK SENSORS", 12, 54, 1)
        
    display.show() # Push drawn graphics memory to the physical screen

def read_telemetry(dht_dev, pir_dev, ldr_dev):
    """Gathers synchronized sensor snapshots."""
    try:
        dht_dev.measure()
        temp = dht_dev.temperature()
        hum = dht_dev.humidity()
        motion_active = pir_dev.value() == 1
        
        raw_analog = ldr_dev.read()
        light_percentage = ((4095 - raw_analog) / 4095) * 100
        
        return {
            "status": "SUCCESS",
            "temperature": temp,
            "humidity": hum,
            "motion": "ALERT-MOVING" if motion_active else "SECURE",
            "light_level": light_percentage,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

def print_terminal_header():
    """Prints the enhanced professional header block."""
    print("\n" + "═" * 60)
    print("    IoT SENSOR SIMULATION - Enhanced Node Terminal")
    print("═" * 60)
    print(f" Sensors  : Temperature | Humidity | Motion | Light")
    print(f" Interval : {READ_INTERVAL}s")
    print(" Status   : ACTIVE STREAM")
    print("═" * 60 + "\n")

def print_terminal_reading(count, data):
    """Prints a beautifully formatted, auto-aligning ASCII reading block."""
    # Format the local time (HH:MM:SS)
    t = time.localtime()
    time_str = f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
    
    # Map motion status to clean text
    motion_text = "MOTION DETECTED" if data['motion'] == "ALERT-MOVING" else "NO MOTION"
    
    # Construct the top border dynamically so it always caps at 60 characters
    top_border = f"┌─ Reading {count:02d} ─── {time_str} "
    top_border += "─" * (60 - len(top_border) - 1) + "┐"
    
    print(top_border)
    
    # Manual padding function to replace MicroPython's missing .ljust()
    def pad(text, total_width=58):
        return text + " " * (total_width - len(text))

    # Using the pad function ensures exactly 58 characters of space inside the 60-character box
    print("│" + pad(f"  Temperature : {data['temperature']:6.2f} C") + "│")
    print("│" + pad(f"  Humidity    : {data['humidity']:6.2f} %") + "│")
    print("│" + pad(f"  Motion      : {motion_text}") + "│")
    print("│" + pad(f"  Light       : {data['light_level']:6.2f} %") + "│")
    print("└" + "─" * 58 + "┘")

def main():
    th, pir, ldr, oled = init_hardware()
    
    if not oled:
        print("[HALT] System missing critical display hardware.")
        return

    print_terminal_header()
    reading_count = 1

    while True:
        payload = read_telemetry(th, pir, ldr)
        
        # Update local graphical layout
        update_oled_view(oled, payload)
        
        # Enhanced Background Terminal Streaming
        if payload["status"] == "SUCCESS":
            print_terminal_reading(reading_count, payload)
            reading_count += 1
        else:
            print(f"┌─ SYSTEM FAULT {'─'*43}┐")
            err_text = f"  ERROR: {payload['message']}"
            # Manual padding for the error message
            print("│" + err_text + " " * (58 - len(err_text)) + "│")
            print("└" + "─" * 58 + "┘")
            
        time.sleep(READ_INTERVAL)

if __name__ == "__main__":
    main()