from PyQt5 import QtCore
from pathlib import Path
from metadata_utils import read_text_file, find_lyrics_file
from metadata_utils import extract_embedded_art
from typing import Optional

class LyricsWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str, object)
    def __init__(self, song_path: Path):
        super().__init__()
        self.song_path = song_path
        self._interrupted = False

    @QtCore.pyqtSlot()
    def run(self):
        try:
            if self._interrupted:
                return
            lf = find_lyrics_file(self.song_path)
            if not lf:
                self.finished.emit(str(self.song_path), {'content': None, 'suffix': ''})
                return
            content = read_text_file(lf) or ''
            if self._interrupted:
                return
            self.finished.emit(str(self.song_path), {'content': content, 'suffix': lf.suffix.lower()})
        except Exception:
            try:
                self.finished.emit(str(self.song_path), {'content': None, 'suffix': ''})
            except Exception:
                pass

    def interrupt(self):
        self._interrupted = True

class ArtWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str, bytes)
    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self._interrupted = False

    @QtCore.pyqtSlot()
    def run(self):
        try:
            if self._interrupted:
                return
            data = extract_embedded_art(self.path)
            if not data:
                self.finished.emit(str(self.path), b"")
            else:
                self.finished.emit(str(self.path), data)
        except Exception:
            try:
                self.finished.emit(str(self.path), b"")
            except Exception:
                pass

    def interrupt(self):
        self._interrupted = True
