import sys
from filelock import Timeout, FileLock

lockfile = "process.lock"
filelock = FileLock(lockfile, timeout=1)

def lock():
    try:
        filelock.acquire()
    except:
        print("Another instance of this application currently running.")
        sys.exit(1)
