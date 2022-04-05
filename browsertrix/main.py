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

dotenv.load_dotenv()

SOURCE_PATH = os.environ.get("SOURCE_PATH", "/mnt/browsertrix")
TARGET_ROOT_PATH = os.environ.get("TARGET_PATH", "/mnt/browsertrix-out")
BUCKET = os.environ.get("BUCKET", "test-bucket")
USERNAME = os.environ.get("BROWSERTRIX_USERNAME")
PASSWORD = os.environ.get("BROWSERTRIX_PASSWORD")
HOST = os.environ.get("BROWSERTRIX_HOST", "http://127.0.0.1:9871")
TMP_DIR = os.environ.get("TMP_DIR", "/tmp/browstertrix-preprocessor")
LOG_FILE = os.environ.get("LOG_FILE")  # Empty string means stdout
DATA_DIR = os.environ.get("DATA_DIR")
PROMETHEUS_FILE = os.environ.get("PROMETHEUS_FILE")
DATA_JSON_PATH = os.path.join(DATA_DIR, "data.json")

LOOP_INTERVAL = 60
FAIL_DELAY = 10
# Crawl that finished X seconds before the last check is checked again, just in case
LAST_CHECK_WINDOW = 30

# Create temporary folder to stage files before moving them into action folder
TARGET_PATH_TMP = wacz_path = os.path.join(TARGET_ROOT_PATH, "tmp")
TARGET_PATH = wacz_path = os.path.join(TARGET_ROOT_PATH, "input")

if not os.path.exists(TARGET_PATH_TMP):
    os.makedirs(TARGET_PATH_TMP)


def sha256sum(filename):
    with open(filename, "rb") as f:
        bytes = f.read()  # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash


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
    path = r.url[len(HOST) :]
    logging.error(
        f"{r.request.method} {path} failed with status code {r.status_code} (tries: {tries}):\n{r.text}"
    )
    del metrics["request_errors"]  # Prometheus will see this as the same so remove it
    metrics['request_errors{status_code="' + str(r.status_code) + '"}'] += 1


def log_req_success(r, tries):
    path = r.url[len(HOST) :]
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
            f"{HOST}/api/auth/jwt/login",
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
os.makedirs(DATA_DIR, mode=0o755, exist_ok=True)

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
    while True:
        r = requests.get(f"{HOST}/api/archives", headers=headers())
        if r.status_code != 200:
            log_req_err(r, i)
            i += 1
            time.sleep(FAIL_DELAY)
            continue
        log_req_success(r, i)
        break

    for archive in r.json()["archives"]:
        aid = archive["id"]

        logging.info("Working on archive %s", aid)

        if not aid in data:
            data[aid] = {"last_check": 0, "crawls": []}

        new_last_check = data[aid]["last_check"]
        new_crawls = []

        i = 1
        while True:
            r = requests.get(f"{HOST}/api/archives/{aid}/crawls", headers=headers())
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
        crawls.sort(key=lambda x: datetime.fromisoformat(x["finished"]).timestamp())

        for crawl in crawls:
            logging.info("Looking at crawl %s", crawl["id"])

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
                    f"{HOST}/api/archives/{aid}/crawls/{crawl['id']}.json",
                    headers=headers(),
                )
                if r.status_code != 200:
                    log_req_err(r)
                    i += 1
                    time.sleep(FAIL_DELAY)
                    continue
                log_req_success(r, i)
                break

            crawl_reponse = r.json()

            wacz_path = os.path.join(
                SOURCE_PATH, BUCKET, crawl_reponse["resources"][0]["name"]
            )

            if os.path.exists(wacz_path + ".done"):
                # Crawl was already done, file is already there
                logging.warning(
                    "Skipping because crawl DONE file already exists in %s: %s",
                    crawl["id"],
                    TARGET_PATH_TMP,
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
            logging.info("WACZ available at path '%s' (tries: %d)", wacz_path, i)

            content_meta = {}
            recorder_meta = {}

            with ZipFile(wacz_path, "r") as wacz:
                d = json.loads(wacz.read("datapackage-digest.json"))
                content_meta["authsign_software"] = d["signedData"]["software"]
                content_meta["authsign_domain"] = d["signedData"]["domain"]

                d = json.loads(wacz.read("datapackage.json"))
                content_meta["wacz_version"] = d["wacz_version"]
                content_meta["created"] = d["created"]

                content_meta["pages"] = {}
                with wacz.open("pages/pages.jsonl") as jsonl_file:
                    for line in jsonl_file.readlines():
                        d = json.loads(line)
                        if "url" in d:
                            content_meta["pages"][d["id"]] = d["url"]

            sha256wacz = sha256sum(wacz_path)
            zip_path = os.path.join(TMP_DIR, sha256wacz + ".zip")

            i = 1
            while True:
                try:
                    with ZipFile(zip_path, "w") as zipf:
                        zipf.write(wacz_path, os.path.basename(wacz_path))
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
                        os.path.join(TARGET_PATH_TMP, sha256wacz + ".zip.part"),
                    )
                except (OSError, shutil.Error, PermissionError):
                    logging.exception(
                        "Failed to move temp ZIP to %s (tries: %d)", TARGET_PATH_TMP, i
                    )
                    metrics["tmp_zip_move_failures"] += 1
                    i += 1
                    time.sleep(FAIL_DELAY)
                else:
                    logging.info("Moved temp ZIP to %s (tries: %d)", TARGET_PATH_TMP, i)
                    break

            i = 1
            sha256zip = sha256sum(
                os.path.join(TARGET_PATH_TMP, sha256wacz + ".zip.part")
            )
            while True:
                try:
                    os.rename(
                        os.path.join(TARGET_PATH_TMP, sha256wacz + ".zip.part"),
                        os.path.join(TARGET_PATH, sha256zip + ".zip"),
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
