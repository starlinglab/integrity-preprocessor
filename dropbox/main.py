import sys
import time
import os
import zipfile
import hashlib
import json
from watchdog.observers import Observer
import watchdog.events
import datetime
import dotenv

dotenv.load_dotenv()

CONFIG_FILE = os.environ.get("CONFIG_FILE")

# Kludge
import sys

sys.path.append(
    os.path.dirname(os.path.realpath(__file__)) + "/../integrity_recorder_id"
)
import integrity_recorder_id

dotenv.load_dotenv()

default_author = {
    "@type": "Organization",
    "identifier": "https://starlinglab.org",
    "name": "Starling Lab",
}

default_content = {
    "name": "Web archive",
    "mine": "application/wacz",
    "description": "Archive collected by browsertrix-cloud",
    "author": default_author,
}

def generate_metadata_content(meta_date_created,dropboxPath,uploader_name):
    extras = {
        "dropboxPath": dropboxPath
    }
    private = {}

    meta_content={}
    create_datetime = datetime.datetime.utcfromtimestamp(meta_date_created)
    meta_content["dateCreated"] = create_datetime.isoformat() + "Z"
    meta_content["extras"] = extras
    meta_content["private"] = private
    meta_content["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    if uploader_name != "":
        meta_content["private"]['uploaderName'] = uploader_name
    return {"contentMetadata": meta_content}

metdata_file_timestamp  = -1
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
       
            
def sha256sum(filename):
    with open(filename,"rb") as f:
        bytes = f.read() # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash

class WatchFolder:
    'Class defining a scan folder'
    event_handler = None
    def __init__(self,conf):
        self.path = conf["sourcePath"]        
        self.config = conf        
        patterns = conf['allowedPatterns']
        self.event_handler = watchdog.events.PatternMatchingEventHandler(patterns=patterns ,
                                        ignore_patterns=[],
                                        ignore_directories=True)
        self.event_handler.on_created = self.on_created
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=False)
        self.observer.start()
        print("Watching " + self.path + " for " + ",".join(patterns))

    def on_created(self, event):
        print(f"Starting Processing of file {event.src_path}")
        sha256asset = sha256sum(event.src_path)

        target=self.config['targetPath']
        extractName = False
        if "extractName" in self.config:
            extractName=self.config['extractName']

        stagePath=os.path.join(target, "tmp")
        outputPath=os.path.join(target, "input")

        if not os.path.exists(stagePath):
            os.makedirs(stagePath)

        assetFileName=event.src_path
        meta_uploader_name = ""
        if extractName:
            fileName = os.path.basename(event.src_path)
            tmp = fileName.split(" ___ ",2)
            meta_uploader_name=tmp[0]
            
        bundleFileName = os.path.join(stagePath,sha256asset + ".zip")
                
        meta_date_create = os.path.getmtime(assetFileName)
        meta_assetpath = os.path.dirname(assetFileName)

        content_meta=generate_metadata_content(meta_date_create,meta_assetpath, meta_uploader_name)
        recorder_meta = prepare_metadata_recorder()

        with zipfile.ZipFile(bundleFileName + ".part", "w") as archive:
            archive.write(assetFileName, os.path.basename(assetFileName))
            archive.writestr(sha256asset + "-meta-content.json", json.dumps(content_meta))
            archive.writestr(sha256asset + "-meta-recorder.json", json.dumps(recorder_meta))
        sha256zip = sha256sum(os.path.join(stagePath,sha256asset + ".zip.part"))
        os.rename(bundleFileName + ".part", os.path.join(outputPath,sha256zip + ".zip"))


    def stop(self):
        self.observer.stop()
        self.observer.join()

config={}
scan_folder = []
with open(CONFIG_FILE) as f:
    config = json.load(f)
    for item in config:
        scan_folder.append(WatchFolder(config[item]))

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Keyboard interrupt received.")

for item in scan_folder:
    item.stop()
