
import math
import time

import usb.device
from usb.device.midi import MIDIInterface

# Example
# https://github.com/micropython/micropython-lib/blob/master/micropython/usb/examples/device/midi_example.py
# https://github.com/micropython/micropython-lib/blob/master/micropython/usb/usb-device-midi/usb/device/midi.py

class MIDIExample(MIDIInterface):
    # Very simple example event handler functions, showing how to receive note
    # and control change messages sent from the host to the device.
    #
    # If you need to send MIDI data to the host, then it's fine to instantiate
    # MIDIInterface class directly.

    def on_open(self):
        super().on_open()
        print("Device opened by host")

    def on_note_on(self, channel, pitch, vel):
        print(f"RX Note On channel {channel} pitch {pitch} velocity {vel}")

    def on_note_off(self, channel, pitch, vel):
        print(f"RX Note Off channel {channel} pitch {pitch} velocity {vel}")

    def on_control_change(self, channel, controller, value):
        print(f"RX Control channel {channel} controller {controller} value {value}")


from mpu6050 import MPU6050
from machine import Pin
import machine


def read_accelerometer():

    i2c = machine.I2C(sda=Pin(0), scl=Pin(1), freq=100_000)
    mpu = MPU6050(i2c)
    print('Accelerometer started')

    prev = None
    while True:

        v = mpu.get_values()
        ax = v['AcX']
        ay = v['AcY']
        az = v['AcZ']

        mag = math.sqrt((ax*ax) + (ay*ay) + (az*az))

        if prev is None:
            # first sample
            prev = mag
        else:
            diff = mag - prev
            yield mag, diff

        # FIXME: get rid of blocking sleep
        time.sleep(0.05)

def main():

    # Sanity check
    for mag, diff in read_accelerometer():
        print(mag, diff)
        break
    print("Check done. Entering MIDI mode soon")
    time.sleep_ms(1000)

    m = MIDIExample()
    # Remove builtin_driver=True
    # if you don't want the MicroPython serial REPL available
    usb.device.get().init(m, builtin_driver=True)

    print("Waiting for USB host to configure the interface...")

    while not m.is_open():
        time.sleep_ms(100)

    print("Starting MIDI loop...")

    # TX constants
    CHANNEL = 0
    PITCH = 60
    CONTROLLER = 64

    # TODO: add a way to change pitch

    control_val = 0

    while m.is_open():

        for mag, diff in read_accelerometer():

            print(diff)
            if diff > 1000:
    
                # FIXME: keep track of note state without time.sleep
                velocity = 0x40
                print(f"TX Note On channel {CHANNEL} pitch {PITCH}")
                m.note_on(CHANNEL, PITCH, velocity)
                time.sleep(0.01)
                m.note_off(CHANNEL, PITCH)


    print("USB host has reset device, example done.")

if __name__ == '__main__':
    main()
