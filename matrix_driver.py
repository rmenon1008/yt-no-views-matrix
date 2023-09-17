import cv2
import numpy as np
import spidev

class Matrix:
    def __init__(self, _):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 1)
        self.spi.no_cs = True
        self.spi.mode = 0b11
        self.spi.max_speed_hz = 16_000_000

        print("Initializing matrix...")

    def __del__(self):
        self.spi.close()

    def set_pixels(self, pixels):
        data = pixels.tobytes()
        self.spi.xfer3(data)
