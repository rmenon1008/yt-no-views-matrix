from requests import get
import random
import datetime
import json
import time
import os

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
    'max_views': 10,
    'max_duration': 60,
    'outtmpl': "temp/%(id)s.mp4",
    'download_ranges': lambda info_dict, ydl: [{'start_time': 0, 'end_time': 10}]
}

class Ydl:
    def __init__(self, options):
        self.options = options
        self.ydl = YoutubeDL(self.options)

    def prelim_video_valid(self, candidate):
        if candidate['view_count'] > 10:
            print("Too many views")
            return False
        if "/shorts/" in candidate['url']:
            print("Video is a short")
            return False
        if candidate["duration"] < 10:
            print("Too short")
            return False
        return True


    def secondary_video_valid(self, candidate):
        age = datetime.datetime.now(
        ) - datetime.datetime.strptime(candidate['upload_date'], "%Y%m%d")
        if age.days > 30:
            print("Video is too old")
            return False
        # if candidate['channel_follower_count'] == None or candidate['channel_follower_count'] > 500:
        #     print("Channel is too big")
        #     return False
        if candidate['formats'][0]['width'] / candidate['formats'][0]['height'] < 1.5:
            print("Video is too tall")
            return False
        return True


    def get_unwatched_video(self):
        video = None
        while video == None:
            rand_num = str(random.randint(0, 7000)).zfill(4)
            candidate = next(self.ydl.extract_info(
                f"ytsearchdate:IMG {rand_num}", download=False, process=False)['entries'])
            if not self.prelim_video_valid(candidate):
                continue
            candidate = self.ydl.extract_info(candidate['url'], download=False)
            if not self.secondary_video_valid(candidate):
                continue
            video = candidate
        return video

    def download_video(self, video):
        self.ydl.download([video['webpage_url']])
        return f"temp/{video['id']}.mp4"

def get_video_frames(video_file, resolution=(96, 48)):
    print(video_file)
    frames = []
    video = cv2.VideoCapture(video_file)
    while True:
        try:
            ret, frame = video.read()
            frame = cv2.resize(frame, resolution)
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