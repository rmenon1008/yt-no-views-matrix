import random
import datetime
import time
import os
import urllib.parse

import cv2
from yt_dlp import YoutubeDL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")

YDL_OPTIONS = {
    'format': '18/best[ext=mp4][acodec!=none][vcodec!=none][height<=360]/best[ext=mp4][acodec!=none][vcodec!=none]/best',
    'noplaylist': True,
    'quiet': True,
    # Use an absolute temp dir so running under systemd/cron/etc doesn't write
    # to an unexpected working directory.
    'outtmpl': os.path.join(TEMP_DIR, "%(id)s.%(ext)s"),
    'download_ranges': lambda info_dict, ydl: [{'start_time': 0, 'end_time': 30}],
    'remote_components': ['ejs:github'],
}

class Ydl:
    def __init__(self, options):
        # Coarse buckets:
        # - "This week": last 7 days
        self.max_age_days = 7
        self.max_views = 1000
        self.search_results_per_query = 50
        self.min_duration_seconds = 10
        self.min_aspect_ratio = 1.5

        # If you want to use YouTube's *native* search filters, paste the `sp`
        # parameter from a filtered YouTube search URL here (or set env var
        # `YT_SEARCH_SP`). Example from user: "EgIIAw%253D%253D".
        self.youtube_search_sp = self._normalize_sp(os.getenv("YT_SEARCH_SP", "EgIIAw%253D%253D"))

        # Push the upload-date constraint into yt-dlp itself so it can reject
        # out-of-range videos as early as possible.
        #
        # yt-dlp accepts relative dates like "today-14days".
        opts = dict(options)
        opts.setdefault("dateafter", f"today-{self.max_age_days}days")

        # Allow disabling features that are more likely to break on minimal installs.
        # (e.g. missing certs for remote components, missing ffmpeg for ranged downloads)
        if os.getenv("YT_NO_REMOTE_COMPONENTS", "").strip() in ("1", "true", "True", "yes", "YES"):
            opts.pop("remote_components", None)
        if os.getenv("YT_DISABLE_RANGES", "").strip() in ("1", "true", "True", "yes", "YES"):
            opts.pop("download_ranges", None)

        # Minimal progress hook to see the *actual* output path on device.
        def _progress_hook(d):
            status = d.get("status")
            if status == "finished":
                fn = d.get("filename")
                if fn:
                    print(f"yt-dlp finished: {fn}")
            elif status == "error":
                print(f"yt-dlp error: {d}")

        # Even with quiet=True, progress hooks still run.
        existing_hooks = list(opts.get("progress_hooks") or [])
        opts["progress_hooks"] = existing_hooks + [_progress_hook]

        self.options = opts
        self.ydl = YoutubeDL(self.options)

        # Keep a small in-memory cache of IDs we've already attempted this run.
        # This reduces repeated lookups from overlapping/random searches.
        self._seen_ids = set()
        self._seen_ids_max = 5000

    @staticmethod
    def _normalize_sp(sp_value: str) -> str:
        """
        Normalize YouTube's `sp` parameter.

        Browsers sometimes show it double-encoded (e.g. %253D instead of %3D).
        We normalize to a value that can be safely appended to a URL as:
        `...&sp=<normalized>`.
        """
        if not sp_value:
            return ""

        s = sp_value.strip()
        if s.startswith("&sp="):
            s = s[4:]
        if s.startswith("sp="):
            s = s[3:]

        # De-double-encode if needed (e.g. %253D -> %3D).
        prev = None
        for _ in range(3):
            if s == prev:
                break
            prev = s
            s = urllib.parse.unquote(s)

        # If it contains raw characters that should be escaped (like '='), encode it once.
        if "%" not in s and any(ch in s for ch in ("=", "+", "/", " ")):
            s = urllib.parse.quote(s, safe="")

        return s

    def _random_query(self):
        seed_words = [
            "test", "demo", "vlog", "video", "clip", "first", "my", "day", "new", "update",
            "img", "dsc", "camera", "phone", "setup", "build", "repair", "art", "music", "cover", "song",
            "life", "travel", "dog", "cat", "challenge", "fun", "music", "workout", "fitness",
            "food", "recipe", "nature", "art", "movie", "review", "unboxing", "science", "technology",
            "learn", "how", "guide", "explore", "trick", "tips", "experiment", "animal", "car", "road",
            "short", "trend", "random", "kids", "play", "let's", "game", "dance", "cute", "best", "hello",
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
            print(f"Skipping {url}: not a shorts video")
            return False

        duration = entry.get("duration")
        if isinstance(duration, (int, float)) and duration < self.min_duration_seconds:
            print("Skipping short video")
            return False

        upload_date = entry.get("upload_date")
        if upload_date and not self._is_recent_enough(upload_date):
            print("Skipping old video")
            return False

        view_count = entry.get("view_count")
        if isinstance(view_count, (int, float)) and view_count > self.max_views:
            print("Skipping video with too many views")
            return False

        return True

    def _secondary_video_valid(self, info):
        if "/shorts/" in (info.get("webpage_url") or ""):
            print("Skipping shorts video")
            return False

        duration = info.get("duration")
        if isinstance(duration, (int, float)) and duration < self.min_duration_seconds:
            print("Skipping short video")
            return False

        upload_date = info.get("upload_date")
        if upload_date and not self._is_recent_enough(upload_date):
            print("Skipping old video")
            return False

        view_count = info.get("view_count")
        if isinstance(view_count, (int, float)) and view_count > self.max_views:
            print("Skipping video with too many views")
            return False

        try:
            # Prefer lightweight fields first; `formats` is often missing when we
            # do a metadata-only extraction (process=False).
            ar = info.get("aspect_ratio")
            if isinstance(ar, (int, float)) and ar < self.min_aspect_ratio:
                print("Skipping video with too small aspect ratio")
                return False

            w = info.get("width")
            h = info.get("height")
            if isinstance(w, (int, float)) and isinstance(h, (int, float)) and h != 0:
                if (w / h) < self.min_aspect_ratio:
                    print("Skipping video with too small aspect ratio")
                    return False
        except Exception:
            pass

        return True

    def _remember_seen_id(self, vid):
        if not vid:
            return
        self._seen_ids.add(vid)
        if len(self._seen_ids) > self._seen_ids_max:
            self._seen_ids.clear()

    def get_unwatched_video(self):
        video = None
        backoff = 0.25

        while video is None:
            query = self._random_query()
            if self.youtube_search_sp:
                # Use YouTube's own filtered results page.
                # NOTE: `search_results_per_query` is not enforced here; YouTube will decide how many
                # results to return. We still randomize and filter locally.
                search_query = urllib.parse.quote_plus(query)
                search = f"https://www.youtube.com/results?search_query={search_query}&sp={self.youtube_search_sp}"
            else:
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

                    vid = entry.get("id")
                    if vid and vid in self._seen_ids:
                        continue

                    url = self._candidate_url(entry)
                    if not url:
                        continue

                    try:
                        info = self.ydl.extract_info(url, download=False, process=False)
                    except Exception:
                        self._remember_seen_id(vid)
                        continue

                    if not self._secondary_video_valid(info):
                        self._remember_seen_id(vid or info.get("id"))
                        continue

                    video = info
                    self._remember_seen_id(vid or info.get("id"))
                    break
            except Exception:
                time.sleep(backoff)

            backoff = min(2.0, backoff * 1.1)

        return video

    def download_video(self, video):
        try:
            # Ensure output directory exists (absolute, stable across processes/services)
            os.makedirs(TEMP_DIR, exist_ok=True)

            url = video.get("webpage_url") or video.get("original_url") or video.get("url")
            if not url:
                vid = video.get("id")
                if vid:
                    url = f"https://www.youtube.com/watch?v={vid}"
            if not url:
                return None

            print(f"Downloading video {url}")
            print(f"cwd={os.getcwd()}")
            print(f"TEMP_DIR={TEMP_DIR}")

            # Use extract_info(download=True) so we can deterministically derive the output filename.
            info = self.ydl.extract_info(url, download=True)
            filename = None
            try:
                filename = self.ydl.prepare_filename(info)
            except Exception:
                # Fallback to expected mp4 name if prepare_filename fails for some reason.
                vid = (info or {}).get("id") or video.get("id")
                if vid:
                    filename = os.path.join(TEMP_DIR, f"{vid}.mp4")

            if filename and os.path.exists(filename):
                return filename

            # Helpful extra signal: check if a partial file was left behind.
            if filename and os.path.exists(f"{filename}.part"):
                print(f"Download left partial file: {filename}.part")
            else:
                print(f"Download completed but file not found: {filename}")
            return None
        except Exception as e:
            print(f"Download failed: {type(e).__name__}: {e}")
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

def iter_video_frames(video_file, resolution=(96, 48), target_fps=None, max_seconds=30):
    """
    Stream frames from a local video file at the correct frame rate.

    If `target_fps` is None, we pace to the video's own timestamps/FPS (preferred).
    If `target_fps` is provided, we pace to that value (useful for downsampling).
    This avoids pre-decoding the whole video and avoids cross-process transfer of huge frame arrays.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"Streaming frames: {video_file}")

    # Check if file exists and is readable
    if not os.path.exists(video_file):
        logger.error(f"Video file does not exist: {video_file}")
        return

    try:
        file_size = os.path.getsize(video_file)
        if file_size == 0:
            logger.error(f"Video file is empty: {video_file}")
            return
        logger.debug(f"Video file size: {file_size} bytes")
    except Exception as e:
        logger.error(f"Error checking video file: {e}")
        return

    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        logger.error(f"Failed to open video: {video_file}")
        cap.release()
        return

    def _get_capture_fps():
        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS))
        except Exception:
            fps = 0.0
        # OpenCV may return 0/NaN/inf for some containers.
        if not (fps > 1e-6) or fps != fps or fps == float("inf"):
            return None
        return fps

    capture_fps = _get_capture_fps()
    paced_fps = float(target_fps) if target_fps is not None else (capture_fps or 30.0)

    start_wall = time.perf_counter()
    base_pos_ms = None
    frame_index = 0

    while True:
        # Hard stop so we never play for more than max_seconds.
        # Prefer container timestamps when available; fall back to our pacing clock.
        try:
            pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            if isinstance(pos_ms, (int, float)) and pos_ms > 0 and (pos_ms / 1000.0) >= max_seconds:
                break
        except Exception:
            pass

        if (time.perf_counter() - start_wall) >= max_seconds:
            break

        ret, frame = cap.read()
        if not ret or frame is None:
            break

        try:
            frame = center_crop(frame, resolution[0] / resolution[1])
            frame = cv2.resize(frame, resolution, interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            continue

        # Pace playback.
        #
        # Prefer the video's own timestamps (better for variable-FPS content).
        # If timestamps aren't available, pace using FPS.
        now = time.perf_counter()
        target_wall = None
        try:
            pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            if isinstance(pos_ms, (int, float)) and pos_ms > 0:
                if base_pos_ms is None:
                    base_pos_ms = pos_ms
                    # Anchor "video time 0" to the current wall clock.
                    start_wall = now
                target_wall = start_wall + ((pos_ms - base_pos_ms) / 1000.0)
        except Exception:
            target_wall = None

        if target_wall is None:
            target_wall = start_wall + (frame_index / paced_fps)

        sleep_for = target_wall - now
        if sleep_for > 0:
            time.sleep(sleep_for)

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
