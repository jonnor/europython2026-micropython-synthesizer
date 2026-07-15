
# Benchmarking on RPI Pico RP2040

With plain Python IIR
```
mpremote run firmware/process.py
```

```
Warning: emlearn_iir did not import. Falling back to plain Python IIR filter (slower)
no module named 'emlearn_iir'
Processed 8626 samples (43.130s) in 60.214s
Analysis time: 15.701s | 1.820 ms/sample | 549.4 samples/s | 2.7x realtime
Wrote out.csv
```

With emlearn_iir

```
mpremote mip install https://emlearn.github.io/emlearn-micropython/builds/latest/armv6m_6.3/emlearn_iir.mpy
```

```
mpremote run firmware/process.py
```

```
mpremote run firmware/process.py
Processed 8626 samples (43.130s) in 52.733s
Analysis time: 8.388s | 0.972 ms/sample | 1028.4 samples/s | 5.1x realtime
Wrote out.csv
```
