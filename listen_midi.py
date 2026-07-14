
import mido
import time

from synthoor import GatedSound, Envelope, Oscillator, ButterFilter

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


synth = TB303()

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
                    synth.play(note=msg.note/3, velocity=msg.velocity, duration=1)

            if time.time() - last_check > 1.0:
                current_ports = set(mido.get_input_names())
                if port_name not in current_ports:
                    print("Device disconnected!")
                    break
                last_check = time.time()

            time.sleep(0.01)  # avoid busy-spinning the CPU


def main():

    target_port = "Board in FS mode:Board in FS mode MIDI 1 20:0"

    # FIXME: handle device disconnect and reconnect
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

