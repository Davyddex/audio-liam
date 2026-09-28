import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd

import socket
import threading
import time
import struct
from config import *

r = []


def callback(indata, frames, time, status):
    if status:
        print(status)

    r.append(indata[:, 0])


def end_input():
    pass


with sd.InputStream(samplerate=SAMPLE_RATE,
    # device=,
    blocksize=BLOCK_SIZE,
    channels=1,
    dtype="int16",
    # latency=100,
    callback=callback,
    finished_callback=end_input,
):
    time.sleep(0.5)

r = np.concatenate(r)
plt.plot(np.arange(r.shape[0])*0.5/BLOCK_SIZE, r)
plt.show()
