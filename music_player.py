import sys
import os
import random
import traceback
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from PyQt5 import QtCore, QtGui, QtWidgets
try:
    os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")
except Exception:
    pass

import vlc
import qdarktheme
import qtawesome as qta

from utils import log_exc_to_file
from paths import SONGS_DIR, LYRICS_DIR, EQ_PRESETS_FILE
from audio_engine import AudioEngine
from metadata_utils import get_metadata, human_time, scan_folder_for_songs, read_text_file, extract_embedded_art, find_lyrics_file, clear_caches_for_path
from lyrics_utils import parse_lyrics_by_suffix
from workers import LyricsWorker, ArtWorker
from equalizer_window import EqualizerWindow
from load_songs_dialog import LoadSongsDialog

class MusicPlayer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.songs_dir = SONGS_DIR
        self.setWindowTitle("🎧 Music Player")
        self.resize(980, 560)

        try:
            self.audio = AudioEngine()
        except Exception as e:
            log_exc_to_file(e)
            raise

        self.all_songs: List[Path] = []
        self.playlist: List[Path] = []
        self.queue: List[Path] = []
        self.current_index: Optional[int] = None
        self.is_playing = False
        self.repeat_mode = 0
        self.shuffle = False

        self._lyrics_threads: List[QtCore.QThread] = []
        self._art_threads: List[QtCore.QThread] = []

        self._lyrics_workers: Dict[str, LyricsWorker] = {}
        self._art_workers: Dict[str, ArtWorker] = {}

        self.lyrics_timeline: List[Tuple[int, str]] = []
        self.current_lyric_index: int = -1
        self._current_track_path: Optional[Path] = None

        self.equalizer_window: Optional[EqualizerWindow] = None

        self._build_ui()

        self.search_completer = QtWidgets.QCompleter()
        self.search_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.search_completer.setFilterMode(QtCore.Qt.MatchContains)
        self.search_input.setCompleter(self.search_completer)
        popup = self.search_completer.popup()
        popup.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        popup.customContextMenuRequested.connect(self._on_completer_context_menu)
        self.search_completer.activated.connect(self._on_completer_selected)

        self._connect_signals()

        try:
            events = self.audio.event_manager()
            if events is not None:
                events.event_attach(vlc.EventType.MediaPlayerEndReached, self._vlc_end_callback)
        except Exception as e:
            log_exc_to_file(e)

        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.setInterval(200)
        self.ui_timer.timeout.connect(self._update_ui)
        self.ui_timer.start()

        self._load_all_songs()
        QtCore.QTimer.singleShot(350, self._auto_load_and_play_random)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top_layout = QtWidgets.QHBoxLayout()
        root.addLayout(top_layout, stretch=1)

        left = QtWidgets.QVBoxLayout()
        top_layout.addLayout(left, stretch=0)
        self.artwork_label = QtWidgets.QLabel("🎵 No Cover")
        self.artwork_label.setFixedSize(260, 260)
        self.artwork_label.setAlignment(QtCore.Qt.AlignCenter)
        self.artwork_label.setStyleSheet("border-radius:12px; background:#222; color:#ddd;")
        left.addWidget(self.artwork_label, alignment=QtCore.Qt.AlignHCenter)
        self.title_label = QtWidgets.QLabel("🎶 Title")
        self.title_label.setStyleSheet("font-weight:600; font-size:16px;")
        left.addWidget(self.title_label, alignment=QtCore.Qt.AlignHCenter)
        self.artist_label = QtWidgets.QLabel("🎤 Artist")
        left.addWidget(self.artist_label, alignment=QtCore.Qt.AlignHCenter)

        mid = QtWidgets.QVBoxLayout()
        top_layout.addLayout(mid, stretch=1)
        search_layout = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search songs (press Enter)...")
        self.search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_input, stretch=1)
        self.playlist_toggle_btn = QtWidgets.QPushButton("📜 Playlist")
        search_layout.addWidget(self.playlist_toggle_btn)
        self.load_songs_btn = QtWidgets.QPushButton("📥 Load Songs")
        search_layout.addWidget(self.load_songs_btn)
        mid.addLayout(search_layout)

        seek_layout = QtWidgets.QHBoxLayout()
        self.time_label = QtWidgets.QLabel("00:00")
        seek_layout.addWidget(self.time_label)
        self.seek_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        seek_layout.addWidget(self.seek_slider, stretch=1)
        self.total_label = QtWidgets.QLabel("00:00")
        seek_layout.addWidget(self.total_label)
        mid.addLayout(seek_layout)

        controls_layout = QtWidgets.QHBoxLayout()
        self.prev_btn = QtWidgets.QPushButton("⏮️")
        self.play_btn = QtWidgets.QPushButton("")
        self.next_btn = QtWidgets.QPushButton("⏭️")
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addStretch(1)
        mid.addLayout(controls_layout)

        opts_layout = QtWidgets.QHBoxLayout()
        self.shuffle_btn = QtWidgets.QPushButton("🔀 Shuffle")
        self.shuffle_btn.setCheckable(True)
        self.repeat_btn = QtWidgets.QPushButton("🔁 Repeat: None")
        self.eq_btn = QtWidgets.QPushButton("🎚️ Equalizer")
        self.queue_btn = QtWidgets.QPushButton("🎶 Queue")
        opts_layout.addWidget(self.shuffle_btn)
        opts_layout.addWidget(self.repeat_btn)
        opts_layout.addWidget(self.eq_btn)
        opts_layout.addStretch(1)
        opts_layout.addWidget(self.queue_btn)
        mid.addLayout(opts_layout)

        volume_layout = QtWidgets.QHBoxLayout()
        self.mute_btn = QtWidgets.QPushButton("🔊")
        self.volume_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        volume_layout.addWidget(self.mute_btn)
        volume_layout.addWidget(self.volume_slider, stretch=1)
        mid.addLayout(volume_layout)

        right = QtWidgets.QVBoxLayout()
        top_layout.addLayout(right, stretch=1)

        self.lyrics_view = QtWidgets.QListWidget()
        self.lyrics_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.lyrics_view.setSpacing(4)
        self.lyrics_view.setMinimumWidth(260)
        self.lyrics_view.setUniformItemSizes(True)
        self.lyrics_view.setWordWrap(True)
        self.lyrics_view.setStyleSheet("QListWidget { border-radius:8px; background: #0f0f0f; color: #ddd; padding:8px; }")
        self.lyrics_view.setToolTip("Lyrics (double-click a line to jump to it). Place .lrc/.srt/.vtt in lyrics/")

        right.addWidget(self.lyrics_view)

        bottom = QtWidgets.QHBoxLayout()
        root.addLayout(bottom)
        self.playlist_widget = QtWidgets.QListWidget()
        self.playlist_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.playlist_widget.hide()
        bottom.addWidget(self.playlist_widget, stretch=2)
        self.queue_widget = QtWidgets.QListWidget()
        bottom.addWidget(self.queue_widget, stretch=1)

        self.status = self.statusBar()
        self.status.showMessage("🎧 Ready to play some tunes!")

        try:
            QtWidgets.QApplication.instance().setStyleSheet(qdarktheme.load_stylesheet("dark"))
        except Exception:
            pass

        self.setStyleSheet(self.styleSheet() + """
            QPushButton { border-radius: 8px; padding:6px; }
            QListWidget { border-radius:8px; background:
            QTextEdit { border-radius:8px; background:
            QLineEdit { border-radius:8px; padding:6px; background:
            QLabel { color:
        """)

        self.art_opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        self.artwork_label.setGraphicsEffect(self.art_opacity_effect)
        self.art_anim = QtCore.QPropertyAnimation(self.art_opacity_effect, b"opacity")
        self.art_anim.setDuration(450)

    def _connect_signals(self):
        self.load_songs_btn.clicked.connect(self._on_load_songs)
        self.play_btn.clicked.connect(self._on_play_pause)
        self.next_btn.clicked.connect(self.next_track)
        self.prev_btn.clicked.connect(self.prev_track)
        self.shuffle_btn.clicked.connect(self._on_toggle_shuffle)
        self.repeat_btn.clicked.connect(self._on_toggle_repeat)
        self.playlist_toggle_btn.clicked.connect(self._toggle_playlist_view)
        self.queue_btn.clicked.connect(self._show_queue_info)
        self.volume_slider.valueChanged.connect(self._on_volume_change)
        self.mute_btn.clicked.connect(self._toggle_mute)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.playlist_widget.itemDoubleClicked.connect(self._on_playlist_doubleclick)
        self.queue_widget.itemDoubleClicked.connect(self._on_queue_doubleclick)
        self.playlist_widget.customContextMenuRequested.connect(self._on_playlist_context)
        self.queue_widget.customContextMenuRequested.connect(self._on_queue_context)
        self.search_input.returnPressed.connect(self._on_search)
        self.playlist_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.queue_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.lyrics_view.itemDoubleClicked.connect(self._on_lyrics_doubleclick)

        QtWidgets.QShortcut(QtGui.QKeySequence("Space"), self, activated=self._on_play_pause)
        QtWidgets.QShortcut(QtGui.QKeySequence("Right"), self, activated=lambda: self.seek_by(5000))
        QtWidgets.QShortcut(QtGui.QKeySequence("Left"), self, activated=lambda: self.seek_by(-5000))

        self._on_volume_change(self.volume_slider.value())

        self.eq_btn.clicked.connect(self._open_equalizer)

    def _load_all_songs(self):
        self.all_songs = scan_folder_for_songs(self.songs_dir)
        self.playlist = list(self.all_songs)
        self._refresh_playlist_view()
        model = QtCore.QStringListModel([p.stem for p in self.all_songs])
        try:
            self.search_completer.setModel(model)
        except Exception:
            pass

    def _auto_load_and_play_random(self):
        if not self.playlist:
            self.status.showMessage("No songs found in songs/ — create the folder and add files.")
            return
        idx = random.randrange(0, len(self.playlist))
        self.current_index = idx
        self.load_track(self.current_index)
        QtCore.QTimer.singleShot(250, self._safe_play)

    def _on_load_songs(self):
        dlg = LoadSongsDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            saved_music: Path = getattr(dlg, "saved_music", None)
            saved_lyrics: Optional[Path] = getattr(dlg, "saved_lyrics", None)
            if saved_music:
                clear_caches_for_path(saved_music)
                if saved_lyrics:
                    clear_caches_for_path(saved_lyrics)
                self._load_all_songs()
                try:
                    idx = self.playlist.index(saved_music)
                except ValueError:
                    idx = next((i for i, p in enumerate(self.playlist) if p.name == saved_music.name), None)
                if idx is not None:
                    self.current_index = idx
                    self.load_track(self.current_index)
                    QtCore.QTimer.singleShot(120, self._safe_play)

    def _on_search(self):
        term = self.search_input.text().strip().lower()
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            visible = term in item.text().lower()
            item.setHidden(not visible)

    def _on_completer_selected(self, text: str):
        for p in self.all_songs:
            if text.lower() in p.stem.lower():
                self.play_item(p)
                break

    def _refresh_playlist_view(self):
        self.playlist_widget.clear()
        for p in self.playlist:
            t, a, _ = get_metadata(p)
            item = QtWidgets.QListWidgetItem(f"{t} — {a}" if a else t)
            item.setData(QtCore.Qt.UserRole, p)
            self.playlist_widget.addItem(item)
        self.queue_widget.clear()
        for q in self.queue:
            t, a, _ = get_metadata(q)
            it = QtWidgets.QListWidgetItem(f"{t} — {a}" if a else t)
            it.setData(QtCore.Qt.UserRole, q)
            self.queue_widget.addItem(it)

    def _toggle_playlist_view(self):
        self.playlist_widget.setVisible(not self.playlist_widget.isVisibleTo(self))

    def _show_queue_info(self):
        QtWidgets.QMessageBox.information(self, "Queue", f"{len(self.queue)} track(s) in queue.")

    def _on_playlist_context(self, pos):
        item = self.playlist_widget.itemAt(pos)
        if not item:
            return
        menu = QtWidgets.QMenu()
        add_to_queue = menu.addAction("Add to queue")
        remove = menu.addAction("Remove from playlist")
        action = menu.exec_(self.playlist_widget.mapToGlobal(pos))
        if action == add_to_queue:
            path = item.data(QtCore.Qt.UserRole)
            self.queue.append(path)
            self._refresh_playlist_view()
        elif action == remove:
            path = item.data(QtCore.Qt.UserRole)
            if path in self.playlist:
                idx = self.playlist.index(path)
                del self.playlist[idx]
                if self.current_index is not None:
                    if idx < self.current_index:
                        self.current_index -= 1
                    elif idx == self.current_index:
                        self.stop()
                        self.current_index = None
                self._refresh_playlist_view()

    def _on_queue_context(self, pos):
        item = self.queue_widget.itemAt(pos)
        if not item:
            return
        menu = QtWidgets.QMenu()
        play_now = menu.addAction("Play now")
        remove = menu.addAction("Remove from queue")
        action = menu.exec_(self.queue_widget.mapToGlobal(pos))
        if action == play_now:
            path = item.data(QtCore.Qt.UserRole)
            self.play_item(path)
        elif action == remove:
            path = item.data(QtCore.Qt.UserRole)
            if path in self.queue:
                self.queue.remove(path)
                self._refresh_playlist_view()

    def load_track(self, index: int):
        try:
            if index is None or index < 0 or index >= len(self.playlist):
                return
            path = self.playlist[index]
            self._current_track_path = path

            self.audio.set_media(str(path))

            title, artist, duration = get_metadata(path)
            self.title_label.setText(title)
            self.artist_label.setText(artist if artist else "Unknown Artist")
            self.total_label.setText(human_time(duration if duration else 0))
            self.time_label.setText("00:00")

            self.lyrics_timeline = []
            self.current_lyric_index = -1
            self.lyrics_view.clear()
            self.lyrics_view.addItem("(Loading lyrics...)")

            try:
                self.artwork_label.setPixmap(QtGui.QPixmap())
                self.artwork_label.setText("Loading...")
            except Exception:
                pass

            try:
                for k, w in list(self._lyrics_workers.items()):
                    if k != str(path):
                        try:
                            w.interrupt()
                        except Exception:
                            pass
            except Exception:
                pass

            lw = LyricsWorker(path)
            lthread = QtCore.QThread()
            lw.moveToThread(lthread)
            lthread.started.connect(lw.run)
            lw.finished.connect(self._on_lyrics_ready)
            lw.finished.connect(lthread.quit)
            lw.finished.connect(lw.deleteLater)
            lthread.finished.connect(lthread.deleteLater)
            self._lyrics_workers[str(path)] = lw
            self._lyrics_threads.append(lthread)
            lthread.start()

            try:
                for k, w in list(self._art_workers.items()):
                    if k != str(path):
                        try:
                            w.interrupt()
                        except Exception:
                            pass
            except Exception:
                pass

            aw = ArtWorker(path)
            athread = QtCore.QThread()
            aw.moveToThread(athread)
            athread.started.connect(aw.run)
            aw.finished.connect(self._on_art_ready)
            aw.finished.connect(athread.quit)
            aw.finished.connect(aw.deleteLater)
            athread.finished.connect(athread.deleteLater)
            self._art_workers[str(path)] = aw
            self._art_threads.append(athread)
            athread.start()

            QtCore.QTimer.singleShot(1600, self._ensure_lyrics_loaded)
            QtCore.QTimer.singleShot(1600, self._ensure_art_loaded)

            self.status.showMessage(f"Loaded: {path.name}")
            self._refresh_playlist_view()

            if self.equalizer_window and getattr(self.equalizer_window, "apply_auto_on_change", True):
                QtCore.QTimer.singleShot(120, self.equalizer_window.apply_eq_to_engine)
        except Exception as e:
            log_exc_to_file(e)

    @QtCore.pyqtSlot(str, object)
    def _on_lyrics_ready(self, path_str: str, payload):
        try:
            if self._current_track_path is None or path_str != str(self._current_track_path):
                return

            content = payload.get('content') if isinstance(payload, dict) else None
            suffix = payload.get('suffix', '') if isinstance(payload, dict) else ''
            if not content:
                self.lyrics_timeline = [(0, "🎵 (Lyrics not found)")]
                self._populate_lyrics_view()
                return
            timeline = parse_lyrics_by_suffix(content, suffix)
            if not timeline:
                lines = [ln for ln in content.splitlines() if ln.strip()]
                t = 0
                timeline = [(t + i*1500, ln.strip()) for i, ln in enumerate(lines)]
            self.lyrics_timeline = timeline
            self._populate_lyrics_view()
        except Exception as e:
            log_exc_to_file(e)
            self.lyrics_timeline = [(0, "⚠️ (Lyrics load error)")]
            self._populate_lyrics_view()
        finally:
            try:
                if path_str in self._lyrics_workers:
                    del self._lyrics_workers[path_str]
            except Exception:
                pass

    def _populate_lyrics_view(self):
        try:
            self.lyrics_view.clear()
            for _, text in self.lyrics_timeline:
                item = QtWidgets.QListWidgetItem(text if text else "")
                item.setForeground(QtGui.QBrush(QtGui.QColor("#bfbfbf")))
                self.lyrics_view.addItem(item)
            if self.lyrics_view.count() == 0:
                self.lyrics_view.addItem("(No lyrics)")
            self.current_lyric_index = -1
        except Exception as e:
            log_exc_to_file(e)

    @QtCore.pyqtSlot(str, bytes)
    def _on_art_ready(self, path_str: str, data: bytes):
        try:
            if self._current_track_path is None or path_str != str(self._current_track_path):
                return

            if data:
                pix = QtGui.QPixmap()
                pix.loadFromData(data)
                scaled = pix.scaled(self.artwork_label.width(), self.artwork_label.height(),
                                    QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self._fade_artwork(scaled)
            else:
                self._fade_artwork_text("No Cover")
        except Exception as e:
            log_exc_to_file(e)
        finally:
            try:
                if path_str in self._art_workers:
                    del self._art_workers[path_str]
            except Exception:
                pass

    def _fade_artwork(self, pixmap: QtGui.QPixmap):
        try:
            self.art_opacity_effect.setOpacity(0.0)
            self.artwork_label.setPixmap(pixmap)
            self.art_anim.stop()
            self.art_anim.setStartValue(0.0)
            self.art_anim.setEndValue(1.0)
            self.art_anim.start()
        except Exception as e:
            log_exc_to_file(e)

    def _fade_artwork_text(self, text: str):
        try:
            self.art_opacity_effect.setOpacity(0.0)
            self.artwork_label.setPixmap(QtGui.QPixmap())
            self.artwork_label.setText(text)
            self.art_anim.stop()
            self.art_anim.setStartValue(0.0)
            self.art_anim.setEndValue(1.0)
            self.art_anim.start()
        except Exception as e:
            log_exc_to_file(e)

    def _on_play_pause(self):
        try:
            if self.audio.is_playing():
                self.audio.pause()
                self.is_playing = False
                self.play_btn.setIcon(qta.icon('fa5s.play', color='white'))
                self.status.showMessage("Paused")
            else:
                if (self.audio.player.get_media() is None and self.playlist):
                    if self.current_index is None:
                        self.current_index = 0
                    self.load_track(self.current_index)
                self.audio.play()
                self.is_playing = True
                self.play_btn.setIcon(qta.icon('fa5s.pause', color='white'))
                self.status.showMessage("Playing")
        except Exception as e:
            log_exc_to_file(e)

    def stop(self):
        try:
            self.audio.stop()
            self.is_playing = False
            self.play_btn.setIcon(qta.icon('fa5s.play', color='white'))
        except Exception as e:
            log_exc_to_file(e)

    def next_track(self):
        try:
            if self.queue:
                next_path = self.queue.pop(0)
                if next_path in self.playlist:
                    self.current_index = self.playlist.index(next_path)
                else:
                    self.playlist.append(next_path)
                    self.current_index = len(self.playlist) - 1
                self._refresh_playlist_view()
                self.load_track(self.current_index)
                QtCore.QTimer.singleShot(80, self._safe_play)
                return

            if not self.playlist:
                return

            if self.shuffle:
                self.current_index = random.randrange(0, len(self.playlist))
            else:
                if self.current_index is None:
                    self.current_index = 0
                else:
                    self.current_index += 1

            if self.current_index >= len(self.playlist):
                if self.repeat_mode == 2:
                    self.current_index = 0
                else:
                    self.stop()
                    self.current_index = len(self.playlist) - 1
                    return
            self.load_track(self.current_index)
            QtCore.QTimer.singleShot(80, self._safe_play)
        except Exception as e:
            log_exc_to_file(e)

    def prev_track(self):
        try:
            if not self.playlist:
                return
            cur_time = self.audio.get_time() or 0
            if cur_time > 3000:
                self.audio.set_time(0)
                return
            if self.current_index is None:
                self.current_index = 0
            else:
                self.current_index -= 1
            if self.current_index < 0:
                self.current_index = 0
            self.load_track(self.current_index)
            QtCore.QTimer.singleShot(80, self._safe_play)
        except Exception as e:
            log_exc_to_file(e)

    def play_item(self, path: Path):
        try:
            if path in self.playlist:
                self.current_index = self.playlist.index(path)
                self.load_track(self.current_index)
                QtCore.QTimer.singleShot(80, self._safe_play)
            else:
                self.playlist.append(path)
                self.current_index = len(self.playlist) - 1
                self.load_track(self.current_index)
                QtCore.QTimer.singleShot(80, self._safe_play)
            self._refresh_playlist_view()
        except Exception as e:
            log_exc_to_file(e)

    def _safe_play(self):
        try:
            self.audio.play()
            self.is_playing = True
            self.play_btn.setIcon(qta.icon('fa5s.pause', color='white'))
        except Exception as e:
            log_exc_to_file(e)

    def seek_by(self, ms_delta: int):
        try:
            cur = self.audio.get_time() or 0
            new = max(0, cur + ms_delta)
            self.audio.set_time(new)
        except Exception as e:
            log_exc_to_file(e)

    def _on_toggle_shuffle(self):
        self.shuffle = self.shuffle_btn.isChecked()
        self.shuffle_btn.setToolTip("Shuffle On" if self.shuffle else "Shuffle Off")
        self.status.showMessage("Shuffle enabled" if self.shuffle else "Shuffle disabled")

    def _on_toggle_repeat(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        if self.repeat_mode == 0:
            self.repeat_btn.setText("🔁 Repeat: None")
        elif self.repeat_mode == 1:
            self.repeat_btn.setText("🔂 Repeat: One")
        else:
            self.repeat_btn.setText("🔁 Repeat: All")

    def _on_volume_change(self, val):
        try:
            self.audio.audio_set_volume(int(val))
        except Exception:
            pass
        self.status.showMessage(f"Volume: {val}%")

    def _toggle_mute(self):
        try:
            muted = self.audio.audio_get_mute()
            self.audio.audio_toggle_mute()
            self.mute_btn.setIcon(qta.icon('fa5s.volume-off' if not muted else 'fa5s.volume-up', color='white'))
        except Exception as e:
            log_exc_to_file(e)

    def _on_seek_released(self):
        try:
            if not self.audio:
                return
            max_val = max(1, self.seek_slider.maximum())
            pos = self.seek_slider.value() / float(max_val)
            length = self.audio.get_length()
            if length and length > 0:
                ms = int(length * pos)
                self.audio.set_time(ms)
        except Exception as e:
            log_exc_to_file(e)

    def _on_playlist_doubleclick(self, item):
        path = item.data(QtCore.Qt.UserRole)
        if path:
            self.play_item(path)

    def _on_queue_doubleclick(self, item):
        path = item.data(QtCore.Qt.UserRole)
        if path in self.queue:
            self.play_item(path)

    def _on_lyrics_doubleclick(self, item):
        try:
            idx = self.lyrics_view.row(item)
            if 0 <= idx < len(self.lyrics_timeline):
                t_ms, _ = self.lyrics_timeline[idx]
                self.audio.set_time(t_ms)
        except Exception as e:
            log_exc_to_file(e)

    def _vlc_end_callback(self, event):
        QtCore.QMetaObject.invokeMethod(self, "_handle_end_of_track", QtCore.Qt.QueuedConnection)

    @QtCore.pyqtSlot()
    def _handle_end_of_track(self):
        try:
            if self.repeat_mode == 1:
                if self.current_index is not None and 0 <= self.current_index < len(self.playlist):
                    self.load_track(self.current_index)
                    QtCore.QTimer.singleShot(150, self._safe_play)
                return
            self.next_track()
        except Exception as e:
            log_exc_to_file(e)

    def _update_ui(self):
        try:
            if self.audio:
                length = self.audio.get_length() or 0
                pos = self.audio.get_time() or 0
                if length > 0:
                    if not self.seek_slider.isSliderDown():
                        try:
                            fraction = pos / length if length else 0
                            self.seek_slider.setValue(int(fraction * self.seek_slider.maximum()))
                        except Exception:
                            pass
                    self.total_label.setText(human_time(length))
                else:
                    self.total_label.setText("00:00")
                self.time_label.setText(human_time(pos))
                if self.audio.is_playing() and not self.seek_slider.isSliderDown():
                    if length:
                        max_val = max(1, self.seek_slider.maximum())
                        target = int((pos / length) * max_val)
                        current = self.seek_slider.value()
                        blended = int(current + (target - current) * 0.4)
                        self.seek_slider.setValue(blended)
                else:
                    if not self.is_playing:
                        self.play_btn.setIcon(qta.icon('fa5s.play', color='white'))

                self._update_lyrics_scroll(pos)
        except Exception as e:
            log_exc_to_file(e)

    def _ensure_lyrics_loaded(self):
        try:
            if self._current_track_path is None:
                return
            if not self.lyrics_timeline:
                if self.lyrics_view.count() == 1 and self.lyrics_view.item(0).text().strip() == "(Loading lyrics...)":
                    self.lyrics_timeline = [(0, "🎵 (Lyrics not found)")]
                    self._populate_lyrics_view()
        except Exception as e:
            log_exc_to_file(e)

    def _ensure_art_loaded(self):
        try:
            if self._current_track_path is None:
                return
            pm = self.artwork_label.pixmap()
            txt = self.artwork_label.text() or ""
            if (pm is None or pm.isNull()) and ("Loading" in txt or txt.strip() == ""):
                self._fade_artwork_text("No Cover")
        except Exception as e:
            log_exc_to_file(e)

    def _update_lyrics_scroll(self, current_ms: int):
        try:
            if not self.lyrics_timeline:
                return
            lo, hi = 0, len(self.lyrics_timeline) - 1
            idx = -1
            while lo <= hi:
                mid = (lo + hi) // 2
                t_mid = self.lyrics_timeline[mid][0]
                if t_mid <= current_ms:
                    idx = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            if idx == -1:
                if self.current_lyric_index != -1:
                    self._set_lyric_highlight(-1)
                return
            if idx != self.current_lyric_index:
                self._set_lyric_highlight(idx)
                item = self.lyrics_view.item(idx)
                if item:
                    self.lyrics_view.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtCenter)
        except Exception as e:
            log_exc_to_file(e)

    def _set_lyric_highlight(self, new_index: int):
        try:
            if 0 <= self.current_lyric_index < self.lyrics_view.count():
                prev_item = self.lyrics_view.item(self.current_lyric_index)
                if prev_item:
                    prev_item.setFont(QtGui.QFont())
                    prev_item.setForeground(QtGui.QBrush(QtGui.QColor("#bfbfbf")))
            if 0 <= new_index < self.lyrics_view.count():
                cur_item = self.lyrics_view.item(new_index)
                if cur_item:
                    f = QtGui.QFont()
                    f.setBold(True)
                    cur_item.setFont(f)
                    cur_item.setForeground(QtGui.QBrush(QtGui.QColor("#00d2ff")))
                    self.lyrics_view.setCurrentRow(new_index)
            else:
                self.lyrics_view.setCurrentRow(-1)
            self.current_lyric_index = new_index
        except Exception as e:
            log_exc_to_file(e)

    def _on_completer_context_menu(self, pos):
        try:
            popup = self.search_completer.popup()
            index = popup.indexAt(pos)
            if not index.isValid():
                return

            song_name = index.data(QtCore.Qt.DisplayRole)

            menu = QtWidgets.QMenu(self)
            add_action = menu.addAction("➕ Add to Queue")

            action = menu.exec_(popup.mapToGlobal(pos))
            if not action:
                return

            matched_path = next((p for p in self.all_songs if song_name.lower() == p.stem.lower()), None)
            if not matched_path:
                return

            if action == add_action:
                self.queue.append(matched_path)
                self._refresh_playlist_view()
                self.status.showMessage(f"Added to queue: {song_name}")

        except Exception as e:
            log_exc_to_file(e)

    def closeEvent(self, event):
        try:
            try:
                self.audio.stop()
            except Exception:
                pass
            try:
                self.audio.release()
            except Exception:
                pass
            for w in list(self._lyrics_workers.values()):
                try:
                    w.interrupt()
                except Exception:
                    pass
            for w in list(self._art_workers.values()):
                try:
                    w.interrupt()
                except Exception:
                    pass
            for th in self._lyrics_threads + self._art_threads:
                try:
                    th.quit()
                except Exception:
                    pass
        except Exception as e:
            log_exc_to_file(e)
        event.accept()

    def _open_equalizer(self):
        try:
            if not self.equalizer_window:
                self.equalizer_window = EqualizerWindow(self, parent=self)
            self.equalizer_window.show()
            self.equalizer_window.raise_()
            self.equalizer_window.activateWindow()
        except Exception as e:
            log_exc_to_file(e)
