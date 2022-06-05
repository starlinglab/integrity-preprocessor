# Match Primary Key with output SHA256
import os
import json
from pathlib import Path

target = "/mnt/integrity_store/starling/internal/hala-systems/dfrlab-web-archives-remote/preprocessor_metadata/"

files = Path(target).glob("*.txt")
for filename in files:
    # asset
    with open(filename, "r") as f:
        asset = f.readline()

    # id
    ts = 0
    dst = str(filename)[:-7]
    with open(dst, "r") as f:
        j = json.load(f)
        ts = j["extra"]["DFRLabMetadata"]["ts"]
    inputBundle=""
    content=""
    archive=""
    archiveEncrypted=""
    archiveEncrypted=""

    if os.path.exists("/mnt/integrity_store/starling/shared/hala-systems/dfrlab-web-archives-remote/action-archive/" + asset + ".json"):
        with open("/mnt/integrity_store/starling/shared/hala-systems/dfrlab-web-archives-remote/action-archive/" + asset + ".json") as f:
            j2 = json.load(f)
            inputBundle=j2['inputBundle']["sha256"]
            content=j2['content']["sha256"]
            archive=j2['archive']["sha256"]
            archiveEncrypted=j2['archiveEncrypted']["sha256"]
            archiveEncrypted=j2['archiveEncrypted']["cid"]
        
        

    dst = os.path.basename(dst)
    print(f"{ts},{asset},{content},{archive},{archiveEncrypted},{archiveEncrypted}")
