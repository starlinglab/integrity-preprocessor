# Purge all crawls and crawlconfigs from an archive
AID = "791b347c-0061-4efa-bb10-a85583294920"

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

USERNAME = os.environ.get("BROWSERTRIX_USERNAME")
PASSWORD = os.environ.get("BROWSERTRIX_PASSWORD")
BROWSERTRIX_URL = os.environ.get("BROWSERTRIX_URL", "http://127.0.0.1:9871")

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

# CRAWLS

URL = f"{BROWSERTRIX_URL}/api/archives/{AID}/crawls"
resp = requests.get(URL, headers=headers)

i = []
for c in resp.json()["crawls"]:
    print(c)
    cid = c["id"]
    i.append(c["id"])
    URL = f"{BROWSERTRIX_URL}/api/archives/{AID}/crawls/{cid}/cancel"
    resp = requests.post(URL, headers=headers)

URL = f"{BROWSERTRIX_URL}/api/archives/{AID}/crawls/delete"

jsons = {"crawl_ids": i}
resp = requests.post(URL, headers=headers, json=jsons)
print(resp.json())


# /archives/{aid}/crawls/delete

# CONFIGS
URL = f"{BROWSERTRIX_URL}/api/archives/{AID}/crawlconfigs"
resp = requests.get(URL, headers=headers)
print(json.dumps(resp.json(), indent=2))


for c in resp.json()["crawlConfigs"]:

    cid = c["id"]
    URL = f"{BROWSERTRIX_URL}/api/archives/{AID}/crawlconfigs/{cid}"
    resp = requests.delete(URL, headers=headers)

# /archives/{aid}/crawlconfigs
