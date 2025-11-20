from mutagen import File as MutagenFile
from pathlib import Path
from paths import LYRICS_DIR
from typing import List, Optional, Tuple, Dict

SUPPORTED_EXT = ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac')
LYRICS_EXTS = ('.lrc', '.srt', '.vtt', '.vit', '.txt')

_metadata_cache: Dict[str, Tuple[str, str, int]] = {}
_art_cache: Dict[str, Optional[bytes]] = {}

def human_time(ms: int) -> str:
    if ms is None or ms <= 0:
        return "00:00"
    s = int(ms // 1000)
    m = s // 60
    s = s % 60
    return f"{m:02d}:{s:02d}"

def scan_folder_for_songs(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    out = []
    for f in sorted(folder.rglob("*")):
        if f.suffix.lower() in SUPPORTED_EXT:
            out.append(f)
    return out

def read_text_file(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="latin1")
        except Exception:
            return None

def get_metadata(path: Path) -> Tuple[str, str, int]:
    key = str(path)
    if key in _metadata_cache:
        return _metadata_cache[key]
    title = path.name
    artist = ""
    duration = 0
    try:
        m = MutagenFile(str(path), easy=True)
        if m:
            title = m.get('title', [title])[0]
            artist = m.get('artist', [''])[0]
            info = getattr(m, "info", None)
            if info:
                length = getattr(info, "length", None)
                if length:
                    duration = int(length * 1000)
    except Exception:
        pass
    _metadata_cache[key] = (title, artist, duration)
    return title, artist, duration

def extract_embedded_art(path: Path):
    key = str(path)
    if key in _art_cache:
        return _art_cache[key]
    data = None
    try:
        m = MutagenFile(str(path))
        if not m:
            data = None
        else:
            try:
                if hasattr(m, "tags") and m.tags is not None:
                    for v in m.tags.values():
                        d = getattr(v, "data", None)
                        if d:
                            data = d
                            break
            except Exception:
                pass
            if data is None:
                try:
                    pics = getattr(m, "pictures", None)
                    if pics:
                        if isinstance(pics, (list, tuple)) and pics:
                            data = pics[0].data
                        elif hasattr(pics, "data"):
                            data = pics.data
                except Exception:
                    pass
    except Exception:
        data = None
    _art_cache[key] = data
    return data

def find_lyrics_file(song_path: Path) -> Optional[Path]:
    base = song_path.stem
    for ext in LYRICS_EXTS:
        candidate = LYRICS_DIR / f"{base}{ext}"
        if candidate.exists():
            return candidate
    if LYRICS_DIR.exists():
        for f in LYRICS_DIR.iterdir():
            if f.is_file() and f.stem.lower() == base.lower() and f.suffix.lower() in LYRICS_EXTS:
                return f
    return None

def clear_caches_for_path(path: Path):
    key = str(path)
    if key in _metadata_cache:
        del _metadata_cache[key]
    if key in _art_cache:
        del _art_cache[key]
