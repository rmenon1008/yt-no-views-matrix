import cv2
import numpy as np
import spidev
import RPi.GPIO as gpio
import time

class Matrix:
    def __init__(self, _):
        self.reset_pin = 14

        self.spi = spidev.SpiDev()
        self.spi.open(0, 1)
        self.spi.no_cs = True
        self.spi.mode = 0b11
        self.spi.max_speed_hz = 16_000_000

        self.reset()
        print("Initializing matrix...")

    def __del__(self):
        self.spi.close()
        self.reset()

    def set_pixels(self, pixels):
        if pixels.shape == (48, 96, 3):
            data = pixels.tobytes()
            self.spi.writebytes2(data)

    def reset(self):
        gpio.setmode(gpio.BCM)
        gpio.setup(self.reset_pin, gpio.OUT)
        gpio.output(self.reset_pin, gpio.LOW)
        time.sleep(0.1)
        gpio.output(self.reset_pin, gpio.HIGH)
        gpio.cleanup()
        time.sleep(0.5)
