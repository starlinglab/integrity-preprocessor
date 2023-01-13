from copy import deepcopy
import io
import datetime
import dotenv
import hashlib
import json
import os
import sys
import time
import watchdog.events
from zipfile import ZipFile
import magic
import csv
import base64

from watchdog.observers import Observer

# Kludge
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import validate
import integrity_recorder_id
import common

dotenv.load_dotenv()

CONFIG_FILE = os.environ.get("CONFIG_FILE")

logging = common.logging
logging.info("Started folder preprocessor")

metdata_file_timestamp = -1


def _mkdir_recursive(path, uid, gid):
    sub_path = os.path.dirname(path)
    if not os.path.exists(sub_path):
        _mkdir_recursive(sub_path, uid, gid)
    if not os.path.exists(path):
        os.mkdir(path)
        os.chown(path, uid, gid)
        logging.info("Creating folder " + path)


def _check_if_file_is_open(filename, lock_file):

    if lock_file != "":
        if os.path.exists(lock_file):
            return True

    for entry_name in os.listdir("/proc"):
        if entry_name.isnumeric():
            entry_path = os.path.join("/proc", entry_name, "fd")
            try:
                for file_name in os.listdir(entry_path):
                    if os.path.exists(os.path.join(entry_path, file_name)):
                        if filename == os.readlink(os.path.join(entry_path, file_name)):
                            return True
            except:
                pass

def _wait_for_file_to_close(filename, lock_file):
    while _check_if_file_is_open(filename, lock_file):
        print(f"Waiting on file {filename}")
        time.sleep(5)

class watch_folder:
    """Class defining a folder to watch"""
    event_handler = None
    legacy_dup_check=[]
    def __init__(self, conf):

        # Create source path if it does not exist
        # Make sure its uid 1001,1001 (docker container user)
        if os.path.exists(conf["sourcePath"]) == False:
            _mkdir_recursive(conf["sourcePath"], 1001, 1001)

        # remember path being watched,  any configs for this folder
        self.path = conf["sourcePath"]
        self.config = conf

        # Start watcher for the allewed extensions only
        patterns = conf["allowedPatterns"]
        self.event_handler = watchdog.events.PatternMatchingEventHandler(
            patterns=patterns, ignore_patterns=[], ignore_directories=True
        )        
        self.event_handler.on_created = self.on_created
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=False)
        self.observer.start()
        logging.info("Watching " + self.path + " for " + ",".join(patterns))

    def on_created(self, event):
        """Function that is triggered whenever a new file is created in a watched folder"""

        source_filename = event.src_path # File being created 

        target = self.config["targetPath"] # Output Path
        stage_path = os.path.join(target, "tmp")
        output_path = os.path.join(target, "input") 

        if not os.path.exists(stage_path):
            os.makedirs(stage_path)

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # Skip index.json if it exists
        if os.path.basename(source_filename) == "index.json":
            logging.info(f"Skipping index.json file")
            return

        # Check for legacy starling capture assets are being processed manually
        # It will wait for all 3 (asset + metadata + signature) to be created before proceeding
        legacy_base = ""
        if (
            "processLegacyStarlingCapture" in self.config
            and self.config["processLegacyStarlingCapture"]
        ):
            logging.info(f"Processing Starling Legacy Assets")
            # Check if all 3 files are present
            tmp = os.path.splitext(source_filename)
            legacy_base = tmp[0]
            ext = tmp[1]
            if ext == ".json":
                legacy_base = legacy_base[: legacy_base.rindex("-")]
            source_filename = f"{legacy_base}.jpg"
            if source_filename in self.legacy_dup_check:
                logging.info(f"Already processed {source_filename} this asset, skipping")
                return
            if not os.path.exists(f"{legacy_base}.jpg"):
                logging.info(f"Skipping - Missing Asset")
                return
            if not os.path.exists(f"{legacy_base}-meta.json"):
                logging.info(f"Skipping - Missing Meta")
                return
            if not os.path.exists(f"{legacy_base}-signature.json"):
                logging.info(f"Skipping - Missing Signature")
                return
            logging.info(
                f"Found all 3 files - merging Starling Backend Legacy Content {source_filename}"
            )
            self.legacy_dup_check.append(source_filename)

        logging.info(f"Start Processing of file {source_filename}")        

        # Wait for file lock is available, and that file is closed and not being written to
        lock_file = ""
        if "lockFile" in self.config:
            lock_file = self.config["lockFile"]
        _wait_for_file_to_close(source_filename, lock_file)

        content_metadata = common.metadata()
        content_metadata.set_mime_from_file(source_filename)
        
        meta_method = "Generic"
        if "method" in self.config:
            meta_method = self.config["method"]
        content_metadata.description(f"{meta_method.title()} document")


        # Name of filename that will be matched in the index.jsopn
        # This can differ if (for example) name is prepended to it
        index_filename = file_name = os.path.basename(source_filename)
        source_path = os.path.dirname(source_filename)

        extra_folder = { 
            "uploadFilename": file_name,
            "uploadDirectory": source_path
        }

        # If extractName is enabled (dropbox), parse out the uploader name based on extractNameCharacters
        extractName = False
        extractNameCharacters = " ___ "
        if "extractName" in self.config:
            extractName = self.config["extractName"]
            if "extractNameCharacters" in self.config:
                extractNameCharacters = self.config["extractNameCharacters"]

        if extractName:
            tmp = file_name.split(extractNameCharacters, 2)
            if len(tmp) == 2:
                extra_folder["uploaderName"]=tmp[0]
                index_filename = tmp[1]
            else:
                extra_folder["uploaderName"]=""
                index_filename = tmp[0]
        content_metadata.add_private_key({"folder": extra_folder})

        # use the OS's file created date as dateCreate
        content_metadata.createdate_utcfromtimestamp(os.path.getmtime(source_filename))

        # Content specific processing
        if "processWacz" in self.config and self.config["processWacz"]:
            content_metadata.process_wacz(source_filename)
        if "processProofmode" in self.config and self.config["processProofmode"]:
            content_metadata.process_proofmode(source_filename)
        if (
            "processLegacyStarlingCapture" in self.config
            and self.config["processLegacyStarlingCapture"]
        ):
            content_metadata.process_legacy_starling_capture(f"{legacy_base}.jpg",f"{legacy_base}-meta.json",f"{legacy_base}-signature.json")

        # Read entries in config file, if it exists, and apply changes
        if "description" in self.config:
            content_metadata.set_description(self.config["description"])

        if "name" in self.config:
            content_metadata.set_name(self.config["name"])

        # Top level config overwrites
        if "author" in self.config:
            content_metadata.author(self.config["author"])

        # Read entries from index, if it exists, and apply changes
        if os.path.exists(f"{source_path}/index.json"):
            index_file = open(f"{source_path}/index.json", "r")
            index = json.load(index_file)
            index_data = None
            for item in index:
                if item["filename"] == index_filename:
                    content_metadata.set_index(item)

        recorder_meta = common.get_recorder_meta("folder")
        out_file = common.add_to_pipeline(
            source_filename, content_metadata.get_content(), recorder_meta, stage_path, output_path
        )
        logging.info(f"{source_filename} Created new asset {out_file}")

    def stop(self):
        self.observer.stop()
        self.observer.join()


config = {}
scan_folder = []
with open(CONFIG_FILE) as f:
    config = json.load(f)
    for item in config:
        scan_folder.append(watch_folder(config[item]))

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logging.info("Keyboard interrupt received.")

for item in scan_folder:
    item.stop()
