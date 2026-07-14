# MIT license; Copyright (c) 2023-2024 Angus Gratton
import usb.device
from usb.device.midi import MIDIInterface
import time

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


m = MIDIExample()
# Remove builtin_driver=True if you don't want the MicroPython serial REPL available.
usb.device.get().init(m, builtin_driver=True)

print("Waiting for USB host to configure the interface...")

while not m.is_open():
    time.sleep_ms(100)

print("Starting MIDI loop...")

# TX constants
CHANNEL = 0
PITCH = 60
CONTROLLER = 64

control_val = 0

while m.is_open():
    time.sleep(1)
    print(f"TX Note On channel {CHANNEL} pitch {PITCH}")
    m.note_on(CHANNEL, PITCH)  # Velocity is an optional third argument
    time.sleep(0.5)
    print(f"TX Note Off channel {CHANNEL} pitch {PITCH}")
    m.note_off(CHANNEL, PITCH)
    time.sleep(1)
    print(f"TX Control channel {CHANNEL} controller {CONTROLLER} value {control_val}")
    m.control_change(CHANNEL, CONTROLLER, control_val)
    control_val += 1
    if control_val == 0x7F:
        control_val = 0
    time.sleep(1)

print("USB host has reset device, example done.")
