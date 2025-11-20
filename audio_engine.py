import vlc
import os

try:
    os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")
except Exception:
    pass

class AudioEngine:
    def __init__(self):
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.media = None

    def set_media(self, path: str):
        try:
            self.media = self.instance.media_new(path)
            self.player.set_media(self.media)
        except Exception:
            pass

    def play(self):
        try:
            self.player.play()
        except Exception:
            pass

    def pause(self):
        try:
            self.player.pause()
        except Exception:
            pass

    def stop(self):
        try:
            self.player.stop()
        except Exception:
            pass

    def is_playing(self) -> bool:
        try:
            return bool(self.player.is_playing())
        except Exception:
            return False

    def get_length(self) -> int:
        try:
            return int(self.player.get_length() or 0)
        except Exception:
            return 0

    def get_time(self) -> int:
        try:
            return int(self.player.get_time() or 0)
        except Exception:
            return 0

    def set_time(self, ms: int):
        try:
            self.player.set_time(int(ms))
        except Exception:
            pass

    def audio_set_volume(self, v: int):
        try:
            self.player.audio_set_volume(int(v))
        except Exception:
            pass

    def audio_get_mute(self) -> bool:
        try:
            return bool(self.player.audio_get_mute())
        except Exception:
            return False

    def audio_toggle_mute(self):
        try:
            self.player.audio_toggle_mute()
        except Exception:
            pass

    def event_manager(self):
        try:
            return self.player.event_manager()
        except Exception:
            return None

    def release(self):
        try:
            try:
                self.player.release()
            except Exception:
                pass
            try:
                self.instance.release()
            except Exception:
                pass
        except Exception:
            pass
