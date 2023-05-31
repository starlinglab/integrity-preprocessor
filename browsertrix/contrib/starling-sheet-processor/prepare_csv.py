#import dotenv
import requests
import os
import json
import starling_csv

JWT="XXXXXXXXXXXXXXX"
PASSWORD = "XXXXXXXXXXXXXXXXX"
FILENAME="XXXXXXXXXXXXXXXXXXXXX.csv"


# MUTLI_COLLECTION = True
# AID = {
# "collection1":"00000000-0000-0000-0000-00000000000",
# "collection2":"00000000-0000-0000-0000-00000000000",
# "collection3":"00000000-0000-0000-0000-00000000000",
# }

MUTLI_COLLECTION = False
AID = "00000000-0000-0000-0000-00000000000" # org id

ORG = "demo"
COLLECTION = "starling-lab"

API_URL="https://api.integrity.stg.starlinglab.org"
USERNAME = "tools@starlinglab.org"
BROWSERTRIX_URL = "https://org1.browsertrix.stg.starlinglab.org"

starting_row=6
ending_row=99999
header_row=1


result = starling_csv.process_starling_csv(FILENAME,starting_row,ending_row,header_row)

# Browsertrix Stuff

#def ConfigureCrawl(AID, target_urls, meta_data, orgKey, sourceId):

for item in result:
    
    CURRENT_AID = AID

    # Deal with multi collections
    if MUTLI_COLLECTION:
        COLLECTION=item["collection_id"]
        CURRENT_AID=AID[COLLECTION]

    del(item["collection_id"])

    TARGET_ROOT_PATH = (
        f"/mnt/integrity_store/starling/internal/{ORG}/{COLLECTION}/"
    )
    CID = starling_csv.configure_crawl(CURRENT_AID,item,BROWSERTRIX_URL,USERNAME,PASSWORD,True)
    starling_csv.submit_metadata(ORG,COLLECTION,CURRENT_AID,item, API_URL,JWT)
