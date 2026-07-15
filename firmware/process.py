
import math
import os
import array
import time

from csv import DictWriter

# https://stackoverflow.com/a/20932062
def butter2_lowpass(f, sr):
    ff = f / sr
    ita = 1.0/ math.tan(math.pi*ff)
    q = math.sqrt(2.0)
    b0 = 1.0 / (1.0 + q*ita + ita*ita)
    b1 = 2 * b0
    b2 = b0
    a1 = 2.0 * (ita*ita - 1.0) * b0
    a2 = -(1.0 - q*ita + ita*ita) * b0

    # Return in biquad / Second Order Stage format
    # to be compatible with scipy, a1 and a2 needed to be flipped??
    sos = [ b0, b1, b2, 1.0, -a1, -a2 ]

    return sos

class IIRFilter():
    """
    Plain MicroPython version of an IIR filter.
    Using cascaded second-order biquads (SOS).

    API compatible with emlearn_iir (implemented in C, faster).
    """
    def __init__(self, coefficients : array.array):
        stages = len(coefficients)//6

        self.sos = coefficients
        self.state = array.array('f', [0.0]*(2*stages))

    @micropython.native
    def run(self, samples : array.array):
        """Filter incoming data with cascaded second-order sections.
        """

        stages = len(self.sos)//6

        # iterate over all samples
        for i in range(len(samples)):
            x = samples[i]

            # apply all filter sections
            for s in range(stages):
                b0, b1, b2, a0, a1, a2 = self.sos[s*6:(s*6)+6]

                # compute difference equations of transposed direct form II
                y = b0*x + self.state[(s*2)+0]
                self.state[(s*2)+0] = b1*x - a1*y + self.state[(s*2)+1]
                self.state[(s*2)+1] = b2*x - a2*y
                # set biquad output as input of next filter section
                x = y

            # assign to output
            samples[i] = x

        return None

class GravityEstimatorLowpass:
    """Estimate gravity vector from IMU data using a low-pass filter"""
    
    def __init__(self, coefficients : array.array):
        """
        """
        self.gravity = array.array('f', [0.0, 0.0, 0.0])

        IIR = IIRFilter
        emlearn_iir = None
        try:
            import emlearn_iir
            IIR = emlearn_iir.new
        except ImportError as e:
            print("Warning: emlearn_iir did not import. Falling back to plain Python IIR filter (slower)")
            print(e)

        # one filter per XYZ axis
        self.filters = [ IIR(coefficients) for i in range(3) ]

        self.temp = array.array('f', [0.0])


    def update(self, accel : array.array):
        """
        accel: Accelerometer raw data [ax, ay, az]

        Returns: estimated gravity vector - in same unit as input
        """

        if len(accel) % 3 != 0:
            raise ValueError("Input must have 3 columns")

        # Buffer for deinterleaved data
        n_samples = len(accel) // 3

        # Deinterleave and run IIR filter sample-by-sample
        # NOTE: emlearn_iir can take an array of samples as input,
        # but when we would have to deinterleave temporary array anyway
        arr = self.temp
        for axis in range(0, 3):
            filter_func = self.filters[axis].run
            for sample in range(n_samples):
                index = (sample*3)+axis
                arr[0] = accel[index]
                out = filter_func(arr)
                self.gravity[axis] = arr[0]

        return self.gravity


def compute_alpha(time_const: float, samplerate: float) -> float:
    dt = 1.0 / samplerate
    tau = time_const
    alpha = 1.0 - math.exp(-dt / tau)
    return min(1.0, max(0.0, alpha))

class Detector:

    def __init__(self, samplerate : int, gravity_cutoff=0.5, attack_ms=2.0):
        self.mag = None
        self.env = None

        self.env_alpha = compute_alpha(attack_ms/1000.0, samplerate)
        assert self.env_alpha < 1.0, (self.env_alpha, attack_ms, samplerate)

        lowpass = butter2_lowpass(f=gravity_cutoff, sr=samplerate)
        coeff = array.array('f', lowpass)
        self.gravity_filter = GravityEstimatorLowpass(coeff)

    def process(self, ax, ay, az):

        # Estimate gravity vector / orientation
        gravity_start = time.ticks_us()
        gravity = self.gravity_filter.update(array.array('f', [ax, ay, az]))

        # Isolate motion by subtracting gravity vector
        if True:
            mx = ax - gravity[0]
            my = ay - gravity[1]
            mz = az - gravity[2]
        else:
            mx = ax
            mx = ay
            mx = az
        gravity_duration = time.ticks_diff(time.ticks_us(), gravity_start)

        # Compute overall motion magnitude
        metrics_start = time.ticks_us()
        mag = math.sqrt((mx*mx) + (my*my) + (mz*mz))

        # Scale from int16 range to 1.0 scaled floats
        mag = mag / 2**15

        #print(mag)

        # Compute jerk and envelope
        jerk = 0.0
        env = 0.0
        if self.mag is None:
            # first sample
            self.mag = mag
            self.env = env
        else:
            self.mag = mag - self.mag
            env = self.env + self.env_alpha * (mag - self.env)  
            jerk = env - self.env 
            self.env = env

        pos_jerk = max(jerk, 0)
        # trigger only if there is a large value AND a large change
        onset = pos_jerk * self.env
        metrics_duration = time.ticks_diff(time.ticks_us(), metrics_start)

        return onset

def read_recording(data_dir):

    import npyfile
    filenames = sorted(os.listdir(data_dir))
    for f in filenames:
        path = data_dir + f

        with npyfile.Reader(path) as reader:
            # data should be 3-axis acceleration X time
            assert len(reader.shape) == 2, reader.shape
            n_samples, n_columns = reader.shape
            assert n_columns == 3, reader.shape
            for chunk in reader.read_data_chunks(n_columns):
                ax, ay, az = chunk
                yield ax, ay, az

def main():

    samplerate  = 200

    data_dir = 'data2/data/'
    data_dir = 'data/'
    out_path = 'out.csv'

    process_start = time.ticks_ms()
    process_only_time_ms = 0.0
    detector = Detector(samplerate=samplerate, attack_ms=4.0)
    sample_idx = 0
    with open(out_path, 'w') as f:

        writer = DictWriter(f, fieldnames=['t', 'acc_x', 'acc_y', 'acc_z', 'onset'])
        writer.writeheader()

        # TODO: track read and write times also
        for ax, ay, az in read_recording(data_dir):

            detect_start = time.ticks_us()
            onset = detector.process(ax, ay, az)
            t = sample_idx * (1.0/samplerate)
            detect_duration = time.ticks_diff(time.ticks_us(), detect_start)

            process_only_time_ms += (detect_duration/1000.0)

            # Write output
            d = dict(acc_x=ax, acc_y=ay, acc_z=az, onset=onset, t=t)
            writer.writerow(d)
            sample_idx += 1

    data_duration = (sample_idx / samplerate)
    total_duration = time.ticks_diff(time.ticks_ms(), process_start) / 1000.0

    process_duration = process_only_time_ms/1000.0
    realtime_factor = data_duration / process_duration

    per_sample_ms = (process_duration / sample_idx)*1000
    print(f'Processed {sample_idx} samples ({data_duration:.3f}s) in {total_duration:.3f}s')
    print(f'Analysis time: {process_duration:.3f}s | {per_sample_ms:.3f} ms/sample | {sample_idx/process_duration:.1f} samples/s | {realtime_factor:.1f}x realtime')

    print('Wrote', out_path)

if __name__ == '__main__':
    main()
