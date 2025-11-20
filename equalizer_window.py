from PyQt5 import QtWidgets, QtCore, QtGui
import json
import vlc
from paths import EQ_PRESETS_FILE
from utils import log_exc_to_file

class EqualizerWindow(QtWidgets.QDialog):
    BAND_LABELS = ["32 Hz", "64 Hz", "125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz", "16 kHz", "20 kHz"]
    BAND_COUNT = 11

    def __init__(self, parent_player, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("🎚Equalizer")
        self.setModal(False)
        self.resize(780, 420)
        self.parent_player = parent_player

        self.eq = None
        try:
            self.eq = vlc.AudioEqualizer()
        except Exception:
            try:
                self.eq = vlc.audio_equalizer_new()
            except Exception:
                self.eq = None

        self.sliders = []
        self.animations = []
        self.preset_combo = None
        self.apply_auto_on_change = True

        self._load_user_presets()

        self._build_ui()
        self.apply_eq_to_engine()
        self._do_open_animation()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Equalizer — 11-band")
        title.setStyleSheet("font-size:18px; font-weight:700;")
        header_layout.addWidget(title, alignment=QtCore.Qt.AlignLeft)

        self.preset_combo = QtWidgets.QComboBox()
        self._populate_preset_combo()
        header_layout.addStretch(1)
        header_layout.addWidget(self.preset_combo)

        apply_preset_btn = QtWidgets.QPushButton("Apply Preset")
        apply_preset_btn.clicked.connect(self._on_apply_preset_clicked)
        header_layout.addWidget(apply_preset_btn)

        save_preset_btn = QtWidgets.QPushButton("Save Preset")
        save_preset_btn.clicked.connect(self._on_save_preset)
        header_layout.addWidget(save_preset_btn)

        reset_btn = QtWidgets.QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_eq)
        header_layout.addWidget(reset_btn)

        layout.addLayout(header_layout)

        slider_frame = QtWidgets.QFrame()
        slider_layout = QtWidgets.QHBoxLayout(slider_frame)
        slider_layout.setSpacing(10)
        slider_layout.setContentsMargins(8, 8, 8, 8)

        for i in range(self.BAND_COUNT):
            col = QtWidgets.QVBoxLayout()
            lbl = QtWidgets.QLabel(self.BAND_LABELS[i] if i < len(self.BAND_LABELS) else f"Band {i+1}")
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setFixedHeight(24)

            s = QtWidgets.QSlider(QtCore.Qt.Vertical)
            s.setRange(-120, 120)
            s.setValue(0)
            s.setSingleStep(1)
            s.setPageStep(10)
            s.setTracking(True)
            s.setToolTip("0.0 dB")
            s.valueChanged.connect(self._on_slider_value_changed)

            val_label = QtWidgets.QLabel("0.0 dB")
            val_label.setAlignment(QtCore.Qt.AlignCenter)
            val_label.setFixedHeight(18)

            s.value_label = val_label

            col.addWidget(lbl)
            col.addStretch(1)
            col.addWidget(s, stretch=5)
            col.addWidget(val_label)
            slider_layout.addLayout(col)

            self.sliders.append(s)

            anim = QtCore.QPropertyAnimation(s, b"value", self)
            anim.setDuration(420)
            anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            self.animations.append(anim)

        layout.addWidget(slider_frame)

        bottom_layout = QtWidgets.QHBoxLayout()
        self.auto_apply_chk = QtWidgets.QCheckBox("Apply automatically on track change")
        self.auto_apply_chk.setChecked(True)
        self.auto_apply_chk.stateChanged.connect(lambda s: setattr(self, "apply_auto_on_change", bool(s)))
        bottom_layout.addWidget(self.auto_apply_chk)

        bottom_layout.addStretch(1)
        self.status_label = QtWidgets.QLabel("Preset: Flat")
        bottom_layout.addWidget(self.status_label)

        layout.addLayout(bottom_layout)

    def _populate_preset_combo(self):
        self.presets = {
            "Flat": [0.0]*self.BAND_COUNT,
            "Rock": [4.0, 3.0, 1.5, -1.0, -1.5, 0.5, 2.0, 3.0, 3.5, 3.8, 3.5],
            "Pop": [-1.0, 2.0, 4.0, 4.0, 2.0, 0.5, -0.5, -1.0, -1.0, -0.5, 0.0],
            "Jazz": [0.5, 1.0, 1.5, 0.5, -0.5, -0.5, 0.0, 1.5, 2.0, 1.5, 0.5],
            "Classical": [0.0, 0.5, 1.0, 1.5, 1.0, 0.0, -0.5, -1.0, -0.5, 0.0, 0.5],
            "Bass Boost": [6.0, 4.5, 3.0, 1.0, -1.0, -2.0, -3.0, -3.0, -3.0, -3.0, -3.0],
            "Treble Boost": [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 6.0],
        }
        if hasattr(self, "user_presets") and isinstance(self.user_presets, dict):
            for k, v in self.user_presets.items():
                if isinstance(v, list) and len(v) == self.BAND_COUNT:
                    self.presets[k] = v

        self.preset_combo.clear()
        for name in sorted(self.presets.keys()):
            self.preset_combo.addItem(name)

    def _on_apply_preset_clicked(self):
        name = self.preset_combo.currentText()
        if not name:
            return
        vals = self.presets.get(name, [0.0]*self.BAND_COUNT)
        for i, s in enumerate(self.sliders):
            target_val = int(round(vals[i] * 10.0))
            anim = self.animations[i]
            anim.stop()
            anim.setStartValue(s.value())
            anim.setEndValue(target_val)
            anim.start()
        self.status_label.setText(f"Preset: {name}")
        QtCore.QTimer.singleShot(460, self.apply_eq_to_engine)

    def _on_save_preset(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not text.strip():
            return
        name = text.strip()
        vals = [s.value() / 10.0 for s in self.sliders]
        self.user_presets[name] = vals
        self._save_user_presets()
        self._populate_preset_combo()
        index = self.preset_combo.findText(name)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        self.status_label.setText(f"Preset saved: {name}")

    def _load_user_presets(self):
        self.user_presets = {}
        try:
            if EQ_PRESETS_FILE.exists():
                raw = EQ_PRESETS_FILE.read_text(encoding="utf-8")
                data = json.loads(raw)
                if isinstance(data, dict):
                    self.user_presets = data
        except Exception as e:
            log_exc_to_file(e)

    def _save_user_presets(self):
        try:
            EQ_PRESETS_FILE.write_text(json.dumps(self.user_presets, indent=2), encoding="utf-8")
        except Exception as e:
            log_exc_to_file(e)

    def reset_eq(self):
        for i, s in enumerate(self.sliders):
            anim = self.animations[i]
            anim.stop()
            anim.setStartValue(s.value())
            anim.setEndValue(0)
            anim.start()
        self.status_label.setText("Preset: Flat")
        QtCore.QTimer.singleShot(460, self.apply_eq_to_engine)

    def _on_slider_value_changed(self, val: int):
        s = self.sender()
        try:
            db = val / 10.0
            if hasattr(s, "value_label"):
                s.value_label.setText(f"{db:.1f} dB")
            self.apply_eq_to_engine()
        except Exception:
            pass

    def apply_eq_to_engine(self):
        try:
            eq_inst = None
            if self.eq is None:
                try:
                    eq_inst = vlc.AudioEqualizer()
                except Exception:
                    try:
                        eq_inst = vlc.audio_equalizer_new()
                    except Exception:
                        eq_inst = None
            else:
                eq_inst = self.eq

            if not eq_inst:
                return

            for i, s in enumerate(self.sliders):
                db_val = float(s.value()) / 10.0
                try:
                    eq_inst.set_amp_at_index(db_val, i)
                except Exception:
                    try:
                        vlc.audio_equalizer_set_amp_at_index(eq_inst, db_val, i)
                    except Exception:
                        pass
            try:
                mp = getattr(self.parent_player, "audio", None)
                if mp and getattr(mp, "player", None) is not None:
                    try:
                        mp.player.set_equalizer(eq_inst)
                    except Exception:
                        try:
                            mp.player.audio_set_equalizer(eq_inst)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception as e:
            log_exc_to_file(e)

    def _do_open_animation(self):
        self.setWindowOpacity(0.0)
        anim = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
