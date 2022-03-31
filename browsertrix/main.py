from zipfile import ZipFile
import requests
from datetime import datetime
import json
import shutil
import os
from collections import defaultdict
import time
import logging

SOURCE_PATH = os.environ.get("SOURCE_PATH", "/mnt/browsertrix")
TARGET_PATH = os.environ.get("TARGET_PATH", "/mnt/browsertrix-out")
BUCKET = os.environ.get("BUCKET", "test-bucket")
USERNAME = os.environ.get("BROWSERTRIX_USERNAME")
PASSWORD = os.environ.get("BROWSERTRIX_PASSWORD")
HOST = os.environ.get("BROWSERTRIX_HOST", "127.0.0.1:9871")
TMP_DIR = os.environ.get("TMP_DIR", "/tmp/browstertrix-preprocessor")
LOG_PATH = os.environ.get("LOG_PATH")  # Empty string means stdout
DATA_DIR = os.environ.get("DATA_DIR")

DATA_JSON_PATH = os.path.join(DATA_DIR, "data.json")

LOOP_INTERVAL = 60
FAIL_DELAY = 10
# Crawl that finished X seconds before the last check is checked again, just in case
LAST_CHECK_WINDOW = 30


def send_to_prometheus(d):
    # For now do nothing
    pass


def log_req_err(r, tries):
    path = r.url[len("http://" + HOST) :]
    logging.error(
        f"{r.request.method} {path} failed with status code {r.status_code} (tries: {tries}):\n{r.text}"
    )


def log_req_success(r, tries):
    path = r.url[len("http://" + HOST) :]
    logging.info(f"{r.request.method} {path} succeeded (tries: {tries})")


def write_data(d):
    with open(DATA_JSON_PATH, "w") as f:
        json.dump(d, f)


logging.basicConfig(
    filename=LOG_PATH,
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


while True:
    metrics = defaultdict(lambda: 0)

    i = 1
    while True:
        r = requests.post(
            f"http://{HOST}/api/auth/jwt/login",
            data={"username": USERNAME, "password": PASSWORD},
        )
        if r.status_code != 200:
            log_req_err(r, i)
            i += 1
            time.sleep(FAIL_DELAY)
            continue
        log_req_success(r, i)
        break

    headers = {"Authorization": "Bearer " + r.json()["access_token"]}

    i = 1
    while True:
        r = requests.get(f"http://{HOST}/api/archives", headers=headers)
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
            r = requests.get(
                f"http://{HOST}/api/archives/{aid}/crawls", headers=headers
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
        crawls.sort(key=lambda x: datetime.fromisoformat(x["finished"]).timestamp())

        for crawl in crawls:
            logging.info("Looking at crawl %s", crawl["id"])

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
                    f"http://{HOST}/api/archives/{aid}/crawls/{crawl['id']}.json",
                    headers=headers,
                )
                if r.status_code != 200:
                    log_req_err(r)
                    i += 1
                    time.sleep(FAIL_DELAY)
                    continue
                log_req_success(r, i)
                break

            crawl_reponse = r.json()

            if os.path.exists(os.path.join(TARGET_PATH, crawl["id"] + ".zip")):
                # Crawl was already done, ZIP is already there
                logging.warning(
                    "Skipping because crawl ZIP already exists in %s: %s",
                    crawl["id"],
                    TARGET_PATH,
                )
                # Update data as if it was completed in this check, because it's
                # already done
                new_last_check = finish_date.timestamp()
                new_crawls.append(crawl["id"])
                continue

            wacz_path = os.path.join(
                SOURCE_PATH, BUCKET, crawl_reponse["resources"][0]["name"]
            )

            i = 1
            while not os.path.exists(wacz_path):
                logging.error(
                    "WACZ not available at path '%s' (tries: %d)", wacz_path, i
                )
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

            zip_path = os.path.join(TMP_DIR, crawl["id"] + ".zip")

            i = 1
            while True:
                try:
                    with ZipFile(zip_path, "w") as zipf:
                        zipf.write(wacz_path, os.path.basename(wacz_path))
                        zipf.writestr("content_metadata.json", json.dumps(content_meta))
                        zipf.writestr(
                            "recorder_metadata.json", json.dumps(recorder_meta)
                        )
                except OSError:
                    logging.exception(
                        "Failed to write temp ZIP to %s (tries: %d)", TMP_DIR, i
                    )
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
                        os.path.join(TARGET_PATH, crawl["id"] + ".zip.part"),
                    )
                except (OSError, shutil.Error, PermissionError):
                    logging.exception(
                        "Failed to move temp ZIP to %s (tries: %d)", TARGET_PATH, i
                    )
                    i += 1
                    time.sleep(FAIL_DELAY)
                else:
                    logging.info("Moved temp ZIP to %s (tries: %d)", TARGET_PATH, i)
                    break

            i = 1
            while True:
                try:
                    os.rename(
                        os.path.join(TARGET_PATH, crawl["id"] + ".zip.part"),
                        os.path.join(TARGET_PATH, crawl["id"] + ".zip"),
                    )
                except OSError:
                    logging.exception(
                        "Failed to rename .zip.part to .zip for crawl %s (tries: %d)",
                        crawl["id"],
                        i,
                    )
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
            # Update data since processing of crawl was successful
            new_last_check = finish_date.timestamp()
            new_crawls.append(crawl["id"])

        logging.info("Done with archive %s", aid)

        data[aid] = {"last_check": new_last_check, "crawls": new_crawls}
        write_data(data)

    send_to_prometheus(metrics)

    time.sleep(LOOP_INTERVAL)
