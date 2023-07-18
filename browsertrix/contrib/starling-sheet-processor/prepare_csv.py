#import dotenv
import requests
import os
import json
import starling_csv
import dotenv
dotenv.load_dotenv()

JWT=  os.environ.get("JWT", "")
PASSWORD  =  os.environ.get("BROWSERTRIX_PASSWORD", "")
FILENAME  =  os.environ.get("FILENAME", "example.csv")
ORG  =  os.environ.get("ORG", "demo-org")
COLLECTION = os.environ.get("COLLECTION", "")
COLLECTIONS = os.environ.get("COLLECTIONS", "")

API_URL=os.environ.get("API_URL","https://api.integrity.stg.starlinglab.org")
USERNAME = os.environ.get("BROWSERTRIX_USERNAME","tools@starlinglab.org")
BROWSERTRIX_URL =os.environ.get("BROWSERTRIX_URL","https://org1.browsertrix.stg.starlinglab.org")
PROFILE="Daryl-Starling"


# Resolve Collections
AID=""
PROFILE_ID=""
PROFILE_NAME=os.environ.get("PROFILE","")
MUTLI_COLLECTION = False
if COLLECTION: 
    MUTLI_COLLECTION = False
    AID = starling_csv.resolve_collection(ORG,COLLECTION,BROWSERTRIX_URL,USERNAME,PASSWORD)
    PROFILE_ID = starling_csv.resolve_profile(AID,PROFILE_NAME,BROWSERTRIX_URL,USERNAME,PASSWORD)
if COLLECTIONS: 
    MUTLI_COLLECTION = True
    collection_json= json.loads(os.environ['COLLECTIONS'])    
    AID={}
    PROFILE_ID={}
    for col in collection_json:
        aid = starling_csv.resolve_collection(ORG,col,BROWSERTRIX_URL,USERNAME,PASSWORD)
        AID[col] = aid
        PROFILE_ID[col] = starling_csv.resolve_profile(aid,PROFILE_NAME,BROWSERTRIX_URL,USERNAME,PASSWORD)


starting_row= int(os.environ.get("START_ROW","6"))
ending_row= int(os.environ.get("END_ROW","9999"))
header_row=1


result = starling_csv.process_starling_csv(FILENAME,starting_row,ending_row,header_row)

# Browsertrix Stuff

#def ConfigureCrawl(AID, target_urls, meta_data, orgKey, sourceId):

for item in result:
    
    CURRENT_AID = AID
    CURRENT_PROFILE = ""
    # Deal with multi collections
    if MUTLI_COLLECTION:
        COLLECTION=item["collection_id"]
        if COLLECTION not in AID:
            print("Skipping - Collection Missing")
            continue
        CURRENT_AID=AID[COLLECTION]
        CURRENT_PROFILE=PROFILE_ID[COLLECTION]

    del(item["collection_id"])

    TARGET_ROOT_PATH = (
        f"/mnt/integrity_store/starling/internal/{ORG}/{COLLECTION}/"
    )
    CID = starling_csv.configure_crawl(CURRENT_AID,CURRENT_PROFILE,item,BROWSERTRIX_URL,USERNAME,PASSWORD,True)
    starling_csv.submit_metadata(ORG,COLLECTION,CURRENT_AID,item, API_URL,JWT)
