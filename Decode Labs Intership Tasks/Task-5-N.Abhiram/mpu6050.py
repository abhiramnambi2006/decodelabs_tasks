import machine

class MPU6050:
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        # Wake up the sensor
        self.i2c.writeto_mem(self.addr, 0x6B, b'\x00')

    @property
    def acceleration(self):
        # Read 6 bytes of accelerometer data
        data = self.i2c.readfrom_mem(self.addr, 0x3B, 6)
        
        def combine_bytes(high, low):
            val = (high << 8) | low
            return val if val < 32768 else val - 65536
            
        # Convert raw data to m/s^2 (Assuming +/- 2g range: 16384 LSB/g)
        ax = (combine_bytes(data[0], data[1]) / 16384.0) * 9.81
        ay = (combine_bytes(data[2], data[3]) / 16384.0) * 9.81
        az = (combine_bytes(data[4], data[5]) / 16384.0) * 9.81
        
        return (ax, ay, az)