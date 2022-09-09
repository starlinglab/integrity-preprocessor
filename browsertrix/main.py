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

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import common

dotenv.load_dotenv()

SOURCE_PATH = os.environ.get("SOURCE_PATH", "/mnt/browsertrix")
TARGET_DEFAULT_ROOT_PATH = os.environ.get("TARGET_PATH", "/mnt/browsertrix-out")
BUCKET = os.environ.get("BUCKET", "test-bucket")
USERNAME = os.environ.get("BROWSERTRIX_USERNAME")
PASSWORD = os.environ.get("BROWSERTRIX_PASSWORD")
BROWSERTRIX_URL = os.environ.get("BROWSERTRIX_URL", "http://127.0.0.1:9871")
TMP_DIR = os.environ.get("TMP_DIR", "/tmp/browstertrix-preprocessor")
LOG_FILE = os.environ.get("LOG_FILE", None)
DATA_JSON_PATH = os.environ.get("DATA_FILE")
CONFIG_FILE = os.environ.get("CONFIG_FILE")
PROMETHEUS_FILE = os.environ.get("PROMETHEUS_FILE")
HOSTNAME = os.environ.get("HOSTNAME")


LOOP_INTERVAL = 60
FAIL_DELAY = 10
# Crawl that finished X seconds before the last check is checked again, just in case
LAST_CHECK_WINDOW = 30


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging = common.logging

# Load config
config_data = {}
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config_data = json.load(f)

TARGET_PATH_TMP = {}
TARGET_PATH = {}
TARGET_ROOT_PATH = {}
TARGET_AUTHOR = {}

# Process collections in config
if "collections" in config_data:
    for aid in config_data["collections"]:
        TARGET_AUTHOR[aid] = config_data["collections"][aid]["author"]
        TARGET_ROOT_PATH[aid] = config_data["collections"][aid]["target_path"]
        TARGET_PATH_TMP[aid] = os.path.join(TARGET_ROOT_PATH[aid], "tmp")
        TARGET_PATH[aid] = wacz_path = os.path.join(TARGET_ROOT_PATH[aid], "input")

        # Create temporary folder to stage files before moving them into action folder
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


def download_file(url, local_filename):
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        if r.status_code == 200:
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    # if chunk:
                    f.write(chunk)
        else:
            return -1
    return 1


def generate_metadata_content(
    meta_crawl_config,
    meta_crawl_data,
    meta_additional,
    meta_extra,
    meta_date_created,
    author,
):

    extras = deepcopy(meta_extra)
    if "extras" in meta_additional:
        extras.update(meta_additional["extras"])
    private = {}
    if "private" in meta_additional:
        private.update(meta_additional["private"])
    sourceId = None
    if "sourceId" in meta_additional:
        sourceId = meta_additional["sourceId"]

    private["crawlConfigs"] = meta_crawl_config
    private["crawlData"] = meta_crawl_data

    meta_content = deepcopy(default_content)
    if author:
        meta_content["author"] = author

    create_date = meta_date_created.split("T")[0]
    meta_content["name"] = f"Web archive on {create_date}"

    pagelist = ""
    if "pages" in extras:
        i = []
        c = 0
        suffix = ""
        for item in extras["pages"]:
            c = c + 1
            if c == 4:
                suffix = ", ..."
            i.append(extras["pages"][item])
        pagelist = "[ " + ", ".join(i[:3]) + f"{suffix} ]"

    meta_content[
        "description"
    ] = f"Web archive {pagelist} captured using Browsertrix on {create_date}"

    meta_content["dateCreated"] = meta_date_created
    meta_content["extras"] = extras
    meta_content["private"] = private
    if sourceId:
        meta_content["sourceId"] = sourceId
    meta_content["timestamp"] = datetime.utcnow().isoformat() + "Z"

    return meta_content


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
    r = requests.post(
        f"{BROWSERTRIX_URL}/api/auth/jwt/login",
        data={"username": USERNAME, "password": PASSWORD},
    )
    if r.status_code != 200:
        raise Exception(f"PATCH of {aid}/crawlconfigs Faild")

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


def update_crawl_config(cid, aid, data):
    i = 0
    r = requests.patch(
        f"{BROWSERTRIX_URL}/api/archives/{aid}/crawlconfigs/{cid}",
        headers=headers(),
        json=data,
    )
    if r.status_code != 200:
        raise Exception(f"PATCH of {aid}/crawlconfigs Faild")
    return r.json()


def get_crawl_config(cid, aid):
    i = 0
    r = requests.get(
        f"{BROWSERTRIX_URL}/api/archives/{aid}/crawlconfigs/{cid}",
        headers=headers(),
    )
    if r.status_code != 200:
        raise Exception(f"GET of {aid}/crawlconfigs Faild")
    return r.json()


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

while True:

    i = 1

    r = requests.get(f"{BROWSERTRIX_URL}/api/archives", headers=headers())
    if r.status_code != 200:
        raise Exception(f"GET of /api/archives failed")

    crawl_running_count = 0

    for archive in r.json()["archives"]:
        aid = archive["id"]

        if aid in TARGET_PATH:
            current_collection = aid
        else:
            # Skip because archive is not defined in collection file
            continue

        logging.info("Working on archive %s", aid)

        if not aid in data:
            data[aid] = {"last_check": 0, "crawls": []}

        new_last_check = data[aid]["last_check"]
        new_crawls = data[aid]["crawls"]

        i = 1
        r = requests.get(
            f"{BROWSERTRIX_URL}/api/archives/{aid}/crawls", headers=headers()
        )
        if r.status_code != 200:
            raise Exception(f"GET of /api/archives/{aid}/crawls failed")
        crawls = r.json()["crawls"]

        # Count the number of currently running crawls
        for crawl in crawls:
            if crawl["state"] == "running":
                crawl_running_count = crawl_running_count + 1

        # Sort crawls by finish time, from ones that finished first to those
        # that finished most recently
        crawls = list(filter(lambda x: x["finished"] != None, crawls))
        crawls.sort(key=lambda x: datetime.fromisoformat(x["finished"]).timestamp())

        for crawl in crawls:

            # If crawl is finished but marked as _R_unning, change it to _D_one
            crawl_config = get_crawl_config(crawl["cid"], aid)
            if crawl_config["name"][:3] == "_R_":
                new_name = "_D_" + crawl_config["name"][3:]
                update_crawl_config(crawl["cid"], aid, {"name": new_name})

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
            r = requests.get(
                f"{BROWSERTRIX_URL}/api/archives/{aid}/crawls/{crawl['id']}.json",
                headers=headers(),
            )
            if r.status_code != 200:
                raise Exception(
                    f"GET of /api/archives/{aid}/crawls/{crawl['id']}.json Failed"
                )

            crawl_json = r.json()

#            wacz_url = f"https://{HOSTNAME}" + crawl_json["resources"][0]["path"]
            # Old way to download file, to be fixed for k8
            wacz_url = crawl_json["resources"][0]["path"]
            wacz_url = wacz_url.split("?")[0]
            wacz_path = (
                TARGET_ROOT_PATH[current_collection] + "/tmp/" + crawl["cid"] + ".wacz"
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
            download_file(wacz_url, wacz_path)
            logging.info(f"Downloaded {wacz_path}")

            if not os.path.exists(wacz_path):
                Path(wacz_path + ".done").touch()
                Path(wacz_path + ".error").touch()
                logging.error("WACZ not available at path '%s'", wacz_path)
                continue

            # Meta data collection and generation
            recorder_meta = common.get_recorder_meta("browsertrix")

            meta_additional = ""
            meta_crawl = ""
            meta_date_created = ""

            # Get craw cawlconfig from API
            meta_crawl = get_crawl_config(crawl["cid"], aid)

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

            meta_extra = common.parse_wacz_data_extra(wacz_path)
            meta_date_created = crawl_json["started"]

            content_meta = generate_metadata_content(
                meta_crawl,
                crawl_json,
                meta_additional,
                meta_extra,
                meta_date_created,
                TARGET_AUTHOR[current_collection],
            )

            i = 1

            out_file = common.add_to_pipeline(
                wacz_path,
                content_meta,
                recorder_meta,
                TARGET_PATH_TMP[current_collection],
                TARGET_PATH[current_collection],
            )
            sha256zip = os.path.splitext(os.path.basename(out_file))[0]

            # Write the ID to a file for refrence
            if os.path.exists(meta_additional_filename):
                f = open(meta_additional_filename + ".id.txt", "w")
                f.write(sha256zip)
                f.close()

            logging.info("Successfully processed crawl %s", crawl["id"])
            Path(wacz_path + ".done").touch()
            os.remove(wacz_path)

            metrics["processed_crawls"] += 1
            # Update data since processing of crawl was successful
            new_last_check = finish_date.timestamp()
            new_crawls.append(crawl["id"])

        logging.info("Done with archive %s", aid)
        metrics["processed_archives"] += 1

        data[aid] = {"last_check": new_last_check, "crawls": new_crawls}
        write_data(data)

    # Process crawl queue
    i = 1

    r = requests.get(f"{BROWSERTRIX_URL}/api/archives", headers=headers())
    if r.status_code != 200:
        raise Exception(f"GET of api/archives Failed")

    queuelist = []
    for archive in r.json()["archives"]:

        aid = archive["id"]
        r = requests.get(
            f"{BROWSERTRIX_URL}/api/archives/{aid}/crawlconfigs", headers=headers()
        )
        if r.status_code != 200:
            raise Exception(f"GET of {aid}/crawlconfigs Failed")

        # Check if crawl is to be queued and add it to array
        for crawl_config in r.json()["crawlConfigs"]:
            crawl_name = crawl_config["name"]
            if crawl_name[:3] == "_Q_":
                queuelist.append(
                    {"aid": aid, "id": crawl_config["id"], "name": crawl_name}
                )

    # If less then 3 crawls happening, and there is a queue, start the next item
    while crawl_running_count < 3 and len(queuelist) > 0:

        r = queuelist.pop()
        aid = r["aid"]
        cid = r["id"]
        name = r["name"][3:]

        r = requests.post(
            f"{BROWSERTRIX_URL}/api/archives/{aid}/crawlconfigs/{cid}/run",
            headers=headers(),
        )
        crawl_running_count = crawl_running_count + 1
        logging.info(f"Started crawl of {aid}/{cid}")
        crawlid = r.json()["started"]
        new_name = "_R_" + name
        data = {"name": new_name}
        r = update_crawl_config(cid, aid, data)

    time.sleep(LOOP_INTERVAL)
