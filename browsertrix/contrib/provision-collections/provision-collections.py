import requests
import sys
import subprocess
import json
import os
import dotenv

dotenv.load_dotenv("/root/integrity-preprocessor/browsertrix/.env")
config_dir = os.environ.get("CONFIG_FILE")

BROWSERTRIX_CREDENTIALS = os.environ.get("BROWSERTRIX_CREDENTIALS")

config_path = "/root/.integrity/"
base_url = "/mnt/integrity_store/starling/internal"

# password="PASSW0RD!"
if os.path.exists(BROWSERTRIX_CREDENTIALS):
    with open(BROWSERTRIX_CREDENTIALS, "r") as f:
        SERVERS = json.load(f)

def get_token_bypass(email, password, server):
    # AUTH
    auth = {"username": email, "password": password}
    URL = f"https://{server}/api/auth/jwt/login"
    access_token = ""
    resp = requests.post(URL, data=auth)
    response_json = resp.json()
    if "access_token" not in response_json:
        raise Exception("Access Token Failed")
    access_token = response_json["access_token"]

    return {"Authorization": "Bearer " + access_token}


def get_token(server):
    email = SERVERS[server]["login"]
    password = SERVERS[server]["password"]
    if "headers" not in SERVERS[server]:
        SERVERS[server]["headers"] = ""
    if SERVERS[server]["headers"] == "":
        SERVERS[server]["headers"] = get_token_bypass(email, password, server)
    return SERVERS[server]["headers"]


def create_org(org_name, server):
    header = get_token(server)
    URL = f"https://{server}/api/orgs/create"
    d = {"name": org_name}
    r = requests.post(URL, headers=header, json=d)
    return r.json()

def get_org(org_name, server):
    header = get_token(server)
    URL = f"https://{server}/api/orgs"
    d = {"name": org_name}
    r = requests.get(URL, headers=header)
    res = r.json()
    for o in res["items"]:
        if o["name"] == org_name:
            return o

data = {}

with open(f"{config_path}preprocessor-browsertrix-collections.json", "r") as f:
    data = json.load(f)

result = {"collections": {}}
for item_data in data:
    server = item_data["server"]
    archive_name = item_data["orgID"] + "_" + item_data["collectionID"]
    if "suffix" in item_data:
        archive_name = archive_name + "_" + item_data['suffix']
    aid = ""
    btrx_org = get_org(archive_name, server)
    if btrx_org is None:
        print(f"Creating {archive_name}")
        res = create_org(archive_name, server)
#        invite_user_to_org(header,"integrity@starlinglab.org",org["id"])
        btrx_org = get_org(archive_name, server)
    author = None
    if "author" in item_data:
        author = item_data['author']
    col = item_data["collectionID"]
    org = item_data["orgID"]
    orgid = btrx_org["id"]
    print(item_data)
    result["collections"][orgid] = {
        "collectionID": col,
        "organizationID":org,
        "target_path": f"{base_url}/{org}/{col}/",
        "author": author,
        "server": server
    }

print(config_dir)
f = open(config_dir, 'w')
json.dump(result, f, indent=2)