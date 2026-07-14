
import machine

"""
References:

MPU-6000 and MPU-6050 Product Specification
https://www.invensense.tdk.com/en-us/download-resource/ps-mpu-6000a-00-mpu-6000-and-mpu-6050-datasheet-0

The MPU-6000 and MPU-6050 Register Map and Descriptions Document
https://cdn.sparkfun.com/datasheets/Sensors/Accelerometers/RM-MPU-6000A.pdf

Existing drivers
https://github.com/OneMadGypsy/upy-motion/blob/main/mpu6050.py

https://stackoverflow.com/questions/60419390/mpu-6050-correctly-reading-data-from-the-fifo-register
"""

REG_PWR_MGMT_1 = 107
REG_WHO_AM_I = 117

CHIP_ID_MPU6500 = 0x70
CHIP_ID_MPU6050 = 0x68

class MPU6050():
    def __init__(self, i2c, addr=0x68):
        self.iic = i2c
        self.addr = addr

        # check that it is the right device
        chip_id = self.iic.readfrom_mem(self.addr, REG_WHO_AM_I, 1)[0]
        if chip_id not in (CHIP_ID_MPU6500, CHIP_ID_MPU6050):
            raise ValueError(f"Unknown chip ID: {hex(chip_id)}")

        # wakeup device 
        self.iic.writeto_mem(self.addr, REG_PWR_MGMT_1, b'\x00')

    def get_raw_values(self):
        a = self.iic.readfrom_mem(self.addr, 0x3B, 14)
        return a

    def bytes_toint(self, firstbyte, secondbyte):
        if not firstbyte & 0x80:
            return firstbyte << 8 | secondbyte
        return - (((firstbyte ^ 255) << 8) | (secondbyte ^ 255) + 1)

    def get_values(self):
        raw_ints = self.get_raw_values()
        vals = {}
        vals["AcX"] = self.bytes_toint(raw_ints[0], raw_ints[1])
        vals["AcY"] = self.bytes_toint(raw_ints[2], raw_ints[3])
        vals["AcZ"] = self.bytes_toint(raw_ints[4], raw_ints[5])
        vals["Tmp"] = self.bytes_toint(raw_ints[6], raw_ints[7]) / 340.00 + 36.53
        vals["GyX"] = self.bytes_toint(raw_ints[8], raw_ints[9])
        vals["GyY"] = self.bytes_toint(raw_ints[10], raw_ints[11])
        vals["GyZ"] = self.bytes_toint(raw_ints[12], raw_ints[13])
        return vals  # returned in range of Int16
