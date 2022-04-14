import datetime
import dotenv
import hashlib
import json
import os
import sys
import time
import watchdog.events
import zipfile

from watchdog.observers import Observer

# Kludge
sys.path.append(
    os.path.dirname(os.path.realpath(__file__)) + "/../integrity_recorder_id"
)
import integrity_recorder_id

dotenv.load_dotenv()

CONFIG_FILE = os.environ.get("CONFIG_FILE")

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


def generate_metadata_content(
    meta_date_created, dropboxPath, uploader_name, meta_extras
):
    extras = meta_extras
    private = {}

    meta_content = default_content

    meta_content["description"] = "Web archive uploaded to Dropbox"

    if "waczTitle" in extras:
        meta_content["name"] = f"WebArchive - {extras['waczTitle']}"
    else:
        meta_content["name"] = f"WebArchive"

    create_datetime = datetime.datetime.utcfromtimestamp(meta_date_created)
    meta_content["dateCreated"] = create_datetime.isoformat() + "Z"
    meta_content["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    if uploader_name != "":
        private["uploaderName"] = uploader_name
    private["uploadDirectory"] = os.path.dirname(dropboxPath)
    private["uploadFilename"] = os.path.basename(dropboxPath)

    meta_content["extras"] = extras
    meta_content["private"] = private

    return {"contentMetadata": meta_content}


metdata_file_timestamp = -1


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
    with open(filename, "rb") as f:
        bytes = f.read()  # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash


def processWacz(wacz_path):
    # WACZ metadata extraction
    with zipfile.ZipFile(wacz_path, "r") as wacz:
        d = json.loads(wacz.read("datapackage-digest.json"))
        if "signedData" in d:

            extras = {}

            # auth sign data
            if "authsignDomain" in d["signedData"]:
                extras["authsignSoftware"] = d["signedData"]["software"]
                extras["authsignDomain"] = d["signedData"]["domain"]
            elif "publicKey" in d["signedData"]:
                extras["localsignSoftware"] = d["signedData"]["software"]
                extras["localsignPublicKey"] = d["signedData"]["publicKey"]
                extras["localsignSignaturey"] = d["signedData"]["signature"]
            else:
                logging.info("WACZ missing signature ")

        d = json.loads(wacz.read("datapackage.json"))
        extras["waczVersion"] = d["wacz_version"]
        extras["software"] = d["software"]
        extras["dateCrawled"] = d["created"]
        extras["waczTitle"] = d["title"]

        extras["pages"] = {}
        if "pages/pages.jsonl" in wacz.namelist():
            with wacz.open("pages/pages.jsonl") as jsonl_file:
                for line in jsonl_file.readlines():
                    d = json.loads(line)
                    if "url" in d:
                        extras["pages"][d["id"]] = d["url"]
        else:
            logging.info("Missing pages/pages.jsonl in archive %s", aid)

        return extras

class WatchFolder:
    "Class defining a scan folder"
    event_handler = None

    def __init__(self, conf):
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
        print("Watching " + self.path + " for " + ",".join(patterns))

    def on_created(self, event):
        print(f"Starting Processing of file {event.src_path}")
        sha256asset = sha256sum(event.src_path)

        target = self.config["targetPath"]
        extractName = False
        if "extractName" in self.config:
            extractName = self.config["extractName"]

        stagePath = os.path.join(target, "tmp")
        outputPath = os.path.join(target, "input")

        if not os.path.exists(stagePath):
            os.makedirs(stagePath)

        assetFileName = event.src_path
        meta_uploader_name = ""
        if extractName:
            fileName = os.path.basename(event.src_path)
            tmp = fileName.split(" ___ ", 2)
            meta_uploader_name = tmp[0]

        bundleFileName = os.path.join(stagePath, sha256asset + ".zip")

        meta_date_create = os.path.getmtime(assetFileName)

        extras = {}
        if "processWacz" in self.config and self.config["processWacz"]:
            print("Processing file as a wacz")
            extras = processWacz(assetFileName)

        content_meta = generate_metadata_content(
            meta_date_create, assetFileName, meta_uploader_name, extras
        )
        recorder_meta = prepare_metadata_recorder()

        with zipfile.ZipFile(bundleFileName + ".part", "w") as archive:
            archive.write(assetFileName, os.path.basename(assetFileName))
            archive.writestr(
                sha256asset + "-meta-content.json", json.dumps(content_meta)
            )
            archive.writestr(
                sha256asset + "-meta-recorder.json", json.dumps(recorder_meta)
            )
        sha256zip = sha256sum(os.path.join(stagePath, sha256asset + ".zip.part"))
        os.rename(
            bundleFileName + ".part", os.path.join(outputPath, sha256zip + ".zip")
        )

    def stop(self):
        self.observer.stop()
        self.observer.join()

config = {}
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
