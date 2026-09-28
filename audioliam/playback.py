import numpy as np
import sounddevice as sd
import socket
import threading
import time
import struct
from config import *


def callback(outdata, frames, time_info, status):
    if status:
        print(status)


    t = np.arange(frames)

    outdata[:, 0] = 0 * t

def end_output():
    pass

with sd.OutputStream(SAMPLE_RATE,
    # device=,
    blocksize=BLOCK_SIZE,
    channels=1,
    dtype="float32",
    # latency=100,
    callback=callback,
    finished_callback=end_output
):
    print("start")
    input()

