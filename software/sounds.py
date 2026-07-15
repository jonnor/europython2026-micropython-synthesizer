
import time

from synthoor import Sound, GatedSound, Envelope, Oscillator, ButterFilter
import numpy as np

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

class Kick(GatedSound):
    def __init__(self,
                 amp_attack=0.001, amp_decay=0.3, amp_sustain=0.0, amp_release=0.01,
                 pitch_attack=0.001, pitch_decay=0.08, pitch_sustain=0.0, pitch_release=0.01,
                 start_freq=150, end_freq=50, **kwargs):
        super().__init__(**kwargs)
        
        self.env_amp = Envelope(amp_attack, amp_decay, amp_sustain, amp_release)
        self.env_pitch = Envelope(pitch_attack, pitch_decay, pitch_sustain, pitch_release)
        
        self.start_freq = start_freq
        self.end_freq = end_freq
        
        # XXX: using osc sine does not work when freq is below 200??
        self.osc0 = Oscillator('square')
        self.tone_filter = ButterFilter(btype='lowpass', db=36)
        

    def forward(self):
        g0 = self.gate()
        
        e_pitch = self.env_pitch(g0)
        freq = self.end_freq + e_pitch * (self.start_freq - self.end_freq)

        a0 = self.osc0(freq=freq)
        a0 = self.tone_filter(a0, freq=self.start_freq * 4.5)

        e_amp = self.env_amp(g0)
        
        return a0 * e_amp

    def _forward(self):
        g0 = self.gate()
        
        n0 = self.noise()
        n0 = self.filter(n0, freq=self.cutoff)
        e0 = self.env0(g0)
        
        return n0 * e0


class Hihat(GatedSound):
    def __init__(self,
                 attack=0.001, decay=0.05, sustain=0.0, release=0.01,
                 cutoff=7000, **kwargs):
        super().__init__(**kwargs)
        
        self.env0 = Envelope(attack, decay, sustain, release)
        self.noise = WhiteNoise()
        self.filter = ButterFilter(btype='highpass')
        self.cutoff = cutoff
        
    def forward(self):
        g0 = self.gate()
        
        n0 = self.noise()
        n0 = self.filter(n0, freq=self.cutoff)
        e0 = self.env0(g0)
        
        return n0 * e0

class Snare(GatedSound):
    def __init__(self,
                 tone_attack=0.001, tone_decay=0.1, tone_sustain=0.0, tone_release=0.01,
                 noise_attack=0.001, noise_decay=0.15, noise_sustain=0.0, noise_release=0.02,
                 tone_cutoff=180, noise_cutoff=2000, mix=0.35, **kwargs):
        super().__init__(**kwargs)
        
        self.env0 = Envelope(tone_attack, tone_decay, tone_sustain, tone_release)
        self.env1 = Envelope(noise_attack, noise_decay, noise_sustain, noise_release)
        
        self.osc0 = Oscillator('triangle')
        self.noise = WhiteNoise()
        
        self.tone_filter = ButterFilter(btype='lowpass')
        self.noise_filter = ButterFilter(btype='highpass')
        
        self.tone_cutoff = tone_cutoff
        self.noise_cutoff = noise_cutoff
        self.mix = mix
        
    def forward(self):
        try:
            return self._forward()
        except Exception as e:
            print('EE', e)

    def _forward(self):
        g0 = self.gate()
        
        a0 = self.osc0(freq=self.freq)
        a0 = self.tone_filter(a0, freq=self.tone_cutoff)
        e0 = self.env0(g0)
        
        n0 = self.noise()
        n0 = self.noise_filter(n0, freq=self.noise_cutoff)
        e1 = self.env1(g0)
        
        return a0 * e0 * self.mix + n0 * e1 * (1 - self.mix)
