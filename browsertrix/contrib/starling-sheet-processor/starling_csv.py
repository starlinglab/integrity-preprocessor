import requests
import json
import csv

def process_starling_csv(filename,starting_row,endding_row,header_row):
    with open(filename, newline="\n", encoding="utf8") as csvfile:
        csv_reader = csv.reader(
            csvfile,
            delimiter=",",
        )

        header_name_from_index={}    
        header_index_from_name={}

        row_count = -1
        result=[]
        for row in csv_reader:
            row_count = row_count + 1

            if row_count == header_row:             
                c=0
                for col in row:
                    header_name_from_index[c]=col
                    header_index_from_name[col]=c
                    c=c+1
            
            if row_count >= starting_row and row_count<=endding_row:

                r = {
                    "path":"",
                    "sourceId":{},
                    "name":"",
                    "description":"",
                    "author": {
                        "@type":"",
                        "name":"",
                        "identifier":""
                    },
                    "extras": {},
                    "private": {}                
                }
                row_key = f"{row[1]}_{row[2]}"

                r["path"]=row[header_index_from_name["path"]]
                r["sourceId"]["key"]=row[header_index_from_name["asset_id:key"]]
                r["sourceId"]["value"]=row[header_index_from_name["asset_id:value"]]
                r["name"]=row[header_index_from_name["name"]]
                r["description"]=row[header_index_from_name["description"]]
                r["author"]["@type"]=row[header_index_from_name["author:type"]]
                r["author"]["name"]=row[header_index_from_name["author:name"]]
                r["author"]["identifier"]=row[header_index_from_name["author:identifier"]]

                c_index=-1
                for col in row:
                    c_index=c_index+1
                
                    current_header=header_name_from_index[c_index]
                                    
                    if current_header.startswith("extras:") or current_header.startswith("private:"):
                        field_type="private"
                        if current_header.startswith("extras:"):
                            field_type="extras"

                        stub = current_header.split(":",2)[1]
                        stub_index = stub.split("_",2)[1]                    
                        stub = stub.split("_",2)[0]


                        if stub=="key":
                            key_value_name=f"{field_type}:value_{stub_index}"
                            if not key_value_name in header_index_from_name:
                                print(f"cant find {key_value_name}")
                                exit(1)

                            metadata_key=row[header_index_from_name[current_header]]
                            metadata_value=header_index_from_name[key_value_name]

                            try:
                                if row[metadata_value].startswith("["): 
                                    a=row[metadata_value]
                                    row[metadata_value] = json.loads(a)
                            except:
                                print("not json")
                            if metadata_key!="":
                                r[field_type][metadata_key]=row[metadata_value]

                result.append(r)
    return result

def configure_crawl(AID,meta_data,BROWSERTRIX_URL,USERNAME,PASSWORD, RUN):
    target_urls = [meta_data["path"]]
    target_urls_seeds=[]
    for t in target_urls:
          seed={}
          seed["url"]=t
          target_urls_seeds.append(seed)

    orgKey = "sourceMetadata"
    sourceId =  meta_data["sourceId"]
    itemID = sourceId["value"]    

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
        "runNow": RUN,
        "config": {
            "seeds": target_urls_seeds,
            "scopeType": "page",
            "depth": -1,
            "limit": 0,
            "extraHops": 0,
            "behaviorTimeout": 300,
            "behaviors": "autoscroll,autoplay,autofetch,siteSpecific",
        },
    }
    URL = f"{BROWSERTRIX_URL}/api/orgs/" + AID + "/crawlconfigs/"


    r = requests.post(URL, json=config, headers=headers)
    res = r.json()
  
    if "added" not in res:
        print(res)
        raise Exception("Failed to create template")
        
    CID = res["added"]
    print(f"Added {itemID} -  {CID}")
    return CID

def submit_metadata(ORG,COLLECTION,CID,meta_data, API_URL,JWT):

    data = {
        "preprocessor": "browsertrix",
        "collection": COLLECTION,
        "organization": ORG,
        "crawl_id": CID,
        "meta_data": meta_data
    }
    
    header = {f"Authorization": f"Bearer {JWT}"}
    
    res=requests.post(f"{API_URL}/v1/assets/metadata/append",json=data,headers=header)