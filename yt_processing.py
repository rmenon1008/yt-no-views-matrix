import random
import datetime
import time
import os

import cv2
from yt_dlp import YoutubeDL

YDL_OPTIONS = {
    'format': 'worstvideo',
    'noplaylist': True,
    'quiet': True,
    'outtmpl': "temp/%(id)s.mp4",
    'download_ranges': lambda info_dict, ydl: [{'start_time': 0, 'end_time': 30}],
}

class Ydl:
    def __init__(self, options):
        self.options = options
        self.ydl = YoutubeDL(self.options)

        self.max_age_days = 14
        self.max_views = 200
        self.search_results_per_query = 50
        self.min_duration_seconds = 10
        self.min_aspect_ratio = 1.5

    def _random_query(self):
        seed_words = [
            "test", "demo", "vlog", "video", "clip", "first", "my", "day", "new", "update",
            "img", "dsc", "camera", "phone", "setup", "build", "repair", "art", "music", "cover", "song",
            "life", "travel", "dog", "cat", "challenge", "fun", "music", "workout", "fitness",
            "food", "recipe", "nature", "art", "movie", "review", "unboxing", "science", "technology",
            "learn", "how", "guide", "explore", "trick", "tips", "experiment", "animal", "car", "road",
            "short", "trend", "random", "kids", "play", "let's", "game", "dance", "cute", "best", "hello",
            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p",
            "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
        ]
        w1 = random.choice(seed_words)
        w2 = random.choice(seed_words)
        if random.random() < 0.6:
            token = str(random.randint(0, 9999)).zfill(4)
        else:
            token = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(random.randint(3, 5)))
        if w1 == w2:
            w2 = random.choice([w for w in seed_words if w != w1])
        return f"{w1} {w2} {token}"

    def _is_recent_enough(self, upload_date):
        try:
            dt = datetime.datetime.strptime(upload_date, "%Y%m%d")
            age = datetime.datetime.now() - dt
            return age.days <= self.max_age_days
        except Exception:
            return False

    def _candidate_url(self, entry):
        url = entry.get("url") or entry.get("webpage_url")
        if url:
            return url
        vid = entry.get("id")
        if vid:
            return f"https://www.youtube.com/watch?v={vid}"
        return None

    def _prelim_video_valid(self, entry):
        vid = entry.get("id")
        if not vid:
            return False

        url = self._candidate_url(entry) or ""
        if "/shorts/" in url:
            return False

        duration = entry.get("duration")
        if isinstance(duration, (int, float)) and duration < self.min_duration_seconds:
            return False

        upload_date = entry.get("upload_date")
        if upload_date and not self._is_recent_enough(upload_date):
            return False

        view_count = entry.get("view_count")
        if isinstance(view_count, (int, float)) and view_count > self.max_views:
            return False

        return True

    def _secondary_video_valid(self, info):
        if "/shorts/" in (info.get("webpage_url") or ""):
            return False

        duration = info.get("duration")
        if isinstance(duration, (int, float)) and duration < self.min_duration_seconds:
            return False

        upload_date = info.get("upload_date")
        if upload_date and not self._is_recent_enough(upload_date):
            return False

        view_count = info.get("view_count")
        if isinstance(view_count, (int, float)) and view_count > self.max_views:
            return False

        try:
            fmt0 = (info.get("formats") or [None])[0] or {}
            w = fmt0.get("width")
            h = fmt0.get("height")
            if isinstance(w, (int, float)) and isinstance(h, (int, float)) and h != 0:
                if (w / h) < self.min_aspect_ratio:
                    return False
        except Exception:
            pass

        return True

    def get_unwatched_video(self):
        video = None
        backoff = 0.25

        while video is None:
            query = self._random_query()
            search = f"ytsearchdate{self.search_results_per_query}:{query}"
            try:
                res = self.ydl.extract_info(search, download=False, process=False)
                entries = list(res.get("entries") or [])
                if not entries:
                    time.sleep(backoff)
                    continue

                random.shuffle(entries)
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    if not self._prelim_video_valid(entry):
                        continue

                    url = self._candidate_url(entry)
                    if not url:
                        continue

                    try:
                        info = self.ydl.extract_info(url, download=False)
                    except Exception:
                        continue

                    if not self._secondary_video_valid(info):
                        continue

                    video = info
                    break
            except Exception:
                time.sleep(backoff)

            backoff = min(2.0, backoff * 1.1)

        return video

    def download_video(self, video):
        try:
            print(f"Downloading video {video['webpage_url']}")
            self.ydl.download([video['webpage_url']])
            return f"temp/{video['id']}.mp4"
        except Exception:
            return None

def center_crop(image, aspect_ratio):
    height, width = image.shape[:2]
    image_aspect_ratio = width / height
    if image_aspect_ratio > aspect_ratio:
        new_width = int(height * aspect_ratio)
        left = (width - new_width) // 2
        right = width - new_width - left
        return image[:, left:-right]
    elif image_aspect_ratio < aspect_ratio:
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

        try:
            frame = center_crop(frame, resolution[0] / resolution[1])
            frame = cv2.resize(frame, resolution, interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            continue

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
        except Exception:
            break
    video.release()
    return frames

def delete_video(video_file):
    try:
        os.remove(video_file)
    except Exception:
        print("Failed to delete video")
        pass
