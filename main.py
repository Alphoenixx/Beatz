import sys
from PyQt5 import QtWidgets
import qdarktheme
from music_player import MusicPlayer
from paths import SONGS_DIR, LYRICS_DIR

def main():
    app = QtWidgets.QApplication(sys.argv)

    try:
        app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    except Exception:
        pass

    SONGS_DIR.mkdir(exist_ok=True)
    LYRICS_DIR.mkdir(exist_ok=True)

    window = MusicPlayer()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
