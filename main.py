import multiprocessing as mp
import time
import numpy as np
import cv2
import os

from matrix_driver import Matrix
from yt_processing import Ydl, YDL_OPTIONS, get_video_frames, delete_video

def video_finder(video_queue):
        ydl = Ydl(YDL_OPTIONS)
        while True:
            if video_queue.full():
                continue
            video = ydl.download_video(ydl.get_unwatched_video())
            if video is not None:
                video_queue.put(video)

def video_downloader(video_queue, frame_queue):
    while True:
        video = video_queue.get()
        frames = get_video_frames(video)
        delete_video(video)
        frame_queue.put(frames)

BLANK_FRAME = np.ones((48, 96, 3), dtype=np.uint8) * 255
STARTUP_FRAME = cv2.cvtColor(cv2.imread("/home/dietpi/yt-no-views-matrix/loading.png"), cv2.COLOR_BGR2RGB)
class App:
    def __init__(self, matrix):
        self.matrix = matrix

        m = mp.Manager()
        self.video_queue = m.Queue(maxsize=15)
        self.frame_queue = m.Queue(maxsize=3)
        self.video_finder_process = mp.Process(target=video_finder, args=(self.video_queue,))
        self.video_downloader_process = mp.Process(target=video_downloader, args=(self.video_queue, self.frame_queue))
        self.video_finder_process.start()
        self.video_downloader_process.start()

        self.matrix.set_pixels(BLANK_FRAME)
        self.matrix.reset()
        time.sleep(1)

        self.matrix.set_pixels(STARTUP_FRAME)
        time.sleep(4)

    def _get_buffered_videos(self):
        return self.video_queue.qsize() + self.frame_queue.qsize()

    def run(self):
        print("Waiting until 5 videos in queue")
        while self._get_buffered_videos() < 5:
            time.sleep(0.5)
        print("Found 5 videos, starting playback")
        while True:
            if self._get_buffered_videos() < 3:
                print("Running out of videos")
            frames = self.frame_queue.get()
            start_time = time.perf_counter()
            print("Playing new video")

            while True:
                frame_index = int((time.perf_counter() - start_time) * 30)
                if frame_index >= len(frames):
                    break
                frame = frames[frame_index]
                self.matrix.set_pixels(frame)

if __name__ == "__main__":
    app = App(Matrix((96, 48)))
    app.run()
