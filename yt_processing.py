from requests import get
import random
import datetime
import json
import time
import os
import re

import cv2
from yt_dlp import YoutubeDL
import numpy as np

# download_ranges:   A callback function that gets called for every video with
                    #    the signature (info_dict, ydl) -> Iterable[Section].
                    #    Only the returned sections will be downloaded.
                    #    Each Section is a dict with the following keys:
                    #    * start_time: Start time of the section in seconds
                    #    * end_time: End time of the section in seconds
                    #    * title: Section title (Optional)
                    #    * index: Section number (Optional)

YDL_OPTIONS = {
    'format': 'worstvideo',
    'noplaylist': True,
    'quiet': True,
    'outtmpl': "temp/%(id)s.mp4",
    'download_ranges': lambda info_dict, ydl: [{'start_time': 0, 'end_time': 30}]
}

class Ydl:
    def __init__(self, options):
        self.options = options
        self.ydl = YoutubeDL(self.options)

    # def prelim_video_valid(self, candidate):
    #     if candidate['view_count'] > 10:
    #         print("Too many views")
    #         return False
    #     if "/shorts/" in candidate['url']:
    #         print("Video is a short")
    #         return False
    #     if candidate["duration"] < 20:
    #         print("Too short")
    #         return False
    #     return True


    # def secondary_video_valid(self, candidate):
    #     age = datetime.datetime.now(
    #     ) - datetime.datetime.strptime(candidate['upload_date'], "%Y%m%d")
    #     if age.days > 30:
    #         print("Video is too old")
    #         return False
    #     if candidate['formats'][0]['width'] / candidate['formats'][0]['height'] < 1.5:
    #         print("Video is too tall")
    #         return False
    #     return True


    # def get_unwatched_video(self):
    #     video = None
    #     while video == None:
    #         rand_num = str(random.randint(0, 7000)).zfill(4)
    #         candidate = next(self.ydl.extract_info(
    #             f"ytsearchdate:IMG {rand_num}", download=False, process=False)['entries'])
    #         if not self.prelim_video_valid(candidate):
    #             continue
    #         candidate = self.ydl.extract_info(candidate['url'], download=False)
    #         if not self.secondary_video_valid(candidate):
    #             continue
    #         video = candidate
    #     return video

    def get_unwatched_video(self):
        URL = "https://petittube.com/"
        video = None
        try:
            with open('already_watched.json', 'r') as f:
                already_watched = json.load(f)[:100]
        except:
            print("Creating new watched index")
            already_watched = []
        while video is None:
            try:
                r = get(URL)
                if r.status_code == 200:
                    text = r.text
                    regex_match = re.search(r'src="https:\/\/www\.youtube\.com\/embed\/(.*?)\?', text)
                    if regex_match:
                        yt_id = regex_match.group(1)
                        if yt_id in already_watched:
                            print("Video already watched")
                            continue
                        else:
                            already_watched.append(yt_id)
                            with open('already_watched.json', 'w') as f:
                                json.dump(already_watched, f)
                        try:
                            candidate = self.ydl.extract_info(f'https://www.youtube.com/watch?v={yt_id}', download=False)
                            if candidate['formats'][0]['width'] / candidate['formats'][0]['height'] >= 1.5:
                                video = candidate
                            else:
                                print("Video too tall")
                        except:
                            print("Video is unavailable")
                            continue
            except:
                pass
        return video

    def download_video(self, video):
        try:
            print(f"Downloading video {video['webpage_url']}")
            out = self.ydl.download([video['webpage_url']])
            return f"temp/{video['id']}.mp4"
        except:
            return None

def center_crop(image, aspect_ratio):
    height, width = image.shape[:2]
    image_aspect_ratio = width / height
    if image_aspect_ratio > aspect_ratio:
        # Crop width
        new_width = int(height * aspect_ratio)
        left = (width - new_width) // 2
        right = width - new_width - left
        return image[:, left:-right]
    elif image_aspect_ratio < aspect_ratio:
        # Crop height
        new_height = int(width / aspect_ratio)
        top = (height - new_height) // 2
        bottom = height - new_height - top
        return image[top:-bottom, :]
    else:
        return image

def iter_video_frames(video_file, resolution=(96, 48), target_fps=30):
    """
    Stream frames from a local video file at (approximately) target_fps.
    This avoids pre-decoding the whole video and avoids cross-process transfer of huge frame arrays.
    """
    print(f"Streaming frames: {video_file}")
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print("Failed to open video")
        cap.release()
        return

    start_time = time.perf_counter()
    frame_index = 0

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        # Process frame for the LED matrix
        try:
            frame = center_crop(frame, resolution[0] / resolution[1])
            frame = cv2.resize(frame, resolution, interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            # Skip bad frames rather than stalling playback
            continue

        # Pace output
        target_time = start_time + (frame_index / float(target_fps))
        now = time.perf_counter()
        if target_time > now:
            time.sleep(target_time - now)

        frame_index += 1
        yield frame

    cap.release()

def get_video_frames(video_file, resolution=(96, 48)):
    print(f"Getting frames: {video_file}")
    frames = []
    video = cv2.VideoCapture(video_file)
    while True:
        try:
            ret, frame = video.read()
            frame = center_crop(frame, resolution[0]/resolution[1])
            frame = cv2.resize(frame, resolution, interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if not ret:
                break
            frames.append(frame)
        except:
            break
    video.release()
    return frames

def delete_video(video_file):
    try:
        os.remove(video_file)
    except:
        print("Failed to delete video")
        pass
