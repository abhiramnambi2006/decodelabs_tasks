# 🌐 DecodeLabs Internship — IoT Tasks
**Intern:** N. Abhiram  
**Domain:** Internet of Things (IoT) & Embedded Systems  
**Platform:** Wokwi Simulator + MicroPython (ESP32)

---

## 📁 Repository Structure

```
decodelabs-iot-internship/
│
├── Task-1_IoT-Presentation/
│   └── 1780053473844_Task-1-N_Abhiram.pdf     # IoT & Device Communication slides
│
├── Task-2_Multi-Sensor-Node-Local/
│   ├── main.py                                 # ESP32 firmware (local OLED only)
│   ├── ssd1306.py                              # OLED display driver
│   ├── diagram.json                            # Wokwi circuit diagram
│   └── wokwi-project.txt                       # Wokwi project link
│
├── Task-3_Multi-Sensor-Node-MQTT/
│   ├── main.py                                 # ESP32 firmware (WiFi + MQTT cloud)
│   ├── ssd1306.py                              # OLED display driver
│   ├── diagram.json                            # Wokwi circuit diagram
│   ├── wokwi-project.txt                       # Wokwi project link
│   ├── dashboard.py                            # Streamlit live telemetry dashboard
│   └── telemetry_history.csv                   # Logged sensor data
│
└── Task-5_Disaster-Alert-System/
    ├── main.py                                 # ESP32 disaster detection firmware
    ├── mpu6050.py                              # IMU/accelerometer driver
    ├── hcsr04.py                               # Ultrasonic sensor driver
    ├── ssd1306.py                              # OLED display driver
    ├── telegrambot.py                          # Python Telegram alert worker
    ├── diagram.json                            # Wokwi circuit diagram
    └── wokwi-project.txt                       # Wokwi project link
```

---

## 📝 Task 1 — Introduction to IoT & Device Communication

**Type:** Research & Presentation  
**File:** `Task-1_IoT-Presentation/1780053473844_Task-1-N_Abhiram.pdf`

A structured presentation covering the fundamentals of the Internet of Things ecosystem:

- What is IoT — definition, core pillars (smart sensors, connectivity, real-time communication, automation, data intelligence)
- IoT Architecture — 4-layer model: Device → Network → Cloud & Processing → Application
- Device Communication & Data Flow — sensor-to-cloud pipeline, bidirectional control, edge computing
- Real-World Applications — Smart Home, Healthcare, Industrial IoT, Smart Agriculture
- Smart Cities — traffic, surveillance, environment monitoring, smart waste management
- Key Benefits & Challenges — automation, efficiency vs. cybersecurity, scalability, power consumption
- Future Trends — AI-Powered IoT, Edge Computing, 5G, Digital Twins, Autonomous Systems

---

## 🔌 Task 2 — Multi-Sensor Node with Local OLED Dashboard

**Platform:** ESP32 + MicroPython (Wokwi Simulator)  
**Wokwi Project:** https://wokwi.com/projects/464472873812634625

### Hardware
| Component | Pin | Purpose |
|-----------|-----|---------|
| DHT22 | GPIO 15 | Temperature & Humidity |
| PIR Motion Sensor | GPIO 14 | Motion Detection |
| LDR Photoresistor | GPIO 34 (ADC) | Light Level (%) |
| SSD1306 OLED (128×64) | SDA: GPIO 21, SCL: GPIO 22 | Live Display |

### Features
- Real-time sensor readings every 2 seconds via SoftI2C
- OLED dashboard with structured UI: inverted header banner, data grid, dynamic footer
- Motion alert state — flashing banner when movement is detected
- Formatted serial terminal output with ASCII box-drawing characters

### OLED Display Layout
```
┌─────────────────┐
│ SENSOR READINGS │   ← Inverted header
├─────────────────┤
│ TEMP  : 24.0 C  │
│ HUMID : 55.0 %  │
│ LIGHT : 75.6 %  │
├─────────────────┤
│  SYSTEM SECURE  │   ← or !! MOTION ALERT !!
└─────────────────┘
```

---

## 📡 Task 3 — Multi-Sensor Node with MQTT Cloud + Streamlit Dashboard

**Platform:** ESP32 + MicroPython (Wokwi Simulator) + Python (PC)  
**Wokwi Project:** https://wokwi.com/projects/464567050018842625

### What's New vs Task 2
This task extends the same hardware with full cloud connectivity:
- ESP32 connects to WiFi (`Wokwi-GUEST`) and publishes sensor data as JSON over MQTT
- A Python Streamlit dashboard subscribes to the MQTT topic and visualizes live telemetry

### Hardware
Same as Task 2 — DHT22, PIR, LDR, SSD1306 OLED on ESP32.

### MQTT Configuration
| Parameter | Value |
|-----------|-------|
| Broker | `broker.hivemq.com` |
| Port | `1883` |
| Client ID | `abhiram_node_8829` |
| Topic | `decodelabs/abhiram/telemetry` |

### Streamlit Dashboard (`dashboard.py`)
A full-featured live IoT analytics dashboard built with Streamlit + Plotly:

- **KPI Cards** — Live temperature, humidity, light level, and motion event count
- **4 Charts** — Temperature, humidity, light intensity (area charts), motion detection (bar chart)
- **Security Alert Banner** — Red/green banner based on real-time motion state
- **Automated Intelligence** — Environmental health analysis and energy audit recommendations
- **Sidebar Controls** — Theme selector (Dark / Light / High Contrast), live update toggle, max data points slider, clear data button
- **Data Logging** — Readings auto-saved to `telemetry_history.csv`

### Running the Dashboard
```bash
pip install streamlit plotly paho-mqtt pandas numpy
streamlit run dashboard.py
```

### Telemetry Data Sample (`telemetry_history.csv`)
```
Timestamp,Temperature,Humidity,Light_Level,Motion
15:46:35,22.8,58.5,75.56,1
15:46:50,26.3,58.5,75.56,0
```

---

## 🚨 Task 5 — Multi-Hazard Disaster Alert System

**Platform:** ESP32 + MicroPython (Wokwi Simulator) + Python (PC)  
**Wokwi Project:** https://wokwi.com/projects/465239088687883265

### Hardware
| Component | Pin | Purpose |
|-----------|-----|---------|
| MPU6050 IMU | I2C (SDA: 21, SCL: 22) | Earthquake / Seismic Detection |
| HC-SR04 Ultrasonic | TRIG: GPIO 5, ECHO: GPIO 18 | Flood Level Detection |
| MQ-2 Gas Sensor | GPIO 34 (ADC) | Fire / Gas Detection |
| Buzzer | GPIO 15 | Audible Alert |
| Red LED | GPIO 2 | Alert Indicator |
| Green LED | GPIO 4 | Safe / Standby Indicator |

### Detection Thresholds
| Hazard | Sensor | Threshold |
|--------|--------|-----------|
| Earthquake | MPU6050 (acceleration magnitude) | > 12.0 m/s² |
| Flood | HC-SR04 (water distance) | < 15.0 cm |
| Fire / Gas | MQ-2 (ADC raw value) | > 2000 |

### System Architecture
```
ESP32 Node (Wokwi)
    │
    ├─ Reads MPU6050, HC-SR04, MQ-2 every 1s
    ├─ Triggers buzzer + red LED on any alert
    ├─ Publishes JSON payloads over MQTT
    │       ├─ my_custom_project_99/disaster/earthquake
    │       ├─ my_custom_project_99/disaster/flood
    │       ├─ my_custom_project_99/disaster/fire
    │       └─ my_custom_project_99/disaster/status
    │
MQTT Broker (broker.hivemq.com)
    │
telegrambot.py (runs on local machine / server)
    │
    └─ Sends formatted alerts to Telegram via Bot API
```

### Telegram Alert Format
```
⚠️ 🔴 EARTHQUAKE DETECTED!
📍 Location: Zone-1
📊 Magnitude: 14.32 m/s²
🕒 Time: 2026-05-29 10:45:00
```

### Running the Telegram Alert Worker
```bash
pip install paho-mqtt requests
python telegrambot.py
```

> ⚠️ **Security Note:** Replace `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `telegrambot.py` with your own credentials. Never commit real tokens to GitHub — use environment variables or a `.env` file.

---

## ⚙️ Running the Wokwi Simulations

1. Go to the Wokwi project URL listed under each task.
2. The `diagram.json` defines the circuit — components are pre-wired.
3. Click **▶ Start Simulation** to run `main.py` on the virtual ESP32.
4. Monitor sensor output in the **Serial Monitor** panel.

To run on real hardware, flash MicroPython onto an ESP32 and upload all `.py` files using [Thonny IDE](https://thonny.org/) or `mpremote`.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Microcontroller | ESP32 DevKit C v4 |
| Firmware | MicroPython v1.22 / v1.28 |
| Simulator | Wokwi |
| Cloud Broker | HiveMQ (`broker.hivemq.com`, port 1883) |
| Protocol | MQTT (`umqtt.simple`) |
| Dashboard | Python · Streamlit · Plotly |
| Notifications | Telegram Bot API |
| Buses | I2C (OLED, IMU) · ADC (LDR, Gas) · Digital GPIO (PIR, Ultrasonic, LEDs, Buzzer) |

---

## 📄 License

Developed as part of the **DecodeLabs Internship Program**.  
Free to use for educational and reference purposes.
