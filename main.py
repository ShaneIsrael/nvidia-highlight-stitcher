import os
import re
import ffmpeg
import time
import config
from lock import lock
from shutil import copyfile, move
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

def getUncompressedHighlights(game):
    root = f'{config.highlights_root}/{game}/combined'
    filesnames = [f for f in os.listdir(root) if os.path.isfile(f'{root}/{f}') and os.path.splitext(f'{root}/{f}')[1] == '.avi']
    return filesnames

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

def processClips(clips, game, date):
    processedFolder = f'{config.highlights_root}/{game}/processed'
    concat = []
    for clip in clips:
        clipFilepath = f'{config.highlights_root}/{game}/{clip}'
        clipVideo = ffmpeg.input(clipFilepath)
        v = clipVideo.video
        a = clipVideo.audio
        concat.append(v)
        concat.append(a)
    joined = ffmpeg.concat(*concat, v=1, a=1).node
    out = ffmpeg.output(joined[0], joined[1], f'{config.highlights_root}/{game}/combined/{date}.temp.mp4')
    out.global_args('-loglevel', 'error').run()
    move(f'{config.highlights_root}/{game}/combined/{date}.temp.mp4', f'{config.highlights_root}/{game}/combined/{date}.mp4')
    # move clips to process folder
    for clip in clips:
        # ignore clip if it comes from the combined directory
        if 'combined/' in clip:
            continue
        clipFilepath = f'{config.highlights_root}/{game}/{clip}'
        move(clipFilepath, f'{processedFolder}/{clip}')
    print(f'Done processing highlights for date: {date}')

def checkAndProcess():
    for game in getGameDirectories():
        clips = getGameClips(game)
        print(f'Creating combined highlights for: {game}')
        print(f'\tFound {len(clips)} clip(s) to process...')
        batches = {}

        for clip in clips:
            date = parseDateFromGameClip(clip)
            if not date:
                continue
            if date not in batches:
                batches[f'{date}'] = []
            batches[f'{date}'].append(clip)
            
        for key in batches.keys():
            # check if a combined highlight already exists and add to our concat list
            combinedHighlight = f'{config.highlights_root}/{game}/combined/{key}.mp4'
            if os.path.isfile(combinedHighlight):
                batches[key].insert(0, f'combined/{key}.mp4')
            print(f'\tprocessing highlights for date: {key}')
            processClips(batches[key], game, key)


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
    print('All existing clips have been processed')
    # Watching directory may massively drop fps while in game
    #initializeObserver() 

main()