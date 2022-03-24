from zipfile import ZipFile
import requests
import datetime
import json
import shutil
import os
from collections import defaultdict
import time
import logging

SOURCEPATH = "/mnt/browsertrix"
TARGETPATH = "/mnt/browsertrix-out"
DELAY = 60
FAIL_DELAY = 10

BUCKET = os.environ.get("BUCKET", "test-bucket")
USERNAME = os.environ.get("BROWSERTRIX_USERNAME")
PASSWORD = os.environ.get("BROWSERTRIX_PASSWORD")
HOST = os.environ.get("BROWSERTRIX_HOST", "127.0.0.1:9871")
TMP_DIR = os.environ.get("TMP_DIR", "/tmp/browstertrix-preprocessor")
LOGFILE = os.environ.get("LOGFILE")  # Empty string means stdout


def send_to_prometheus(d):
    # For now do nothing
    pass


def log_req_err(r):
    path = r.url[len("http://" + HOST) :]
    logging.error(f"{path} failed with status code {r.status_code}: {r.text}")


last_check = {}

logging.basicConfig(
    filename=LOGFILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logging.info("Started browsertrix preprocessor")

os.makedirs(TMP_DIR, exist_ok=True)

while True:
    metrics = defaultdict(lambda: 0)

    r = requests.post(
        f"http://{HOST}/api/auth/jwt/login",
        data={"username": USERNAME, "password": PASSWORD},
    )
    if not r.ok:
        log_req_err(r)
        time.sleep(FAIL_DELAY)
        continue

    headers = {"Authorization": "Bearer " + r.json()["access_token"]}

    r = requests.get(f"http://{HOST}/api/archives", headers=headers)
    if not r.ok:
        log_req_err(r)
        time.sleep(FAIL_DELAY)
        continue

    for archive in r.json()["archives"]:
        aid = archive["id"]

        if not aid in last_check:
            last_check[aid] = 0

        r = requests.get(
            f"http://{HOST}/api/archives/" + aid + "/crawls", headers=headers
        )
        if not r.ok:
            log_req_err(r)
            time.sleep(FAIL_DELAY)
            continue

        for crawl in r.json()["crawls"]:

            metrics["crawl_state_" + crawl["state"]] += 1

            if crawl["state"] == "complete":
                start_date = datetime.datetime.fromisoformat(crawl["started"])
                finish_date = datetime.datetime.fromisoformat(crawl["finished"])
                length = finish_date - start_date

                if length.total_seconds() / 60 < 1:
                    metrics["crawl_slow_count"] += 1

                if finish_date.timestamp() > last_check[aid]:
                    last_check[aid] = finish_date.timestamp()

                    logging.info("Working on crawl %s", crawl["id"])

                    r = requests.get(
                        f"http://{HOST}/api/archives/{aid}/crawls/{crawl['id']}.json",
                        headers=headers,
                    )
                    if not r.ok:
                        log_req_err(r)
                        time.sleep(FAIL_DELAY)
                        continue

                    crawl_reponse = r.json()

                    wacz_path = os.path.join(
                        SOURCEPATH, BUCKET, crawl_reponse["resources"][0]["name"]
                    )

                    content_meta = {}
                    recorder_meta = {}

                    with ZipFile(wacz_path, "r") as wacz:
                        data = json.loads(wacz.read("datapackage-digest.json"))
                        content_meta["authsign_software"] = data["signedData"][
                            "software"
                        ]
                        content_meta["authsign_domain"] = data["signedData"]["domain"]

                        data = json.loads(wacz.read("datapackage.json"))
                        content_meta["wacz_version"] = data["wacz_version"]
                        content_meta["created"] = data["created"]

                        content_meta["pages"] = {}
                        with wacz.open("pages/pages.jsonl") as jsonl_file:
                            for line in jsonl_file.readlines():
                                data = json.loads(line)
                                if "url" in data:
                                    content_meta["pages"][data["id"]] = data["url"]

                        zip_path = os.path.join(TMP_DIR, crawl_reponse["id"] + ".zip")
                        zipf = ZipFile(zip_path, "w")
                        zipf.write(wacz_path, os.path.basename(wacz_path))
                        zipf.writestr("content_metadata.json", json.dumps(content_meta))
                        zipf.writestr(
                            "recorder_metadata.json", json.dumps(recorder_meta)
                        )
                        zipf.close()

                        # Moving is not atomic in this case because the destination
                        # is on a mounted filesystem. So use a .part file.
                        shutil.move(
                            zip_path,
                            os.path.join(TARGETPATH, crawl_reponse["id"] + ".zip.part"),
                        )
                        os.rename(
                            os.path.join(TARGETPATH, crawl_reponse["id"] + ".zip.part"),
                            os.path.join(TARGETPATH, crawl_reponse["id"] + ".zip"),
                        )

    send_to_prometheus(metrics)

    time.sleep(DELAY)
