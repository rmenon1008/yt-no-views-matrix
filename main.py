import multiprocessing as mp
import time

from matrix_driver import Matrix
from yt_processing import Ydl, YDL_OPTIONS, get_video_frames, delete_video

def video_finder(video_queue):
        ydl = Ydl(YDL_OPTIONS)
        while True:
            if video_queue.full():
                continue
            video_queue.put(
                ydl.download_video(ydl.get_unwatched_video())
            )

def video_downloader(video_queue, frame_queue):
    while True:
        video = video_queue.get()
        frames = get_video_frames(video)
        delete_video(video)
        frame_queue.put(frames)

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

    def run(self):
        while True:
            frames = self.frame_queue.get()

            start_time = time.perf_counter()
            while True:
                frame_index = int((time.perf_counter() - start_time) * 30)
                if frame_index >= len(frames):
                    break
                frame = frames[frame_index]
                self.matrix.set_pixels(frame)


if __name__ == "__main__":
    app = App(Matrix((96, 48)))
    app.run()
