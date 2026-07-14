
import math
import os

from csv import DictWriter

class Detector:

    def __init__(self, ):
        self.prev = None

    def process(self, ax, ay, az):

        mag = math.sqrt((ax*ax) + (ay*ay) + (az*az))

        if self.prev is None:
            # first sample
            self.prev = mag
            return 0.0
        else:
            diff = mag - self.prev
            onset = diff
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

    detector = Detector()

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
