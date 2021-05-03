import os
import re
import time
import config
from lock import lock
from shutil import copyfile, move
from moviepy.editor import VideoFileClip, concatenate_videoclips
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


def parseDateFromGameClip(clip):
    match = re.search('[0-9]{4}\.(0[1-9]|1[0-2])\.(0[1-9]|[1-2][0-9]|3[0-1])', clip) 
    if match:
        return match.group(0)
    else:
        return None

def getGameClips(game):
    gameRoot = f'{config.highlights_root}/{game}'
    filenames = [f for f in os.listdir(gameRoot) if os.path.isfile(f'{gameRoot}/{f}') and os.path.splitext(f'{gameRoot}/{f}')[1] == '.mp4']
    return filenames

def getGameDirectories():
    return os.listdir(config.highlights_root)

def createDir(dirpath):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

def setupFolders():
    print("\tRunning setup...")
    games = getGameDirectories()
    for game in games:
        createDir(f'{config.highlights_root}/{game}/combined')
        createDir(f'{config.highlights_root}/{game}/processed')

def processClip(clip, game):
    print(f'\tprocessing clip: {clip}...')
    date = parseDateFromGameClip(clip)
    combinedFilepath = f'{config.highlights_root}/{game}/combined/{date}.mp4'
    combinedFilepathTemp = f'{config.highlights_root}/{game}/combined/{date}.temp.mp4'
    clipFilepath = f'{config.highlights_root}/{game}/{clip}'
    processedFolder = f'{config.highlights_root}/{game}/processed'
    if not date:
        print(f'\tCould not parse date from clip: {clip}, skipping')
    else:
        if not os.path.exists(combinedFilepath):
            print (f'\tStarting new combined file: {date}.mp4')
            # move clip and title as starting clip
            copyfile(clipFilepath, combinedFilepath)
        else:
            print(f'\tAppending to {date}.mp4, this could take a while...')
            combined = VideoFileClip(combinedFilepath)
            clipToCombine = VideoFileClip(clipFilepath)
            combinedClips = concatenate_videoclips([combined, clipToCombine])
            combinedClips.write_videofile(combinedFilepathTemp, verbose=False)
            move(combinedFilepathTemp, combinedFilepath)
        move(clipFilepath, f'{processedFolder}/{clip}')
        print(f'\tDone processing clip')

def checkAndProcess():
    for game in getGameDirectories():
        clips = getGameClips(game)
        print(f'Creating combined highlights for: {game}')
        print(f'\tFound {len(clips)} clip(s) to process...')
        for clip in clips:
            processClip(clip, game)

def onCreated(event):
    print('--- New Clip Detected!')
    checkAndProcess()
def onMoved(event):
    print('--- New Clip Detected!')
    checkAndProcess()

def initializeObserver():
    # Watcher
    patterns = ["*.mp4"]
    ignorePatterns = ["*/combined/*", "*/processed/*"]
    ignoreDirectories = True
    caseSensitive = True
    myEventHandler = PatternMatchingEventHandler(patterns, ignorePatterns, ignoreDirectories, caseSensitive)
    myEventHandler.on_created = onCreated
    myEventHandler.on_moved = onMoved


    path = config.highlights_root
    myObserver = Observer()
    myObserver.schedule(myEventHandler, path, recursive=True)

    myObserver.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        myObserver.stop()
        myObserver.join()

def main():
    lock()
    print('Starting Highlight Stitcher')
    setupFolders()
    checkAndProcess()
    print('All existing clips have been processed, watching directory for new clips...')
    initializeObserver()

main()