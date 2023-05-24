import requests
#import dotenv
import os
import json
import starling_csv

JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJvcmdhbml6YXRpb25faWQiOiJoeXBoYWNvb3AiLCJhdXRob3IiOnsidHlwZSI6IlBlcnNvbiIsImlkZW50aWZpZXIiOiJodHRwczovL2h5cGhhLmNvb3AiLCJuYW1lIjoiQmVuZWRpY3QgTGF1In0sInR3aXR0ZXIiOnsidHlwZSI6Ik9yZ2FuaXphdGlvbiIsImlkZW50aWZpZXIiOiJodHRwczovL2h5cGhhLmNvb3AiLCJuYW1lIjoiSHlwaGFDb29wIn0sImNvcHlyaWdodCI6IkNvcHlyaWdodCAoQykgMjAyMSBIeXBoYSBXb3JrZXIgQ28tb3BlcmF0aXZlLiBBbGwgUmlnaHRzIFJlc2VydmVkLiJ9.gqRi6ZJ54c1g7sPQAfcj5Je1WlRCPSZ1c0aY-3X38jE"
API_URL="https://api.integrity-dev.stg.starlinglab.org"
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
