🎧 PyQt5 Music Player

A feature-rich, modern, desktop music player built with Python, PyQt5, and VLC.
It supports lyrics sync, album art extraction, equalizer, queue, playlist management, search, drag-and-drop, and more — all wrapped in a beautiful dark UI powered by qdarktheme.

1️⃣ Install Python modules

You can run:

python install_modules.py

Or manually install:

pip install PyQt5 python-vlc mutagen qdarktheme qtawesome

2️⃣ Run the App

python main.py

✨ Features


🎵 Music Playback


Plays MP3, WAV, OGG, FLAC, M4A, AAC

Smooth seeking slider

Accurate time display

Volume & mute controls

Keyboard shortcuts (Space / ← / →)


📜 Playlist & Queue


Auto-loads songs from the songs/ folder

Add/remove tracks with context menus

Search songs with auto-suggestion

Play queue with double-click to prioritize



🎚 11-Band Built-in Equalizer


Smooth animated sliders

Presets: Rock, Pop, Jazz, Classical, Bass Boost, Treble Boost

Save custom presets

Auto-apply EQ on track change

Uses VLC AudioEqualizer API


🎤 Lyrics Support


Auto-detects lyrics from lyrics/ folder

Supports LRC, SRT, VTT, TXT

Timestamped lyric scrolling

Double-click a lyric line → jump to timestamp

Background workers load lyrics without freezing UI


🖼 Album Art

Extracts embedded art using Mutagen

Smooth fade transition

Fallback to “No Cover”


📥 Add Songs Dialog

Drag & drop audio / lyrics

Browse manually

Auto-rename saved files

Saves to the app-managed folders

🌓 Modern Dark UI

Powered by qdarktheme

Icons by QtAwesome

Clean animations and transitions

🗂 Folder Setup


├── audio_engine.py         # VLC wrapper for playback

├── equalizer_window.py     # 11-band equalizer window

├── install_modules.py      # Auto-installer for required Python modules

├── load_songs_dialog.py    # Add-song dialog with drag/drop

├── lyrics_utils.py         # Parsing for LRC/SRT/VTT/TXT

├── main.py                 # Application entry point

├── metadata_utils.py       # Mutagen metadata + album art

├── music_player.py         # Main UI + playlist, queue, logic

├── paths.py                # Directory paths (songs/, lyrics/, presets)

├── utils.py                # Helpers (timing, formatting, scanning)

├── workers.py              # QThread-based workers for lyrics & art

├── songs/                  # Auto-loaded music

├── lyrics/                 # Auto-loaded lyric files



⌨️ Keyboard Shortcuts

Key	Action

Space	Play / Pause

Left Arrow	Seek −5 seconds

Right Arrow	Seek +5 seconds

Double-click lyric line	Jump to timestamp

Double-click playlist item	Play track


🛠 Development Notes

Uses multiple QThread workers for lyrics and artwork to keep UI responsive

Equalizer is fully integrated with VLC’s native EQ

Binary search used for lyric syncing (fast scrolling)

All exceptions logged into crash.log

Animated artwork fade-in

Smooth animated EQ sliders (OutCubic)


