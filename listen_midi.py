
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
    try:
        with mido.open_input(port_name) as inport:
            print(f"Listening for MIDI messages on {port_name}...")
            for msg in inport:
                print(msg) # Print the received message
                if msg.type == 'note_on' and msg.velocity > 0:

                    print(f"Playing note: {msg.note}, velocity: {msg.velocity}")
                    synth.play(note=msg.note/3, velocity=msg.velocity, duration=1) # Fixed 0.5 second duration
    except OSError as e:
        print(f"Error opening MIDI port '{port_name}': {e}")
        print("Please ensure the MIDI device is connected and the port name is correct.")
        print("Available ports:", mido.get_input_names())
    except KeyboardInterrupt:
        print("\nStopping MIDI listener.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

available_ports = mido.get_input_names()
target_port = "Board in FS mode:Board in FS mode MIDI 1 20:0"
listen_to_midi(target_port)
