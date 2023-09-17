import eel
import numpy as np

class Matrix:
    def __init__(self, size, pitch=12.7, diameter=7.7):
        self.width = size[0]
        self.height = size[1]
        size = (self.width * pitch + diameter/2, self.height * pitch + 27 + diameter/2)
        eel.init('web')
        eel.start('index.html', size=size, block=False)
        eel.sleep(2)
        eel.init_matrix(self.width, self.height, pitch, diameter)

    def set_pixels(self, pixels):
        pass
        if type(pixels) is np.ndarray:
            pixels = pixels.tolist()
        
        if len(pixels) == self.height:
            pixels = [item for sublist in pixels for item in sublist]
            eel.set_pixels(pixels)
        elif len(pixels) == self.height * self.width:
            eel.set_pixels(pixels)
        else:
            raise ValueError('Pixels must be a 2D array of size height x width or a 1D array of size height * width')
