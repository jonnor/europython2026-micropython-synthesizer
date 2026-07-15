
import math
import time
import array
import asyncio

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


class AccelerometerReader:
    """
    Async iterator that sets up the MPU6050/6500 FIFO, checks FIFO periodically,
    and yields one sample tuple (ax, ay, az) at a time.
    """
    def __init__(self, samplerate=200, poll_interval=0.1, min_packets=4, max_packets=None):
        self.samplerate = samplerate
        self.poll_interval = poll_interval
        self.min_packets = min_packets
        self.max_packets = max_packets
 
        self.mpu = None
        self.buf = None
        self._pending = iter(())  # samples from the current buffer, not yet yielded
        self._started = False
 
    def _start(self):
        i2c = machine.I2C(sda=Pin(0), scl=Pin(1), freq=100_000)
        self.mpu = MPU6050(i2c, fifo_accel=True, fifo_gyro=False, fifo_temp=False)
        self.mpu.set_dlpf(3)  # enable DLPF -> 1kHz base rate
 
        actual_samplerate = self.mpu.set_sample_rate(self.samplerate)
        if actual_samplerate != self.samplerate:
            raise ValueError(f"Unable to use samplerate {self.samplerate}")
 
        self.mpu.fifo_enable(True)
 
        # buffer sized for the max number of packets we'll ever read at once
        max_buf_packets = self.max_packets if self.max_packets is not None else 512 // self.mpu.packet_size
        self.buf = bytearray(max_buf_packets * self.mpu.packet_size)
 
        self._started = True
 
    def __aiter__(self):
        return self
 
    async def __anext__(self):
        if not self._started:
            self._start()
 
        # drain whatever we already read before polling again
        for sample in self._pending:
            return sample
 
        while True:
            n_packets = self.mpu.get_fifo_count()
 
            if n_packets >= self.min_packets:
                if self.max_packets is not None:
                    n_packets = min(n_packets, self.max_packets)
 
                n_bytes = n_packets * self.mpu.packet_size
                view = memoryview(self.buf)[:n_bytes]
                self.mpu.read_samples_into(view)
 
                self._pending = self.mpu.parse_samples(view)
                for sample in self._pending:
                    return sample
 
            await asyncio.sleep(self.poll_interval)


async def main():

    time.sleep(0.5)

    detector = Detector()

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

    reader = AccelerometerReader(samplerate=200)

    while midi.is_open():

        with Recorder(samplerate, file_duration, directory=data_dir) as recorder:

            # UNCOMMENT to clean up data_dir
            #recorder.delete()

            #recorder.start()

            decoded = array.array('h', [0, 0, 0]) # int16 samples

            async for ax, ay, az in reader:

                t = time.ticks_us()

                onset = detector.process(ax, ay, az)
                # TODO: support velocity also
                velocity = 0x40

                #print(t, onset)

                if onset > 200:
                    print(onset)

                if note_off_time is None:
                    # TODO: allow specifying onset threshold as control
                    # not inside a note
                    if onset > 1000:
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


    print("USB host has reset device, example done.")

if __name__ == '__main__':
    asyncio.run(main())
