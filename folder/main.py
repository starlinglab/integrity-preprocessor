import copy
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
import logging

from watchdog.observers import Observer

# Kludge
sys.path.append(
    os.path.dirname(os.path.realpath(__file__)) + "/../lib"
)
import integrity_recorder_id
import common

dotenv.load_dotenv()

CONFIG_FILE = os.environ.get("CONFIG_FILE")

logging.basicConfig(
    filename=None,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
common.logging=logging
logging.info("Started folder preprocessor")



default_author = {
    "@type": "Organization",
    "identifier": "https://starlinglab.org",
    "name": "Starling Lab",
}

default_content = {
    "name": "Web archive",
    "mime": "application/wacz",
    "description": "Archive collected by browsertrix-cloud",
    "author": default_author,
}


def generate_metadata_content(
    meta_date_created, sourcePath, uploader_name, meta_extras, meta_method
):

    # guess mime type
    mime = magic.Magic(mime=True)
    meta_mime_type = mime.from_file(sourcePath)

    extras = meta_extras
    private = {}

    meta_content = default_content

    meta_content["description"] = f"{meta_method.title()} document "

    if "waczTitle" in extras:
        meta_content["name"] = f"WebArchive - {extras['waczTitle']}"
        meta_content[
            "description"
        ] = f"WebArchive {extras['waczTitle']} uploaded via {meta_method}"
    else:
        meta_content["name"] = f"File via {meta_method}"
        meta_content["description"] = f"File uploaded via {meta_method}"
        meta_content["mime"] = meta_mime_type

    create_datetime = datetime.datetime.utcfromtimestamp(meta_date_created)
    meta_content["dateCreated"] = create_datetime.isoformat() + "Z"
    meta_content["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    if uploader_name != "":
        private["uploaderName"] = uploader_name

    private["uploadDirectory"] = os.path.dirname(sourcePath)
    private["uploadFilename"] = os.path.basename(sourcePath)

    meta_content["extras"] = extras
    meta_content["private"] = private

    return {"contentMetadata": meta_content}


metdata_file_timestamp = -1



class watch_folder:
    "Class defining a scan folder"
    event_handler = None

    def __init__(self, conf):
        if os.path.exists(conf["sourcePath"]) == False:
            os.mkdir(conf["sourcePath"])
            os.chown(conf["sourcePath"], 1001, 1001)
            logging.info("Creating folder " + conf["sourcePath"])
        os.chown(conf["sourcePath"], 1001, 1001)
        self.path = conf["sourcePath"]
        self.config = conf
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
        logging.info(f"Starting Processing of file {event.src_path}")
        sha256asset = common.sha256sum(event.src_path)

        target = self.config["targetPath"]
        extractName = False
        if "extractName" in self.config:
            extractName = self.config["extractName"]

        meta_method = "Generic"
        if "method" in self.config:
            meta_method = self.config["method"]

        stagePath = os.path.join(target, "tmp")
        outputPath = os.path.join(target, "input")

        if not os.path.exists(stagePath):
            os.makedirs(stagePath)

        assetFileName = event.src_path
        meta_uploader_name = ""
        if extractName:
            fileName = os.path.basename(event.src_path)

            tmp = fileName.split(" ___ ", 2)
            if len(tmp) == 2:
                meta_uploader_name = tmp[0]
            else:
                meta_uploader_name = ""

        bundleFileName = os.path.join(stagePath, sha256asset + ".zip")

        meta_date_create = os.path.getmtime(assetFileName)

        extras = {}
        if "processWacz" in self.config and self.config["processWacz"]:
            logging.info(f"{assetFileName} Processing file as a wacz")
            extras = common.parse_wacz_data_extra(assetFileName)
        if "processProofMode" in self.config and self.config["processProofMode"]:
            logging.info(f"{assetFileName} Processing file as a ProofMode")
            extras = common.parse_proofmode_data(assetFileName)

        content_meta = generate_metadata_content(
            meta_date_create, assetFileName, meta_uploader_name, extras, meta_method
        )
        recorder_meta = common.get_recorder_meta("folder")

        
        out_file = common.add_to_pipeline(assetFileName, content_meta, recorder_meta, stagePath, outputPath)
        logging.info(f"{assetFileName} Created new asset {out_file}")


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
