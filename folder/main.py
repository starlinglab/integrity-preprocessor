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

from watchdog.observers import Observer

# Kludge
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import integrity_recorder_id
import common

dotenv.load_dotenv()

CONFIG_FILE = os.environ.get("CONFIG_FILE")

logging = common.logging
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
    meta_date_created,
    sourcePath,
    uploader_name,
    meta_extras,
    meta_private,
    meta_method,
    author,
    index_data,
):

    # guess mime type
    mime = magic.Magic(mime=True)
    meta_mime_type = mime.from_file(sourcePath)

    extras = meta_extras
    private = meta_private

    meta_content = default_content

    if author:
        meta_content["author"] = author

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

    if index_data:
        if "description" in index_data:
            meta_content["description"] = index_data["description"]
        if "sourceId" in index_data:
            meta_content["sourceId"] = index_data["sourceId"]
        if "meta_data_private" in index_data:
            for item in index_data["meta_data_private"]:
                private[item] = index_data["meta_data_private"][item]
        if "meta_data_public" in index_data:
            for item in index_data["meta_data_public"]:
                extras[item] = index_data["meta_data_public"][item]

    meta_content["extras"] = extras
    meta_content["private"] = private

    return meta_content


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
        time.sleep(10)


class watch_folder:
    "Class defining a scan folder"
    event_handler = None

    def __init__(self, conf):
        if os.path.exists(conf["sourcePath"]) == False:
            _mkdir_recursive(conf["sourcePath"], 1001, 1001)
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
        # Skip index.json if it exists

        target_filename = event.src_path
        if os.path.basename(target_filename) == "index.json":
            logging.info(f"Skipping index.json file")
            return

        if (
            "processLegacyStarlingCapture" in self.config
            and self.config["processLegacyStarlingCapture"]
        ):
            # Check if all 3 files are present
            tmp = os.path.splitext(target_filename)
            legacy_base = tmp[0]
            ext = tmp[1]
            if ext == ".json":
                legacy_base = legacy_base[: legacy_base.rindex("-")]
            if not os.path.exists(f"{legacy_base}.jpg"):
                logging.info(f"Missing Asset")
                return
            if not os.path.exists(f"{legacy_base}-meta.json"):
                logging.info(f"Missing Meta")
                return
            if not os.path.exists(f"{legacy_base}-signature.json"):
                logging.info(f"Missing Signature")
                return
            target_filename = f"{legacy_base}.jpg"
            logging.info(
                f"Continuing merging Starling Backend Legacy Content {target_filename}"
            )

        logging.info(f"Starting Processing of file {target_filename}")
        sha256asset = common.sha256sum(target_filename)

        lock_file = ""
        if "lockFile" in self.config:
            lock_file = self.config["lockFile"]
        _wait_for_file_to_close(target_filename, lock_file)
        target = self.config["targetPath"]

        extractName = False
        extractNameCharacters = " ___ "
        if "extractName" in self.config:
            extractName = self.config["extractName"]
            if "extractNameCharacters" in self.config:
                extractNameCharacters = self.config["extractNameCharacters"]

        author = None
        if "author" in self.config:
            author = self.config["author"]

        meta_method = "Generic"
        if "method" in self.config:
            meta_method = self.config["method"]

        stage_path = os.path.join(target, "tmp")
        output_path = os.path.join(target, "input")

        if not os.path.exists(stage_path):
            os.makedirs(stage_path)

        asset_filename = target_filename
        meta_uploader_name = ""
        index_filename = ""
        if extractName:
            fileName = os.path.basename(target_filename)
            tmp = fileName.split(extractNameCharacters, 2)
            if len(tmp) == 2:
                meta_uploader_name = tmp[0]
                index_filename = tmp[1]
            else:
                meta_uploader_name = ""
                index_filename = tmp[0]

        bundleFileName = os.path.join(stage_path, sha256asset + ".zip")

        meta_date_create = os.path.getmtime(asset_filename)

        extras = {}
        private = {}
        if "processWacz" in self.config and self.config["processWacz"]:
            logging.info(f"{asset_filename} Processing file as a WACZ")
            extras = common.parse_wacz_data_extra(asset_filename)
        if "processProofMode" in self.config and self.config["processProofMode"]:
            logging.info(f"{asset_filename} Processing file as a ProofMode")
            extras = common.parse_proofmode_data(asset_filename)

        if (
            "processLegacyStarlingCapture" in self.config
            and self.config["processLegacyStarlingCapture"]
        ):
            meta_method = "Starling Capture"
            private["starlingCapture"] = {}
            # Parsing lines since some files come with duplicate lines breaking json format
            with open(f"{legacy_base}-meta.json") as file_meta:
                lines = file_meta.readlines()
                if len(lines) > 1:
                    if lines[0] != lines[1]:
                        logging.info(f"{asset_filename} - Error lines do not match")
                        exit
                content_meta = json.loads(lines[0])
                private["starlingCapture"]["metadata"] = content_meta
            with open(f"{legacy_base}-signature.json") as file_meta:
                lines = file_meta.readlines()
                if len(lines) > 1:
                    if lines[0] != lines[1]:
                        logging.info(f"{asset_filename} - Error lines do not match")
                        exit
                content_meta = json.loads(lines[0])
                private["starlingCapture"]["signature"] = content_meta

        # read index file if it exists
        source_path = os.path.dirname(asset_filename)

        index_data = None

        if os.path.exists(f"{source_path}/index.json"):
            index_file = open(f"{source_path}/index.json", "r")
            index = json.load(index_file)
            index_data = None
            for item in index:
                if item["filename"] == index_filename:
                    index_data = item
                    break
        content_meta = generate_metadata_content(
            meta_date_create,
            asset_filename,
            meta_uploader_name,
            extras,
            private,
            meta_method,
            author,
            index_data,
        )
        recorder_meta = common.get_recorder_meta("folder")
        out_file = common.add_to_pipeline(
            asset_filename, content_meta, recorder_meta, stage_path, output_path
        )
        logging.info(f"{asset_filename} Created new asset {out_file}")

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
