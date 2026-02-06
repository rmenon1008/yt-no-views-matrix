import multiprocessing as mp
import time
import numpy as np
import cv2
import os

from matrix_driver import Matrix
from yt_processing import Ydl, YDL_OPTIONS, iter_video_frames, delete_video

def video_finder(video_queue):
        print("Video finder process started")
        ydl = Ydl(YDL_OPTIONS)
        video_download_count = 0
        while True:
            if video_queue.full():
                print("Video queue is full, waiting...")
                time.sleep(0.05)
                continue
            print("Searching for new unwatched video...")
            video_info = ydl.get_unwatched_video()
            if video_info:
                print(f"Found video to download: {video_info.get('id', 'unknown')}")
                video_file = ydl.download_video(video_info)
                if video_file is not None:
                    video_download_count += 1
                    print(f"Downloaded video #{video_download_count}: {video_file}")
                    video_queue.put(video_file)
                    print(f"Added video #{video_download_count} to queue")
                else:
                    print("Download failed, will try again")
            else:
                print("No suitable video found, will try again")

BLANK_FRAME = np.ones((48, 96, 3), dtype=np.uint8) * 255
STARTUP_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "loading.png")
STARTUP_FRAME = cv2.cvtColor(cv2.imread(STARTUP_IMAGE_PATH), cv2.COLOR_BGR2RGB)
class App:
    def __init__(self, matrix):
        print("Initializing App...")
        self.matrix = matrix

        # NOTE: Keep large frame data in-process; only pass small messages (file paths) across processes.
        print("Creating video queue with maxsize 10")
        self.video_queue = mp.Queue(maxsize=10)
        print("Starting video finder process")
        self.video_finder_process = mp.Process(target=video_finder, args=(self.video_queue,))
        self.video_finder_process.start()

        print("Setting blank frame and resetting matrix")
        self.matrix.set_pixels(BLANK_FRAME)
        self.matrix.reset()
        time.sleep(1)

        print("Displaying startup frame")
        self.matrix.set_pixels(STARTUP_FRAME)
        time.sleep(4)
        print("App initialization complete")

    def _get_buffered_videos(self):
        try:
            return self.video_queue.qsize()
        except NotImplementedError:
            # Some platforms don't implement qsize() for multiprocessing.Queue
            return 0

    def run(self):
        print("Waiting for first downloaded video...")
        video_count = 0
        while True:
            buffered_count = self._get_buffered_videos()
            if buffered_count < 2:
                print(f"Running out of videos - buffered: {buffered_count}")
            video_file = self.video_queue.get()
            video_count += 1
            print(f"Playing video #{video_count}: {video_file}")

            try:
                print(f"Starting frame iteration for video #{video_count}")
                frame_count = 0
                # Pace playback to the video's real timestamps/FPS.
                for frame in iter_video_frames(video_file, resolution=(96, 48)):
                    self.matrix.set_pixels(frame)
                    frame_count += 1
                print(f"Finished playing video #{video_count} - {frame_count} frames displayed")
            except Exception as e:
                print(f"Error playing video #{video_count}: {type(e).__name__}: {e}")
            finally:
                print(f"Deleting video file: {video_file}")
                delete_video(video_file)

if __name__ == "__main__":
    print("Starting up...")
    app = App(Matrix((96, 48)))
    app.run()
