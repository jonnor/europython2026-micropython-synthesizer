
import math
import time
import array

import usb.device
from usb.device.midi import MIDIInterface

from recorder import Recorder
from process import Detector

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

        yield ax, ay, az

def main():

    detector = Detector()

    # Sanity check
    for mag, diff, ax, ay, az in read_accelerometer():
        print(mag, diff)
        break
    print("Check done. Entering MIDI mode soon")
    time.sleep_ms(1000)

    midi = MIDIExample()
    # Remove builtin_driver=True
    # if you don't want the MicroPython serial REPL available
    usb.device.get().init(midi, builtin_driver=True)

    print("Waiting for USB host to configure the interface...")

    start = time.time()
    max_start = 5.0
    while not midi.is_open():
        time.sleep_ms(100)
        since_start = time.time() - start
        if since_start > max_start:
            raise Exception(f"Start timeout {since_start}")

    print("Starting MIDI loop...")
    time.sleep_ms(1000)
    print("running...")

    # TX constants
    CHANNEL = 0
    PITCH = 60
    CONTROLLER = 64

    # TODO: add a way to change pitch

    control_val = 0

    file_duration = 5.0
    samplerate = 20.0
    data_dir = 'data'

    note_off_time = None

    print("foofo")
    while midi.is_open():

        with Recorder(samplerate, file_duration, directory=data_dir) as recorder:

            # UNCOMMENT to clean up data_dir
            #recorder.delete()

            recorder.start()

            decoded = array.array('h', [0, 0, 0]) # int16 samples

            for mag, diff, ax, ay, az in read_accelerometer():

                t = time.ticks_us()

                # TODO: compute velocity from magnitude/diff    
                # velocity =                 
                onset = detector.process(ax, ay, az)
                velocity = 0x40

                if diff > 300:
                    print(diff)

                if note_off_time is None:
                    # TODO: allow specifying onset threshold as control
                    # not inside a note
                    if onset > 0.9:
                        midi.note_on(CHANNEL, PITCH, velocity)
                        print('nON', CHANNEL, PITCH, velocity)
                        note_off_time = t + 20000

                # handle note off
                else:
                    # inside a note
                    if t >= note_off_time:
                        midi.note_off(CHANNEL, PITCH)
                        print('nOFF', CHANNEL, PITCH)
                        note_off_time = None

                # record data (if enabled)
                decoded[0] = ax
                decoded[1] = ay
                decoded[2] = az
                recorder.process(decoded)

                # FIXME: get rid of blocking sleep
                wait = 1.0 / samplerate
                time.sleep(wait)

    print("USB host has reset device, example done.")

if __name__ == '__main__':
    main()
