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
            try:
                self.spi.writebytes2(data)
            except Exception as e:
                print(f"Error writing to SPI: {type(e).__name__}: {e}")
        else:
            print(f"Invalid pixel shape: {pixels.shape}, expected (48, 96, 3)")

    def reset(self):
        gpio.setmode(gpio.BCM)
        gpio.setup(self.reset_pin, gpio.OUT)
        gpio.output(self.reset_pin, gpio.LOW)
        time.sleep(0.1)
        gpio.output(self.reset_pin, gpio.HIGH)
        gpio.cleanup()
        time.sleep(0.5)

# import cv2
# class Matrix:
#     def __init__(self, size):
#         pass

#     def set_pixels(self, pixels):
#         pixels = cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
#         cv2.namedWindow("Matrix Emulator", cv2.WINDOW_NORMAL)
#         cv2.resizeWindow("Matrix Emulator", 750, 375)
#         cv2.imshow("Matrix Emulator", pixels)

#         if cv2.waitKey(1) & 0xFF == ord("q"):
#             cv2.destroyAllWindows()
#             exit(0)

#     def reset(self):
#         pass