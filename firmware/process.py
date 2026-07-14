
import math
import os
import array

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

        print('env alpha', self.env_alpha)

        lowpass = butter2_lowpass(f=gravity_cutoff, sr=samplerate)
        self.gravity_filter = GravityEstimatorLowpass(lowpass)

    def process(self, ax, ay, az):

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

        # Compute overall motion magnitude
        mag = math.sqrt((mx*mx) + (my*my) + (mz*mz))

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
            self.env = self.env + self.env_alpha * (mag - self.env)  

        # TODO: return velocity also

        onset = self.env
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

    detector = Detector(samplerate=20)

    data_dir = 'data1/data/'
    out_path = 'out.csv'

    sample_idx = 0
    with open(out_path, 'w') as f:

        writer = DictWriter(f, fieldnames=['sample', 'acc_x', 'acc_y', 'acc_z', 'onset'])
        writer.writeheader()

        for ax, ay, az in read_recording(data_dir):

            onset = detector.process(ax, ay, az)
            d = dict(sample=sample_idx, acc_x=ax, acc_y=ay, acc_z=az, onset=onset)
            writer.writerow(d)
            sample_idx += 1

    print('Wrote', out_path, sample_idx)

if __name__ == '__main__':
    main()
