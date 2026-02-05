import multiprocessing as mp
import time
import numpy as np
import cv2
import os

from matrix_driver import Matrix
from yt_processing import Ydl, YDL_OPTIONS, iter_video_frames, delete_video

def video_finder(video_queue):
        ydl = Ydl(YDL_OPTIONS)
        while True:
            if video_queue.full():
                time.sleep(0.05)
                continue
            video = ydl.download_video(ydl.get_unwatched_video())
            if video is not None:
                video_queue.put(video)

BLANK_FRAME = np.ones((48, 96, 3), dtype=np.uint8) * 255
STARTUP_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "loading.png")
STARTUP_FRAME = cv2.cvtColor(cv2.imread(STARTUP_IMAGE_PATH), cv2.COLOR_BGR2RGB)
class App:
    def __init__(self, matrix):
        self.matrix = matrix

        # NOTE: Keep large frame data in-process; only pass small messages (file paths) across processes.
        self.video_queue = mp.Queue(maxsize=10)
        self.video_finder_process = mp.Process(target=video_finder, args=(self.video_queue,))
        self.video_finder_process.start()

        self.matrix.set_pixels(BLANK_FRAME)
        self.matrix.reset()
        time.sleep(1)

        self.matrix.set_pixels(STARTUP_FRAME)
        time.sleep(4)

    def _get_buffered_videos(self):
        try:
            return self.video_queue.qsize()
        except NotImplementedError:
            # Some platforms don't implement qsize() for multiprocessing.Queue
            return 0

    def run(self):
        print("Waiting for first downloaded video...")
        while True:
            if self._get_buffered_videos() < 2:
                print("Running out of videos")
            video_file = self.video_queue.get()
            print(f"Playing new video: {video_file}")

            try:
                # Pace playback to the video's real timestamps/FPS.
                for frame in iter_video_frames(video_file, resolution=(96, 48)):
                    self.matrix.set_pixels(frame)
            finally:
                delete_video(video_file)

if __name__ == "__main__":
    print("Starting up...")
    app = App(Matrix((96, 48)))
    app.run()
