import machine
"""
References:
MPU-6000 and MPU-6050 Product Specification
https://www.invensense.tdk.com/en-us/download-resource/ps-mpu-6000a-00-mpu-6000-and-mpu-6050-datasheet-0
The MPU-6000 and MPU-6050 Register Map and Descriptions Document
https://cdn.sparkfun.com/datasheets/Sensors/Accelerometers/RM-MPU-6000A.pdf
MPU-6500 Register Map and Descriptions (RM-MPU-6500A-00)
Existing drivers
https://github.com/OneMadGypsy/upy-motion/blob/main/mpu6050.py
https://stackoverflow.com/questions/60419390/mpu-6050-correctly-reading-data-from-the-fifo-register
"""

REG_SMPLRT_DIV = 0x19
REG_CONFIG = 0x1A
REG_GYRO_CONFIG = 0x1B
REG_ACCEL_CONFIG = 0x1C
REG_FIFO_EN = 0x23
REG_INT_ENABLE = 0x38
REG_ACCEL_XOUT_H = 0x3B
REG_USER_CTRL = 0x6A
REG_PWR_MGMT_1 = 0x6B
REG_FIFO_COUNT_H = 0x72
REG_FIFO_COUNT_L = 0x73
REG_FIFO_R_W = 0x74
REG_WHO_AM_I = 0x75  # note: 0x75 on MPU6500, 0x75 on MPU6050 too (117 dec)

CHIP_ID_MPU6500 = 0x70
CHIP_ID_MPU6050 = 0x68

# FIFO_EN bitfield (Register 35)
TEMP_FIFO_EN = 1 << 7
XG_FIFO_EN = 1 << 6
YG_FIFO_EN = 1 << 5
ZG_FIFO_EN = 1 << 4
ACCEL_FIFO_EN = 1 << 3

GYRO_FIFO_EN = XG_FIFO_EN | YG_FIFO_EN | ZG_FIFO_EN

# USER_CTRL bits (Register 106)
FIFO_EN_BIT = 1 << 6
FIFO_RST_BIT = 1 << 2

# bytes per enabled channel in a FIFO packet, in the fixed order
# accel(6) -> temp(2) -> gyro X/Y/Z(2 each)
ACCEL_BYTES = 6
TEMP_BYTES = 2
GYRO_BYTES = 6  # X+Y+Z


class MPU6050():
    def __init__(self, i2c, addr=0x68, fifo_gyro=True, fifo_accel=True, fifo_temp=False):
        self.iic = i2c
        self.addr = addr

        # check that it is the right device
        chip_id = self.iic.readfrom_mem(self.addr, REG_WHO_AM_I, 1)[0]
        if chip_id not in (CHIP_ID_MPU6500, CHIP_ID_MPU6050):
            raise ValueError(f"Unknown chip ID: {hex(chip_id)}")

        # wakeup device
        self.iic.writeto_mem(self.addr, REG_PWR_MGMT_1, b'\x00')

        # remember which channels go into the FIFO, and thus how to parse it
        self.fifo_accel = fifo_accel
        self.fifo_temp = fifo_temp
        self.fifo_gyro = fifo_gyro
        self._packet_size = (ACCEL_BYTES if fifo_accel else 0) \
            + (TEMP_BYTES if fifo_temp else 0) \
            + (GYRO_BYTES if fifo_gyro else 0)

    def read_register(self, reg):
        data = self.iic.readfrom_mem(self.addr, reg, 1)
        return data[0]

    def write_register(self, reg, value):
        self.iic.writeto_mem(self.addr, reg, bytes((value,)))

    def get_raw_values(self):
        a = self.iic.readfrom_mem(self.addr, REG_ACCEL_XOUT_H, 14)
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

    # ---------------- FIFO API (mirrors the LIS3DH-style driver) ----------------

    def set_dlpf(self, dlpf_cfg):
        """dlpf_cfg: 0..6, see CONFIG register / DLPF_CFG table in datasheet"""
        value = self.read_register(REG_CONFIG)
        value = (value & ~0x07) | (dlpf_cfg & 0x07)
        self.write_register(REG_CONFIG, value)
        self._dlpf_cfg = dlpf_cfg & 0x07

    def set_sample_rate(self, rate_hz):
        """
        Set the sample rate in Hz (applies to both accel and gyro, and thus
        the rate at which data is pushed into the FIFO).

        Internally this is Gyro_output_rate / (1 + SMPLRT_DIV), where
        Gyro_output_rate is 8kHz with the DLPF disabled (dlpf_cfg 0 or 7)
        or 1kHz with the DLPF enabled (dlpf_cfg 1-6). Call set_dlpf() first
        if you want the 1kHz base rate; default DLPF state gives 8kHz.
        Actual rate is rounded to the nearest achievable value and returned.
        """
        base_rate = 1000 if getattr(self, "_dlpf_cfg", 0) in range(1, 7) else 8000

        divider = round(base_rate / rate_hz) - 1
        divider = max(0, min(255, divider))
        self.write_register(REG_SMPLRT_DIV, divider)

        actual_rate_hz = base_rate / (1 + divider)
        return actual_rate_hz

    @property
    def packet_size(self):
        """Size in bytes of one FIFO sample packet, given the enabled channels"""
        return self._packet_size

    def fifo_enable(self, enable):
        if enable:
            if self._packet_size == 0:
                raise ValueError("At least one of fifo_accel/fifo_gyro/fifo_temp must be enabled")

            # reset FIFO (also clears any stale data)
            user_ctrl = self.read_register(REG_USER_CTRL)
            self.write_register(REG_USER_CTRL, user_ctrl | FIFO_RST_BIT)

            # select which sensor data is written into the FIFO
            fifo_en = 0
            if self.fifo_accel:
                fifo_en |= ACCEL_FIFO_EN
            if self.fifo_temp:
                fifo_en |= TEMP_FIFO_EN
            if self.fifo_gyro:
                fifo_en |= GYRO_FIFO_EN
            self.write_register(REG_FIFO_EN, fifo_en)

            # enable the FIFO itself
            user_ctrl = self.read_register(REG_USER_CTRL)
            self.write_register(REG_USER_CTRL, user_ctrl | FIFO_EN_BIT)
        else:
            self.write_register(REG_FIFO_EN, 0x00)
            user_ctrl = self.read_register(REG_USER_CTRL)
            self.write_register(REG_USER_CTRL, user_ctrl & ~FIFO_EN_BIT)

    def get_fifo_count(self):
        """
        Return the number of complete sample packets ready in the FIFO.
        Any trailing partial packet (from a read mid-write) is ignored.
        """
        data = self.iic.readfrom_mem(self.addr, REG_FIFO_COUNT_H, 2)
        byte_count = (data[0] << 8) | data[1]
        return byte_count // self._packet_size

    def read_samples_into(self, buf):
        """
        Read raw FIFO sample packets into buf.

        buf length must be a multiple of self.packet_size. Each packet is
        laid out as: [accel_x,y,z (if enabled)][temp (if enabled)]
        [gyro_x,y,z (if enabled)], each field big-endian int16, matching
        the FIFO_EN configuration used in fifo_enable().

        NOTE: caller is responsible for ensuring that enough samples are
        ready, typically by calling get_fifo_count() first.
        """
        n_bytes = len(buf)
        if self._packet_size == 0:
            raise ValueError("FIFO not configured, call fifo_enable(True) first")
        if (n_bytes % self._packet_size) != 0:
            raise ValueError(f"Buffer should be a multiple of {self._packet_size}")

        self.iic.readfrom_mem_into(self.addr, REG_FIFO_R_W, buf)

    def parse_samples(self, buf):
        """
        Parse a buffer (as filled by read_samples_into) and yield one tuple
        per sample packet. Fields present depend on which channels are
        enabled, always in this order: (ax, ay, az, temp, gx, gy, gz).
        Temperature, if present, is raw (not converted to degrees C).
 
        This is a generator - iterate over it, or wrap in list()/tuple()
        if you need random access or len().
        """
        ps = self._packet_size
        n_bytes = len(buf)
        if (n_bytes % ps) != 0:
            raise ValueError(f"Buffer should be a multiple of {ps}")
 
        fmt = ""
        if self.fifo_accel:
            fmt += "3h"
        if self.fifo_temp:
            fmt += "h"
        if self.fifo_gyro:
            fmt += "3h"
        fmt = ">" + fmt
 
        for i in range(0, n_bytes, ps):
            yield struct.unpack_from(fmt, buf, i)

