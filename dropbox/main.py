import sys
import time
import os
import zipfile
import hashlib
import json
from watchdog.observers import Observer
import watchdog.events
import dotenv


# Kludge
import sys

sys.path.append(
    os.path.dirname(os.path.realpath(__file__)) + "/../integrity_recorder_id"
)
import integrity_recorder_id

dotenv.load_dotenv()


def prepare_metadata_recorder():
    global metdata_file_timestamp, recorder_meta_all

    current_metadata_file_timestamp = os.path.getmtime(
        integrity_recorder_id.INTEGRITY_PREPROCESSOR_TARGET_PATH
    )

    if current_metadata_file_timestamp > metdata_file_timestamp:
        if os.path.exists(integrity_recorder_id.INTEGRITY_PREPROCESSOR_TARGET_PATH):
            with open(
                integrity_recorder_id.INTEGRITY_PREPROCESSOR_TARGET_PATH, "r"
            ) as f:
                recorder_meta_all = json.load(f)
                print("Recorder Metadata Change Detected")
                metdata_file_timestamp = current_metadata_file_timestamp
    return recorder_meta_all

class MyEventHandler(watchdog.events.PatternMatchingEventHandler):
    def on_created(self, event):
        print("Starting Processing of file")
        sha256asset = sha256sum(event.src_path)

        target="/mnt/integrity_store/starling/internal/starling-lab-test/test-dropbox"
        stagePath=os.path.join(target, "tmp")
        outputPath=os.path.join(target, "input")

        if not os.path.exists(stagePath):
            os.makedirs(stagePath)

        assetFileName=event.src_path
        bundleFileName = os.path.join(stagePath,sha256asset + ".zip")
        content_meta = {}
        recorder_meta = {}
        with zipfile.ZipFile(bundleFileName + ".part", "w") as archive:
            archive.write(assetFileName, os.path.basename(assetFileName))
            archive.writestr(sha256asset + "-meta-content.json", json.dumps(content_meta))
            archive.writestr(sha256asset + "-meta-recorder.json", json.dumps(recorder_meta))
        sha256zip = sha256sum(os.path.join(stagePath,sha256asset + ".zip.part"))
        os.rename(bundleFileName + ".part", os.path.join(outputPath,sha256zip + ".zip"))
            
def sha256sum(filename):
    with open(filename,"rb") as f:
        bytes = f.read() # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash

class WatchFolder:
    'Class defining a scan folder'

    def __init__(self, path,target):
        self.path = path
        self.documents = dict() # key = document label   value = Document reference

        self.event_handler = MyEventHandler(patterns=["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.pdf"],
                                        ignore_patterns=[],
                                        ignore_directories=True)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

path = "/mnt/store/dropbox/Dropbox/integrity-stg-starlinglab-org/"
target = "/mnt/integrity_store/starling/internal/starling-lab-test/test-dropbox"
scan_folder = WatchFolder(path,target)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Keyboard interrupt received.")
scan_folder.stop()
