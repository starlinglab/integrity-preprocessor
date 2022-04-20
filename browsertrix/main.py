from copy import deepcopy
from dataclasses import make_dataclass
from zipfile import ZipFile
import requests
from datetime import datetime
import json
import shutil
import os
from collections import defaultdict
import time
import logging
from base64 import urlsafe_b64decode
import dotenv
from pathlib import Path
import hashlib

# Kludge
import sys

sys.path.append(
    os.path.dirname(os.path.realpath(__file__)) + "/../integrity_recorder_id"
)
import integrity_recorder_id

dotenv.load_dotenv()

SOURCE_PATH = os.environ.get("SOURCE_PATH", "/mnt/browsertrix")
TARGET_DEFAULT_ROOT_PATH = os.environ.get("TARGET_PATH", "/mnt/browsertrix-out")
BUCKET = os.environ.get("BUCKET", "test-bucket")
USERNAME = os.environ.get("BROWSERTRIX_USERNAME")
PASSWORD = os.environ.get("BROWSERTRIX_PASSWORD")
BROWSERTRIX_URL = os.environ.get("BROWSERTRIX_URL", "http://127.0.0.1:9871")
TMP_DIR = os.environ.get("TMP_DIR", "/tmp/browstertrix-preprocessor")
LOG_FILE = os.environ.get("LOG_FILE")  # Empty string means stdout
DATA_JSON_PATH = os.environ.get("DATA_FILE")
CONFIG_FILE = os.environ.get("CONFIG_FILE")
PROMETHEUS_FILE = os.environ.get("PROMETHEUS_FILE")

LOOP_INTERVAL = 60
FAIL_DELAY = 10
# Crawl that finished X seconds before the last check is checked again, just in case
LAST_CHECK_WINDOW = 30

# Load config
config_data = {}
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config_data = json.load(f)

TARGET_PATH_TMP = {}
TARGET_PATH = {}
TARGET_ROOT_PATH = {}

# Process collections in config
if "collections" in config_data:
    for aid in config_data["collections"]:
        # Create temporary folder to stage files before moving them into action folder
        TARGET_ROOT_PATH[aid] = config_data["collections"][aid]["target_path"]
        TARGET_PATH_TMP[aid] = os.path.join(TARGET_ROOT_PATH[aid], "tmp")
        TARGET_PATH[aid] = wacz_path = os.path.join(TARGET_ROOT_PATH[aid], "input")
        if not os.path.exists(TARGET_PATH_TMP[aid]):
            os.makedirs(TARGET_PATH_TMP[aid])
        logging.info(f"Loaded collection archive {aid}")

# Create default entries
TARGET_ROOT_PATH["default"] = TARGET_DEFAULT_ROOT_PATH
TARGET_PATH_TMP["default"] = os.path.join(TARGET_ROOT_PATH["default"], "tmp")
TARGET_PATH["default"] = wacz_path = os.path.join(TARGET_ROOT_PATH["default"], "input")

if not os.path.exists(TARGET_PATH_TMP["default"]):
    os.makedirs(TARGET_PATH_TMP["default"])

metdata_file_timestamp = 0

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
    # TODO remove unused recorders
    return recorder_meta_all


def sha256sum(filename):
    with open(filename, "rb") as f:
        bytes = f.read()  # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash

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

#########################################
# Turn into a module, shared with dropbox#
# #######################################
def processWacz(wacz_path):
    # WACZ metadata extraction
    with ZipFile(wacz_path, "r") as wacz:
        d = json.loads(wacz.read("datapackage-digest.json"))
        extras = {}

        if "signedData" in d:
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

        if "title" in d:
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


def generate_metadata_content(
    meta_crawl_config, meta_crawl_data, meta_additional, meta_extra, meta_date_created
):

    extras = {}
    private = {}
    private["crawlConfigs"] = meta_crawl_config
    private["crawlData"] = meta_crawl_data
    private["additionalData"] = meta_additional

    extras = deepcopy(meta_extra)

    meta_content = deepcopy(default_content)

    create_date = meta_date_created.split("T")[0]
    meta_content["name"] = f"Web archive on {create_date}"

    pagelist = ""
    if "pages" in extras:
        i = []
        c = 0
        for item in extras["pages"]:
            c = c + 1
            if c == 4:
                i.append("...")
            i.append(extras["pages"][item])
        pagelist = "[ " + ", ".join(i[:3]) + " ]"

    meta_content[
        "description"
    ] = f"Web archive {pagelist} captured using Browsertrix on {create_date}"

    meta_content["dateCreated"] = meta_date_created
    meta_content["extras"] = extras
    meta_content["private"] = private
    meta_content["timestamp"] = datetime.utcnow().isoformat() + "Z"

    return {"contentMetadata": meta_content}


def send_to_prometheus(metrics):
    if not PROMETHEUS_FILE:
        return

    # Write to .part file then rename, so that there isn't a race condition
    # where the file watcher might read the truncated file

    with open(PROMETHEUS_FILE + ".part", "w") as f:
        for key, value in metrics.items():
            f.write(f"{key} {value}\n")

    os.rename(PROMETHEUS_FILE + ".part", PROMETHEUS_FILE)


# Metrics live for the duration of the script
metrics = defaultdict(lambda: 0)  # Never fail when updating non-existent key with +=
# Set known keys so they show up when .items() is called
metrics.update(
    {
        "crawl_state_complete": 0,
        "crawl_short_count": 0,
        "request_errors": 0,
        "crawl_already_exists": 0,
        "wacz_not_found": 0,
        "tmp_zip_write_failures": 0,
        "tmp_zip_move_failures": 0,
        "tmp_zip_rename_failures": 0,
        "processed_archives": 0,
        "processed_crawls": 0,
    }
)


def log_req_err(r, tries):
    path = r.url[len(BROWSERTRIX_URL) :]
    logging.error(
        f"{r.request.method} {path} failed with status code {r.status_code} (tries: {tries}):\n{r.text}"
    )
    del metrics["request_errors"]  # Prometheus will see this as the same so remove it
    metrics['request_errors{status_code="' + str(r.status_code) + '"}'] += 1


def log_req_success(r, tries):
    path = r.url[len(BROWSERTRIX_URL) :]
    logging.info(f"{r.request.method} {path} succeeded (tries: {tries})")

access_token = None
access_token_exp = 0

def get_access_token():
    global access_token, access_token_exp

    if access_token_exp - time.time() > 10:
        # It hasn't expired, and won't for at least 10 seconds or more,
        # so keep using it
        return access_token

    # New access token needed, get it by logging in

    i = 1
    while True:
        r = requests.post(
            f"{BROWSERTRIX_URL}/api/auth/jwt/login",
            data={"username": USERNAME, "password": PASSWORD},
        )
        if r.status_code != 200:
            log_req_err(r, i)
            i += 1
            time.sleep(FAIL_DELAY)
            continue
        log_req_success(r, i)
        break

    access_token = r.json()["access_token"]
    access_token_exp = json.loads(
        urlsafe_b64decode(access_token.split(".")[1] + "=="),
    )["exp"]
    return access_token


def headers():
    return {"Authorization": "Bearer " + get_access_token()}


def write_data(d):
    with open(DATA_JSON_PATH, "w") as f:
        json.dump(d, f)


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logging.info("Started browsertrix preprocessor")

os.makedirs(TMP_DIR, mode=0o755, exist_ok=True)

# Data format:
# {
#   "<archive id>": {
#       "last_check": 12345,
#       "crawls": [           # crawls IDs since last check
#           "<crawl id>",
#           "<crawl id>"
#       ]
#   }
# }

data = {}
if os.path.exists(DATA_JSON_PATH):
    with open(DATA_JSON_PATH, "r") as f:
        data = json.load(f)


# Write initial file
send_to_prometheus(metrics)

# Update IDs
integrity_recorder_id.build_recorder_id_json()

while True:

    i = 1
    while True:
        r = requests.get(f"{BROWSERTRIX_URL}/api/archives", headers=headers())
        if r.status_code != 200:
            log_req_err(r, i)
            i += 1
            time.sleep(FAIL_DELAY)
            continue
        log_req_success(r, i)
        break

    for archive in r.json()["archives"]:
        aid = archive["id"]

        if aid in TARGET_PATH:
            current_collection = aid
        else:
            current_collection = "default"

        logging.info("Working on archive %s", aid)

        if not aid in data:
            data[aid] = {"last_check": 0, "crawls": []}

        new_last_check = data[aid]["last_check"]
        new_crawls = data[aid]["crawls"]

        i = 1
        while True:
            r = requests.get(
                f"{BROWSERTRIX_URL}/api/archives/{aid}/crawls", headers=headers()
            )
            if r.status_code != 200:
                log_req_err(r, i)
                i += 1
                time.sleep(FAIL_DELAY)
                continue
            log_req_success(r, i)
            break

        # Sort crawls by finish time, from ones that finished first to those
        # that finished most recently
        crawls = r.json()["crawls"]
        crawls = list(filter(lambda x: x["finished"] != None, crawls))
        crawls.sort(key=lambda x: datetime.fromisoformat(x["finished"]).timestamp())

        for crawl in crawls:

            # Save metrics after each crawl
            send_to_prometheus(metrics)

            metrics["crawl_state_" + crawl["state"]] += 1

            if crawl["state"] != "complete":
                continue

            start_date = datetime.fromisoformat(crawl["started"])
            finish_date = datetime.fromisoformat(crawl["finished"])

            if finish_date.timestamp() < data[aid]["last_check"] - LAST_CHECK_WINDOW:
                # Too old, was processed already
                continue
            if crawl["id"] in data[aid]["crawls"]:
                # Crawl ID is stored, so it was processed already
                continue

            logging.info("Working on crawl %s", crawl["id"])

            length = finish_date - start_date
            if length.total_seconds() / 60 < 1:
                metrics["crawl_short_count"] += 1

            i = 1
            while True:
                r = requests.get(
                    f"{BROWSERTRIX_URL}/api/archives/{aid}/crawls/{crawl['id']}.json",
                    headers=headers(),
                )
                if r.status_code != 200:
                    log_req_err(r)
                    i += 1
                    time.sleep(FAIL_DELAY)
                    continue
                log_req_success(r, i)
                break

            crawl_json = r.json()

            wacz_path = os.path.join(
                SOURCE_PATH, BUCKET, crawl_json["resources"][0]["name"]
            )

            if os.path.exists(wacz_path + ".done"):
                # Crawl was already done, file is already there
                logging.warning(
                    "Skipping because crawl DONE file already exists in %s: %s",
                    crawl["id"],
                    os.path.basename(wacz_path),
                )
                metrics["crawl_already_exists"] += 1
                # Update data as if it was completed in this check, because it's
                # already done
                new_last_check = finish_date.timestamp()
                new_crawls.append(crawl["id"])
                continue

            i = 1
            while not os.path.exists(wacz_path):
                logging.error(
                    "WACZ not available at path '%s' (tries: %d)", wacz_path, i
                )
                metrics["wacz_not_found"] += 1
                i += 1
                time.sleep(FAIL_DELAY)

            # Meta data collection and generation
            recorder_meta = prepare_metadata_recorder()

            meta_additional = ""
            meta_crawl = ""
            meta_date_created = ""

            # Get craw cawlconfig from API
            while True:
                r = requests.get(
                    f"{BROWSERTRIX_URL}/api/archives/{aid}/crawlconfigs/{crawl['cid']}",
                    headers=headers(),
                )
                if r.status_code != 200:
                    log_req_err(r)
                    i += 1
                    time.sleep(FAIL_DELAY)
                    continue
                log_req_success(r, i)
                break

            meta_crawl = r.json()

            # Variable also used later on to write final SHA256 ID
            meta_additional_filename = (
                TARGET_ROOT_PATH[current_collection]
                + "/preprocessor_metadata/"
                + crawl["cid"]
                + ".json"
            )
            if os.path.exists(meta_additional_filename):
                f = open(meta_additional_filename)
                meta_additional = json.load(f)

            meta_extra = processWacz(wacz_path)
            meta_date_created = crawl_json["started"]

            content_meta = generate_metadata_content(
                meta_crawl,
                crawl_json,
                meta_additional,
                meta_extra,
                meta_date_created,
            )

            sha256wacz = sha256sum(wacz_path)
            zip_path = os.path.join(TMP_DIR, sha256wacz + ".zip")

            i = 1
            while True:
                try:
                    with ZipFile(zip_path, "w") as zipf:
                        zipf.write(wacz_path, sha256wacz + ".wacz")
                        zipf.writestr(
                            sha256wacz + "-meta-content.json", json.dumps(content_meta)
                        )
                        zipf.writestr(
                            sha256wacz + "-meta-recorder.json",
                            json.dumps(recorder_meta),
                        )
                except OSError:
                    logging.exception(
                        "Failed to write temp ZIP to %s (tries: %d)", TMP_DIR, i
                    )
                    metrics["tmp_zip_write_failures"] += 1
                    i += 1
                    time.sleep(FAIL_DELAY)
                else:
                    logging.info("Wrote temp ZIP to %s (tries: %d)", TMP_DIR, i)
                    break

            # Moving is not atomic in this case because the destination
            # is on a mounted filesystem. So use a .part file to copy the file
            # contents, then rename on the mounted filesystem.

            i = 1
            while True:
                try:
                    shutil.move(
                        zip_path,
                        os.path.join(
                            TARGET_PATH_TMP[current_collection],
                            sha256wacz + ".zip.part",
                        ),
                    )
                except (OSError, shutil.Error, PermissionError):
                    logging.exception(
                        "Failed to move temp ZIP to %s (tries: %d)",
                        TARGET_PATH_TMP[current_collection],
                        i,
                    )
                    metrics["tmp_zip_move_failures"] += 1
                    i += 1
                    time.sleep(FAIL_DELAY)
                else:
                    logging.info(
                        "Moved temp ZIP to %s (tries: %d)",
                        TARGET_PATH_TMP[current_collection],
                        i,
                    )
                    break

            i = 1
            sha256zip = sha256sum(
                os.path.join(
                    TARGET_PATH_TMP[current_collection], sha256wacz + ".zip.part"
                )
            )
            while True:
                try:
                    os.rename(
                        os.path.join(
                            TARGET_PATH_TMP[current_collection],
                            sha256wacz + ".zip.part",
                        ),
                        os.path.join(
                            TARGET_PATH[current_collection], sha256zip + ".zip"
                        ),
                    )
                except OSError:
                    logging.exception(
                        "Failed to rename .zip.part to .zip for crawl %s (tries: %d)",
                        crawl["id"],
                        i,
                    )
                    metrics["tmp_zip_rename_failures"] += 1
                    i += 1
                    time.sleep(FAIL_DELAY)
                else:
                    logging.info(
                        "Renamed .zip.part to .zip for crawl %s (tries: %d)",
                        crawl["id"],
                        i,
                    )
                    break

            # Write the ID to a file for refrence
            if os.path.exists(meta_additional_filename):
                f = open(meta_additional_filename + ".id.txt", "w")
                f.write(sha256wacz)
                f.close()

            logging.info("Successfully processed crawl %s", crawl["id"])
            Path(wacz_path + ".done").touch()

            metrics["processed_crawls"] += 1
            # Update data since processing of crawl was successful
            new_last_check = finish_date.timestamp()
            new_crawls.append(crawl["id"])

        logging.info("Done with archive %s", aid)
        metrics["processed_archives"] += 1

        data[aid] = {"last_check": new_last_check, "crawls": new_crawls}
        write_data(data)

    time.sleep(LOOP_INTERVAL)
