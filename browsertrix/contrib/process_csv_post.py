# Match Primary Key with output SHA256
import os
import json
from pathlib import Path

target = "/mnt/integrity_store/starling/internal/starling-lab-test/test-web-archive-dfrlab/preprocessor_metadata/"

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
        ts = j["additional_data"]["ts"]

    dst = os.path.basename(dst)
    print(f"{ts},{asset}")
