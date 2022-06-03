from copy import deepcopy
import csv
import json
import ast
from textwrap import indent
from xml.dom.minidom import Identified
import requests
import dotenv
import os

dotenv.load_dotenv("../.env")

SOURCE_PATH = os.environ.get("SOURCE_PATH", "/mnt/browsertrix")
TARGET_ROOT_PATH = os.environ.get("TARGET_PATH", "/mnt/browsertrix-out")
BUCKET = os.environ.get("BUCKET", "test-bucket")
USERNAME = os.environ.get("BROWSERTRIX_USERNAME")
PASSWORD = os.environ.get("BROWSERTRIX_PASSWORD")
BROWSERTRIX_URL = os.environ.get("BROWSERTRIX_URL", "http://127.0.0.1:9871")
TMP_DIR = os.environ.get("TMP_DIR", "/tmp/browstertrix-preprocessor")
LOG_FILE = os.environ.get("LOG_FILE")  # Empty string means stdout
DATA_DIR = os.environ.get("DATA_DIR")
PROMETHEUS_FILE = os.environ.get("PROMETHEUS_FILE")
# DATA_JSON_PATH = os.path.join(DATA_DIR, "data.json")


TARGET_ROOT_PATH = "/mnt/integrity_store/starling/internal/hala-systems/march-kharkiv"
AID = "323df0f3-ea9c-47e8-88ef-d128d73f1ed3"

startrow = 1
endrow = 100


def ConfigureCrawl(AID, target_urls, meta_data, orgKey, sourceId):
    itemID = sourceId["value"]
    if not isinstance(target_urls, list):
        target_urls = [target_urls]

    # Authenticate with Browsertrix
    auth = {"username": USERNAME, "password": PASSWORD}
    URL = f"{BROWSERTRIX_URL}/api/auth/jwt/login"
    # response = requests.post( URL, data=auth)
    access_token = ""
    resp = requests.post(URL, data=auth)
    response_json = resp.json()
    if "access_token" not in response_json:
        raise Exception("Access Token Failed")
    access_token = response_json["access_token"]
    headers = {"Authorization": "Bearer " + access_token}

    # Create crawl template
    config = {
        "name": "_Q_" + itemID,
        "colls": [],
        "crawlTimeout": 60 * 60 * 24,
        "scale": 1,
        "schedule": "",
        "runNow": False,
        "config": {
            "seeds": target_urls,
            "scopeType": "page",
            "depth": -1,
            "limit": 0,
            "extraHops": 0,
            "behaviorTimeout": 300,
            "behaviors": "autoscroll,autoplay,autofetch,siteSpecific",
        },
    }
    URL = f"{BROWSERTRIX_URL}/api/archives/" + AID + "/crawlconfigs/"
    r = requests.post(URL, json=config, headers=headers)
    res = r.json()

    if "added" not in res:
        raise Exception("Failed to create template")
    CID = res["added"]

    # Use queue system for now
    #    # Start Crawl
    #    URL = (
    #        f"{BROWSERTRIX_URL}/api/archives/"
    #        + AID
    #        + "/crawlconfigs/"
    #        + CID
    #        + "/run"
    #    )
    #    r = requests.post(URL, headers=headers)
    #    res = r.json()
    #    if "started" not in res:
    #        raise Exception("Failed to start crawl")
    #    CRAWL_ID = res["started"]

    # Prepeare meta data

    meta_data_private = {}
    meta_data_public = {}

    for m in meta_data:
        if m.startswith("private_"):
            meta_data_private[m] = meta_data[m]
        else:
            meta_data_public[m] = meta_data[m]

    meta = {
        "private": {
            "additionalData": {
                "crawl_template_id": CID,
                "crawl_config": config,
                "DFRLabMetadata": meta_data_private,
            }
        },
        "extras": {"DFRLabMetadata": meta_data_public},
        "sourceId": sourceId,
    }

    # Save file as json
    metaPath = TARGET_ROOT_PATH + "/preprocessor_metadata"
    if not os.path.exists(metaPath):
        os.makedirs(metaPath)

    metaFilename = metaPath + "/" + CID + ".json"
    text_file = open(metaFilename, "w")
    text_file.write(json.dumps(meta))
    text_file.close()


with open("kharkiv.csv", newline="\n", encoding="utf8") as csvfile:
    csv_reader = csv.reader(
        csvfile,
        delimiter=",",
    )
    heading = None

    countlines = 0
    json_metadata_template = {}
    for row in csv_reader:
        # Read Heading
        if heading == None:
            column_index = 0
            for col_name in row:
                if col_name == "":
                    col_name = "col_" + str(column_index)
                json_metadata_template[col_name] = ""
                column_index += 1
            heading = row
        else:

            countlines = countlines + 1

            json_metadata = deepcopy(json_metadata_template)
            column_index = 0
            for item in row:
                json_metadata[heading[column_index]] = item
                column_index += 1
            URL = json_metadata["source"]  # ast.literal_eval(row[0])

            if URL.startswith("["):
                URL = ast.literal_eval(URL)

            # Telegram contxt and user
            profile = URL[: URL.rfind("/")]
            context = (
                URL[: URL.find("/t.me/")] + "/t.me/s/" + URL[URL.find("/t.me/") + 6 :]
            )
            URL = [URL, profile, context]

            TS = json_metadata["row"]  # row[3]

            if countlines >= startrow:
                ConfigureCrawl(
                    AID,
                    URL,
                    json_metadata,
                    "DFRLabMetadata",
                    {"key": "row", "value": TS}
                )
            if countlines >= endrow:
                break
