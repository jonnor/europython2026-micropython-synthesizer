
import mido
import time

import numpy as np

from synthoor import Sound, GatedSound, Envelope, Oscillator, ButterFilter

# https://github.com/Sangarshanan/synthoor/blob/main/tutorial/5.ipynb
class TB303(GatedSound):

    def __init__(self):

        super().__init__()
        
        # Two Envelopes
        self.env0 = Envelope(
            0.05, 0, 1, 0.01
        )
        self.env1 = Envelope(
            0, 1, 0, 0,
        linear=False)

        self.osc0 = Oscillator('saw')

        self.filter = ButterFilter(btype='lowpass')

    def forward(self):

        g0 = self.gate()

        e0 = self.env0(g0)
        e1 = self.env1(g0, decay=1) * 12 * 10

        a0 = self.osc0(freq=self.freq)

        a1 = self.filter(
            a0,
            key_modulation=e1,
            freq=self.freq,
        )

        return a1 * e0

class WhiteNoise(Sound):
    """White noise generator.
    Note:
        A WhiteNoise inherits all the methods and properties of a Sound class.
    """
    def __init__(self, **kwargs):
        """"""
        super().__init__(**kwargs)
    def forward(self, **kwargs):
        a0 = np.random.uniform(-1, 1, self.frames)
        return a0[:, None]

class SubtractiveDrum(GatedSound):
    def __init__(self):
        super().__init__()
        
        self.env0 = Envelope(0.001, 0, 1, 0.05)   # tone envelope, fast decay
        self.env1 = Envelope(0.001, 0, 1, 0.15)   # noise envelope, slightly longer
        
        self.osc0 = Oscillator('saw')
        self.noise = WhiteNoise()
        
        self.tone_filter = ButterFilter(btype='lowpass')
        self.noise_filter = ButterFilter(btype='highpass')
        
    def forward(self):
        g0 = self.gate()
        
        # Tonal component (the "body")
        a0 = self.osc0(freq=self.freq)
        a0 = self.tone_filter(a0, freq=200)
        e0 = self.env0(g0)
        
        # Noise component (the "snap")
        n0 = self.noise()
        n0 = self.noise_filter(n0, freq=1500)
        e1 = self.env1(g0)
        
        return a0 * e0 * 0.5 + n0 * e1 * 0.5


synth = SubtractiveDrum()

# MIDI listening logic
def listen_to_midi(port_name):

    with mido.open_input(port_name) as inport:

        last_check = time.time()
        while True:
            for msg in inport.iter_pending():  # non-blocking

                print(msg) # Print the received message

                if msg.type == 'note_on' and msg.velocity > 0:
                    print(f"Playing note: {msg.note}, velocity: {msg.velocity}")
                    # FIXME: avoid fixed duration
                    synth.play(note=msg.note, velocity=msg.velocity, duration=0.1)

            if time.time() - last_check > 1.0:
                current_ports = set(mido.get_input_names())
                if port_name not in current_ports:
                    print("Device disconnected!")
                    break
                last_check = time.time()

            time.sleep(0.01)  # avoid busy-spinning the CPU


def main():

    target_port = "Board in FS mode:Board in FS mode MIDI 1 20:0"


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

