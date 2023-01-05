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

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import validate


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
    index_data
):

    # guess mime type
    mime = magic.Magic(mime=True)
    meta_mime_type = mime.from_file(sourcePath)

    extras = meta_extras
    private = meta_private

    meta_content = deepcopy(default_content)

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
        if "relatedAssetCid" in index_data:
            meta_content["relatedAssetCid"] = index_data["relatedAssetCid"]
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

        legacy_base = ""
        if (
            "processLegacyStarlingCapture" in self.config
            and self.config["processLegacyStarlingCapture"]
        ):
            logging.info(f"Processing Starling Legacy Assets")
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

        stage_path = os.path.join(target, "tmp")
        output_path = os.path.join(target, "input")

        if not os.path.exists(stage_path):
            os.makedirs(stage_path)

        content_metadata = common.metadata()
        content_metadata.set_mime_from_file(target_filename)
        
        print(content_metadata.get_content())
        if "author" in self.config:
            content_metadata.author(self.config["author"])

        meta_method = "Generic"
        if "method" in self.config:
            meta_method = self.config["method"]
        content_metadata.description(f"{meta_method.title()} document")

        asset_filename = target_filename
        meta_uploader_name = ""
        index_filename = os.path.basename(target_filename)

        if extractName:
            fileName = os.path.basename(target_filename)
            tmp = fileName.split(extractNameCharacters, 2)
            if len(tmp) == 2:
                content_metadata.add_private_element("uploaderName",tmp[0])
                index_filename = tmp[1]
            else:
                content_metadata.add_private_element("uploaderName","")
                index_filename = tmp[0]

        content_metadata.createdate_utcfromtimestamp(os.path.getmtime(asset_filename))
        if "processWacz" in self.config and self.config["processWacz"]:
            content_metadata.process_wacz(asset_filename)
        if "processProofmode" in self.config and self.config["processProofmode"]:
            content_metadata.process_proofmode(asset_filename)

        if (
            "processLegacyStarlingCapture" in self.config
            and self.config["processLegacyStarlingCapture"]
        ):
            meta_method = "Starling Capture"
            private={}
            private["starlingCapture"] = {}
            # Parsing lines since some files come with duplicate lines breaking json format
            with open(f"{legacy_base}-meta.json") as file_meta:
                lines = file_meta.readlines()
                if len(lines) > 1:
                    if lines[0] != lines[1]:
                        logging.info(f"{asset_filename} - Error lines do not match")
                        exit
                        #contentMetadata.private.starlingCapture.metadata.proof.timestamp
                metadata_json = json.loads(lines[0])
                private["starlingCapture"]["metadata"] = metadata_json
                create_timestamp = private["starlingCapture"]["metadata"]["proof"]["timestamp"]
                meta_date_create = int(create_timestamp/1000)
            with open(f"{legacy_base}-signature.json") as file_meta:
                lines = file_meta.readlines()
                if len(lines) > 1:
                    if lines[0] != lines[1]:
                        logging.info(f"{asset_filename} - Error lines do not match")
                        exit
                
                signature_json = json.loads(lines[0])
                private["starlingCapture"]["signatures"] = signature_json
            # FIX Metadata bug
            metadata_json_fix=deepcopy(metadata_json)
            metadata_json_fix["information"]=[]
            metadata_json_fix=json.dumps(metadata_json_fix)
            metadata_json_fix=metadata_json_fix.replace(" ","")
            sc = validate.StarlingCapture(f"{legacy_base}.jpg", metadata_json_fix, signature_json)
            if not sc.validate():
                raise ClientError("Hashes or signatures did not validate")
            validatedSignatures=sc.validated_sigs_json()

            metadata_byte = metadata_json_fix.encode("ascii")
            metadata_base64_bytes = base64.b64encode(metadata_byte)
            base64_string = metadata_base64_bytes.decode("ascii")            

            private["starlingCapture"]["signatures"][0]["b64AuthenticatedMetadata"] = base64_string
            content_metadata.add_private_key(private)
        # read index file if it exists
        source_path = os.path.dirname(asset_filename)



        if os.path.exists(f"{source_path}/index.json"):
            index_file = open(f"{source_path}/index.json", "r")
            index = json.load(index_file)
            index_data = None
            for item in index:
                if item["filename"] == index_filename:
                    content_metadata.set_index(item)

        if "description" in self.config:
            content_metadata.set_description(self.config["description"])

        if "name" in self.config:
            content_metadata.set_name(self.config["name"])

        recorder_meta = common.get_recorder_meta("folder")
        out_file = common.add_to_pipeline(
            asset_filename, content_metadata.get_content(), recorder_meta, stage_path, output_path
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
