from zipfile import ZipFile
import tempfile
import requests
import datetime
import json
import shutil
import os
from os.path import basename
import time


SOURCEPATH = "/mnt/browsertrix"
TARGETPATH = "/mnt/browsertrix-out"
BUCKET = "test-bucket"


# print(response.json())

lastCheck = {}


def incMetric(key):
    if not key in metrics:
        metrics[key] = 0
    metrics[key] += 1


while 1:
    metrics = {}

    auth = {"username": "yurko@hypha.coop", "password": "83UF3iAf87mj9fS"}
    response = requests.post("http://127.0.0.1:9871/api/auth/jwt/login", data=auth)
    access_token = response.json()["access_token"]
    headers = {"Authorization": "Bearer " + access_token}

    response = requests.get("http://127.0.0.1:9871/api/archives", headers=headers)

    for archive in response.json()["archives"]:
        aid = archive["id"]

        if not aid in lastCheck:
            lastCheck[aid] = 0

        response = requests.get(
            "http://127.0.0.1:9871/api/archives/" + aid + "/crawls", headers=headers
        )
        for crawl in response.json()["crawls"]:

            incMetric("crawl_state_" + crawl["state"])

            if crawl["state"] == "complete":
                startDate = datetime.datetime.fromisoformat(crawl["started"])
                finishDate = datetime.datetime.fromisoformat(crawl["finished"])
                startDateString = startDate.strftime("%Y-%m-%d%H%M")
                finishDate = datetime.datetime.fromisoformat(crawl["finished"])

                length = finishDate - startDate

                if length.total_seconds() / 60 < 1:
                    incMetric("crawl_slow_count")

                if finishDate.timestamp() > lastCheck[aid]:
                    lastCheck[aid] = finishDate.timestamp()
                    print(crawl["id"])

                    response = requests.get(
                        "http://127.0.0.1:9871/api/archives/"
                        + aid
                        + "/crawls/"
                        + crawl["id"]
                        + ".json",
                        headers=headers,
                    )
                    crawlReponse = response.json()

                    # path = SOURCEPATH + "/" + BUCKET + "/" + aid + '/data/' + startDateString + "*" + crawl["id"] + '.wacz'
                    waczPath = (
                        SOURCEPATH
                        + "/"
                        + BUCKET
                        + "/"
                        + crawlReponse["resources"][0]["name"]
                    )
                    meta = {}
                    with ZipFile(waczPath, "r") as waczFile:
                        with tempfile.TemporaryDirectory() as td:
                            waczFile.extract("datapackage-digest.json", td)
                            with open(td + "/datapackage-digest.json") as json_file:
                                data = json.load(json_file)
                                print(data)
                                meta["authsign_software"] = data["signedData"][
                                    "software"
                                ]
                                meta["authsign_domain"] = data["signedData"]["domain"]
                            # print(data)
                            waczFile.extract("datapackage.json", td)
                            with open(td + "/datapackage.json") as json_file:
                                data = json.load(json_file)
                                meta["wacz_version"] = data["wacz_version"]
                                meta["created"] = data["created"]
                            # print(data)
                            waczFile.extract("pages/pages.jsonl", td)
                            meta["pages"] = {}
                            with open(td + "/pages/pages.jsonl") as jsonl_file:
                                for jsonLine in jsonl_file.readlines():
                                    data = json.loads(jsonLine)
                                    if "url" in data:
                                        meta["pages"][data["id"]] = data["url"]
                            f = open(td + "/metadata.json", "w")
                            f.write(json.dumps(meta))
                            f.close

                            f = open(td + "/metadata_injestor.json", "w")
                            f.write(json.dumps({}))
                            f.close

                            zipObj = ZipFile(
                                td + "/" + crawlReponse["id"] + ".zip", "w"
                            )
                            zipObj.write(waczPath, basename(waczPath))
                            zipObj.write(td + "/metadata.json", "metadata.json")
                            zipObj.write(
                                td + "/metadata_injestor.json",
                                "/metadata_injestor.json",
                            )
                            zipObj.close

                            shutil.move(
                                td + "/" + crawlReponse["id"] + ".zip",
                                TARGETPATH + "/" + crawlReponse["id"] + ".zip.part",
                            )
                            os.rename(
                                TARGETPATH + "/" + crawlReponse["id"] + ".zip.part",
                                TARGETPATH + "/" + crawlReponse["id"] + ".zip",
                            )

    print(metrics)
