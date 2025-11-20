from PyQt5 import QtWidgets, QtCore, QtGui
from pathlib import Path
import shutil
from paths import SONGS_DIR, LYRICS_DIR
from utils import log_exc_to_file
from typing import Optional

class LoadSongsDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Load Songs — Add new track")
        self.setModal(True)
        self.resize(640, 360)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.music_path: Optional[Path] = None
        self.lyrics_path: Optional[Path] = None

        self._build_ui()
        self.setAcceptDrops(True)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QtWidgets.QLabel("Add a new song")
        header.setStyleSheet("font-size:18px; font-weight:600;")
        layout.addWidget(header, alignment=QtCore.Qt.AlignLeft)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        layout.addLayout(grid)

        self.music_drop = QtWidgets.QFrame()
        self.music_drop.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.music_drop.setAcceptDrops(True)
        self.music_drop.setMinimumHeight(80)
        self.music_drop.setStyleSheet("""QFrame { border: 2px dashed #444; border-radius:8px; }""")
        md_layout = QtWidgets.QVBoxLayout(self.music_drop)
        self.music_drop_label = QtWidgets.QLabel("Drop music file here or use Browse")
        md_layout.addWidget(self.music_drop_label, alignment=QtCore.Qt.AlignCenter)
        grid.addWidget(QtWidgets.QLabel("MUSIC FILE"), 0, 0)
        grid.addWidget(self.music_drop, 0, 1)

        music_controls = QtWidgets.QHBoxLayout()
        self.music_browse_btn = QtWidgets.QPushButton("Browse...")
        self.music_clear_btn = QtWidgets.QPushButton("Clear")
        music_controls.addWidget(self.music_browse_btn)
        music_controls.addWidget(self.music_clear_btn)
        grid.addLayout(music_controls, 1, 1)

        self.music_path_preview = QtWidgets.QLineEdit()
        self.music_path_preview.setReadOnly(True)
        grid.addWidget(self.music_path_preview, 2, 1)

        self.lyrics_drop = QtWidgets.QFrame()
        self.lyrics_drop.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lyrics_drop.setAcceptDrops(True)
        self.lyrics_drop.setMinimumHeight(80)
        self.lyrics_drop.setStyleSheet("""QFrame { border: 2px dashed #444; border-radius:8px; }""")
        ld_layout = QtWidgets.QVBoxLayout(self.lyrics_drop)
        self.lyrics_drop_label = QtWidgets.QLabel("Drop lyrics file here (optional) or use Browse")
        ld_layout.addWidget(self.lyrics_drop_label, alignment=QtCore.Qt.AlignCenter)
        grid.addWidget(QtWidgets.QLabel("LYRICS FILE"), 3, 0)
        grid.addWidget(self.lyrics_drop, 3, 1)

        lyrics_controls = QtWidgets.QHBoxLayout()
        self.lyrics_browse_btn = QtWidgets.QPushButton("Browse...")
        self.lyrics_clear_btn = QtWidgets.QPushButton("Clear")
        lyrics_controls.addWidget(self.lyrics_browse_btn)
        lyrics_controls.addWidget(self.lyrics_clear_btn)
        grid.addLayout(lyrics_controls, 4, 1)

        self.lyrics_path_preview = QtWidgets.QLineEdit()
        self.lyrics_path_preview.setReadOnly(True)
        grid.addWidget(self.lyrics_path_preview, 5, 1)

        name_label = QtWidgets.QLabel("SONG NAME")
        grid.addWidget(name_label, 6, 0)
        self.name_input = QtWidgets.QLineEdit()
        grid.addWidget(self.name_input, 6, 1)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch(1)
        self.save_btn = QtWidgets.QPushButton("Save")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        QtWidgets.QApplication.instance().setStyleSheet(QtWidgets.QApplication.instance().styleSheet())
        self.setStyleSheet(self.styleSheet() + """
            QPushButton { border-radius: 8px; padding:6px; min-width:90px; }
            QLineEdit { background: #111; color: #eee; padding:6px; border-radius:6px; }
            QLabel { color: #ddd; }
        """)

        self.music_browse_btn.clicked.connect(self._on_music_browse)
        self.lyrics_browse_btn.clicked.connect(self._on_lyrics_browse)
        self.music_clear_btn.clicked.connect(self._on_music_clear)
        self.lyrics_clear_btn.clicked.connect(self._on_lyrics_clear)
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QtGui.QDropEvent):
        pos = event.pos()
        global_pos = self.mapToGlobal(pos)
        widget = QtWidgets.QApplication.widgetAt(global_pos)
        urls = event.mimeData().urls()
        if not urls:
            return
        first = Path(urls[0].toLocalFile())
        if widget is self.music_drop or widget is self.music_drop_label or widget is self.music_path_preview:
            self._set_music_path(first)
            return
        if widget is self.lyrics_drop or widget is self.lyrics_drop_label or widget is self.lyrics_path_preview:
            self._set_lyrics_path(first)
            return
        if first.suffix.lower() in ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'):
            self._set_music_path(first)
        elif first.suffix.lower() in ('.lrc', '.srt', '.vtt', '.txt'):
            self._set_lyrics_path(first)

    def _on_music_browse(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select music file", str(Path.home()),
                                                     "Music files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;All files (*)")
        if f:
            self._set_music_path(Path(f))

    def _on_lyrics_browse(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select lyrics file", str(Path.home()),
                                                     "Lyrics files (*.lrc *.srt *.vtt *.txt);;All files (*)")
        if f:
            self._set_lyrics_path(Path(f))

    def _on_music_clear(self):
        self.music_path = None
        self.music_path_preview.setText("")
        self.music_drop_label.setText("Drop music file here or use Browse")

    def _on_lyrics_clear(self):
        self.lyrics_path = None
        self.lyrics_path_preview.setText("")
        self.lyrics_drop_label.setText("Drop lyrics file here (optional) or use Browse")

    def _set_music_path(self, p: Path):
        if not p.exists():
            QtWidgets.QMessageBox.warning(self, "File missing", f"{p} does not exist.")
            return
        if p.suffix.lower() not in ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'):
            QtWidgets.QMessageBox.warning(self, "Invalid file", "Not a supported audio file.")
            return
        self.music_path = p
        self.music_path_preview.setText(str(p))
        self.music_drop_label.setText(p.name)
        current = self.name_input.text().strip()
        if not current:
            self.name_input.setText(p.stem)

    def _set_lyrics_path(self, p: Path):
        if not p.exists():
            QtWidgets.QMessageBox.warning(self, "File missing", f"{p} does not exist.")
            return
        if p.suffix.lower() not in ('.lrc', '.srt', '.vtt', '.txt'):
            QtWidgets.QMessageBox.warning(self, "Invalid file", "Not a supported lyrics file.")
            return
        self.lyrics_path = p
        self.lyrics_path_preview.setText(str(p))
        self.lyrics_drop_label.setText(p.name)

    def _on_save(self):
        if not self.music_path or not self.music_path.exists():
            QtWidgets.QMessageBox.warning(self, "Select music", "Please choose a music file first.")
            return
        name = self.name_input.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Name required", "Please enter a song name.")
            return
        music_ext = self.music_path.suffix
        music_dest = SONGS_DIR / f"{name}{music_ext}"
        lyrics_dest = None
        if self.lyrics_path:
            lyrics_ext = self.lyrics_path.suffix
            lyrics_dest = LYRICS_DIR / f"{name}{lyrics_ext}"

        if music_dest.exists():
            resp = QtWidgets.QMessageBox.question(self, "Overwrite?", f"{music_dest.name} exists. Overwrite?")
            if resp != QtWidgets.QMessageBox.Yes:
                return

        if lyrics_dest and lyrics_dest.exists():
            resp = QtWidgets.QMessageBox.question(self, "Overwrite?", f"{lyrics_dest.name} exists. Overwrite?")
            if resp != QtWidgets.QMessageBox.Yes:
                return

        try:
            SONGS_DIR.mkdir(exist_ok=True)
            LYRICS_DIR.mkdir(exist_ok=True)
            shutil.copy2(str(self.music_path), str(music_dest))
            if self.lyrics_path:
                shutil.copy2(str(self.lyrics_path), str(lyrics_dest))
        except Exception as e:
            log_exc_to_file(e)
            QtWidgets.QMessageBox.critical(self, "Save error", f"Failed to save files: {e}")
            return

        self.saved_music = music_dest
        self.saved_lyrics = lyrics_dest
        self.accept()
