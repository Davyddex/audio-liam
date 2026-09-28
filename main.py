import numpy as np
import sounddevice as sd
import socket
import threading
import time
import struct
from matplotlib import pyplot as plt


if __name__ == '__main__':
    print(sd.query_devices())

audio = sd.rec(
    int(5*48000),
    samplerate=48000,
    channels=1,
    dtype="int16"
)
sd.wait()
#sd.play(audio, 48000)
#sd.wait()
print(audio.shape)

plt.plot(audio)
plt.show()

