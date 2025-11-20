import traceback
from pathlib import Path
import sys

CRASH_LOG = Path("crash.log")

def log_exc_to_file(exc: Exception = None):
    try:
        with CRASH_LOG.open("a", encoding="utf-8") as fh:
            fh.write("==== Exception / Traceback ====\n")
            if exc:
                fh.write(str(exc) + "\n")
            traceback.print_exc(file=fh)
            fh.write("\n")
    except Exception:
        pass

def handle_uncaught(exctype, value, tb):
    try:
        with CRASH_LOG.open("a", encoding="utf-8") as fh:
            fh.write("==== Uncaught Exception ====\n")
            traceback.print_exception(exctype, value, tb, file=fh)
            fh.write("\n")
    except Exception:
        pass
    traceback.print_exception(exctype, value, tb)

sys.excepthook = handle_uncaught
