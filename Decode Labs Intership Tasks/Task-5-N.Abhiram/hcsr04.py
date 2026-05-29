import machine
import time

class HCSR04:
    def __init__(self, trigger_pin, echo_pin):
        self.trigger = machine.Pin(trigger_pin, machine.Pin.OUT)
        self.echo = machine.Pin(echo_pin, machine.Pin.IN)

    def distance_cm(self):
        # Send a 10us pulse to trigger
        self.trigger.value(0)
        time.sleep_us(5)
        self.trigger.value(1)
        time.sleep_us(10)
        self.trigger.value(0)
        
        try:
            # Measure echo pulse duration, timeout after 30ms
            pulse_time = machine.time_pulse_us(self.echo, 1, 30000)
            if pulse_time < 0:
                return 999.0 # Timeout error handling
            # Sound travels at 343 m/s. Formula: (time / 2) / 29.1
            return (pulse_time / 2) / 29.1
        except OSError:
            return 999.0 # Sensor reading error