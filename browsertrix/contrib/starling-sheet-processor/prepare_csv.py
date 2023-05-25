import requests
#import dotenv
import os
import json
import starling_csv

JWT="xxxxxxxxxxxxxxxx"
API_URL="https://api.integrity.stg.starlinglab.org"
USERNAME = "tools@starlinglab.org"
PASSWORD = "<PASSWORD>"
BROWSERTRIX_URL = "https://org1.browsertrix.stg.starlinglab.org"
ORG = "demo"
COLLECTION = "starling-lab"

AID = "a2df7b39-4fce-483f-a929-9c4ee2f0f375" # org id
FILENAME="TEST1 - Sheet1.csv"

starting_row=6
endding_row=99999
header_row=1

TARGET_ROOT_PATH = (
    f"/mnt/integrity_store/starling/internal/{ORG}/{COLLECTION}/"
)


result = starling_csv.process_starling_csv(FILENAME,starting_row,endding_row,header_row)


# Browsertrix Stuff

#def ConfigureCrawl(AID, target_urls, meta_data, orgKey, sourceId):

for item in result:
    CID = starling_csv.configure_crawl(AID,item,BROWSERTRIX_URL,USERNAME,PASSWORD)
    starling_csv.submit_metadata(ORG,COLLECTION,CID,item, API_URL,JWT)
