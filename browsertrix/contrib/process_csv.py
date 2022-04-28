from copy import deepcopy
import csv
import json
import ast
from textwrap import indent
from xml.dom.minidom import Identified
import requests
import dotenv
import os

dotenv.load_dotenv()

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
DATA_JSON_PATH = os.path.join(DATA_DIR, "data.json")


TARGET_ROOT_PATH = (
    "/mnt/integrity_store/starling/internal/starling-lab-test/test-web-archive-dfrlab/"
)


def ConfigureCrawl(itemID, target_urls, meta_data):

    AID = "791b347c-0061-4efa-bb10-a85583294920"

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
        "name": itemID,
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
    URL = (
        f"{BROWSERTRIX_URL}/api/archives/" + AID + "/crawlconfigs/"
    )
    r = requests.post(URL, json=config, headers=headers)
    res = r.json()
    if "added" not in res:
        raise Exception("Failed to create template")
    CID = res["added"]

    # Start Crawl
    URL = (
        f"{BROWSERTRIX_URL}/api/archives/"
        + AID
        + "/crawlconfigs/"
        + CID
        + "/run"
    )
    r = requests.post(URL, headers=headers)
    res = r.json()
    if "started" not in res:
        raise Exception("Failed to start crawl")
    CRAWL_ID = res["started"]

    # Prepeare meta data
    meta = {
        "private": {
            "additionalData": {                    
                "crawl_id": CRAWL_ID,
                "crawl_template_id": CID,
                "crawl_config": config
            }            
        },
        "extra": {
            "DFRLabMetadata": meta_data,
        }
    }

    # Save file as json
    metaPath = TARGET_ROOT_PATH + "/preprocessor_metadata"
    if not os.path.exists(metaPath):
        os.makedirs(metaPath)

    metaFilename = metaPath + "/" + CID + ".json"
    text_file = open(metaFilename, "w")
    text_file.write(json.dumps(meta))
    text_file.close()


with open("starling_sample.csv", newline="\n", encoding="utf8") as csvfile:
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
                json_metadata_template[col_name] = ""
                column_index += 1
            heading = row
        else:
            URL = ast.literal_eval(row[0])
            TS = row[2]

            countlines = countlines + 1

            json_metadata = deepcopy(json_metadata_template)
            column_index = 0
            for item in row:
                json_metadata[heading[column_index]] = item
                column_index += 1

            ConfigureCrawl(TS, URL, json_metadata)

            if countlines >= 20:
                break
