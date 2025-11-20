import re
from typing import List, Tuple

def parse_lrc(text: str) -> List[Tuple[int, str]]:
    pattern = re.compile(r'\[(\d+):(\d+(?:\.\d+)?)\]')
    out = []
    for raw in text.splitlines():
        timestamps = pattern.findall(raw)
        if not timestamps:
            continue
        lyric = pattern.sub('', raw).strip()
        for (mm, ss) in timestamps:
            try:
                minutes = int(mm)
                seconds = float(ss)
                ms = int((minutes * 60 + seconds) * 1000)
                out.append((ms, lyric))
            except Exception:
                continue
    return sorted(out, key=lambda x: x[0])

def parse_srt(text: str) -> List[Tuple[int, str]]:
    pattern = re.compile(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})')
    out = []
    blocks = re.split(r'\n\s*\n', text.strip())
    for b in blocks:
        lines = b.strip().splitlines()
        if len(lines) < 2:
            continue
        time_line = None
        for ln in lines:
            if '-->' in ln:
                time_line = ln
                break
        if not time_line:
            continue
        m1 = pattern.search(time_line)
        if not m1:
            continue
        try:
            h = int(m1.group(1)); mm = int(m1.group(2)); ss = int(m1.group(3)); ms = int(m1.group(4))
            start_ms = ((h * 3600) + (mm * 60) + ss) * 1000 + ms
        except Exception:
            continue
        idx = lines.index(time_line)
        lyric = ' '.join(l.strip() for l in lines[idx+1:] if l.strip())
        out.append((start_ms, lyric))
    return sorted(out, key=lambda x: x[0])

def parse_vtt(text: str) -> List[Tuple[int, str]]:
    pattern = re.compile(r'(\d{2}):(\d{2}):(\d{2})\.(\d{1,3})')
    out = []
    blocks = re.split(r'\n\s*\n', text.strip())
    for b in blocks:
        lines = b.strip().splitlines()
        if len(lines) < 2:
            continue
        time_line = None
        for ln in lines:
            if '-->' in ln:
                time_line = ln
                break
        if not time_line:
            continue
        m1 = pattern.search(time_line)
        if not m1:
            m2 = re.search(r'(\d{2}):(\d{2})\.(\d{1,3})', time_line)
            if m2:
                try:
                    minutes = int(m2.group(1)); seconds = int(m2.group(2)); ms = int(m2.group(3).ljust(3, '0'))
                    start_ms = (minutes * 60 + seconds) * 1000 + ms
                except Exception:
                    continue
            else:
                continue
        else:
            try:
                h = int(m1.group(1)); mm = int(m1.group(2)); ss = int(m1.group(3)); ms = int(m1.group(4).ljust(3, '0'))
                start_ms = ((h * 3600) + (mm * 60) + ss) * 1000 + ms
            except Exception:
                continue
        idx = lines.index(time_line)
        lyric = ' '.join(l.strip() for l in lines[idx+1:] if l.strip())
        out.append((start_ms, lyric))
    return sorted(out, key=lambda x: x[0])

def parse_lyrics_by_suffix(text: str, suffix: str):
    suffix = suffix.lower()
    if suffix == '.lrc':
        return parse_lrc(text)
    if suffix == '.srt':
        return parse_srt(text)
    if suffix in ('.vtt', '.vit'):
        return parse_vtt(text)
    if suffix == '.txt':
        lines = [ln for ln in text.splitlines() if ln.strip()]
        out = []
        t = 0
        for ln in lines:
            out.append((t, ln.strip()))
            t += 1500
        return out
    return parse_lrc(text)
