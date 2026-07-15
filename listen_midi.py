
import mido
import time

import numpy as np

from synthoor import Sound, GatedSound, Envelope, Oscillator, ButterFilter
from sounds import Snare, Kick, Hihat

# MIDI listening logic
def listen_to_midi(port_name, synths : dict[int, (Sound, )]):

    with mido.open_input(port_name) as inport:

        last_check = time.time()
        while True:
            for msg in inport.iter_pending():  # non-blocking

                print(msg) # Print the received message

                if msg.type == 'note_on' and msg.velocity > 0:
                    print(f"Playing note: {msg.note}, velocity: {msg.velocity}")
                    # FIXME: avoid fixed duration

                    synth, duration = synths.get(msg.note, None)
                    if synth is None:
                        print('Unknown note', msg.note)

                    synth.play(note=msg.note, velocity=msg.velocity, duration=duration)

            if time.time() - last_check > 1.0:
                current_ports = set(mido.get_input_names())
                if port_name not in current_ports:
                    print("Device disconnected!")
                    break
                last_check = time.time()

            time.sleep(0.01)  # avoid busy-spinning the CPU

GM_NOTES = {
    'kick': 36,
    'snare': 38,
    'hihat': 42,
}

def test_sounds(drum_map):

    # 16th notes at ~120bpm (adjust to taste)
    step_duration = 0.25

    # 16-step pattern (1 bar of 16th notes)
    pattern = [
        ('kick',  [0, 4, 8, 12]),
        ('snare', [4, 12]),
        ('hihat', list(range(16))),   # every step
    ]

    for step in range(16):
        for name, steps in pattern:
            note = GM_NOTES[name]
            if step in steps:
                drum, duration = drum_map[note]
                drum.play(note=note, velocity=0x40, duration=duration)
        time.sleep(step_duration)

def main():

    target_port = "Board in FS mode:Board in FS mode MIDI 1 20:0"

    DRUM_MAP = {
        36: (Kick(), 80/1000),
        38: (Snare(), 100/1000),
        42: (Hihat(), 30/1000),
    }

    test_sounds(DRUM_MAP)
    print("DONE")

    return 

    while True:

        try:
            print("Checking...")
            available_ports = mido.get_input_names()
            if target_port in available_ports:

                print('Connect')
                listen_to_midi(target_port)

        except KeyboardInterrupt:
            print("Quit")
            break

        time.sleep(1.0)

if __name__ == '__main__':
    main()

