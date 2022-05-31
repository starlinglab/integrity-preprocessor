import copy
import os
import json
import csv
from zipfile import ZipFile
import datetime
import hashlib
import logging

import verify
import integrity_recorder_id

integrity_recorder_id.build_recorder_id_json()

metdata_file_timestamp = 0

# Dearmored keys go here
# Should be absolute path
TMP_DIR = "/tmp/integrity-preprocessor/common"

os.makedirs(TMP_DIR, exist_ok=True)

logging.basicConfig(
    filename=None,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def add_to_pipeline(source_file, content_meta, recorder_meta, stage_path, output_path):

    # Generate SHA and rename asset
    sha256asset = sha256sum(source_file)
    ext = os.path.splitext(source_file)[1]

    # Generate Bundle
    bundleFileName = os.path.join(stage_path, sha256asset + ".zip")
    with ZipFile(bundleFileName + ".part", "w") as archive:
        archive.write(source_file, sha256asset + ext)
        content_meta_data = {"contentMetadata": content_meta}
        archive.writestr(
            sha256asset + "-meta-content.json", json.dumps(content_meta_data)
        )
        archive.writestr(
            sha256asset + "-meta-recorder.json",
            json.dumps(recorder_meta),
        )

    sha256zip = sha256sum(os.path.join(stage_path, sha256asset + ".zip.part"))
    # Rename file for watcher
    os.rename(
        bundleFileName + ".part",
        os.path.join(output_path, sha256zip + ".zip"),
    )
    return os.path.join(output_path, sha256zip + ".zip")


def get_recorder_meta(type):
    global metdata_file_timestamp, recorder_meta_all

    current_metadata_file_timestamp = os.path.getmtime(
        integrity_recorder_id.INTEGRITY_PREPROCESSOR_TARGET_PATH
    )

    if current_metadata_file_timestamp > metdata_file_timestamp:

        if os.path.exists(integrity_recorder_id.INTEGRITY_PREPROCESSOR_TARGET_PATH):
            with open(
                integrity_recorder_id.INTEGRITY_PREPROCESSOR_TARGET_PATH, "r"
            ) as f:
                recorder_meta_all = json.load(f)
                logging.info("Recorder Metadata Change Detected")
                metdata_file_timestamp = current_metadata_file_timestamp
    return recorder_meta_all


def sha256sum(filename):
    hasher = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(32 * 1024), b""):
            hasher.update(byte_block)
        return hasher.hexdigest()

def parse_wacz_data_extra(wacz_path):
    # WACZ metadata extraction
    with ZipFile(wacz_path, "r") as wacz:
        d = json.loads(wacz.read("datapackage-digest.json"))
        extras = {}

        if "signedData" in d:
            # auth sign data
            if "authsignDomain" in d["signedData"]:
                extras["authsignSoftware"] = d["signedData"]["software"]
                extras["authsignDomain"] = d["signedData"]["domain"]
            elif "publicKey" in d["signedData"]:
                extras["localsignSoftware"] = d["signedData"]["software"]
                extras["localsignPublicKey"] = d["signedData"]["publicKey"]
                extras["localsignSignaturey"] = d["signedData"]["signature"]
            else:
                logging.warning(f"{wacz_path} WACZ missing signature ")

        d = json.loads(wacz.read("datapackage.json"))
        extras["waczVersion"] = d["wacz_version"]
        extras["software"] = d["software"]
        extras["dateCrawled"] = d["created"]

        if "title" in d:
            extras["waczTitle"] = d["title"]

        extras["pages"] = {}
        if "pages/pages.jsonl" in wacz.namelist():
            with wacz.open("pages/pages.jsonl") as jsonl_file:
                for line in jsonl_file.readlines():
                    d = json.loads(line)
                    if "url" in d:
                        extras["pages"][d["id"]] = d["url"]
        else:
            logging.info("Missing pages/pages.jsonl in archive %s", wacz_path)

        return extras

## Proof mode processing
def parse_proofmode_data(proofmode_path):
    if not verify.ProofMode().verify(proofmode_path):
        raise Exception("proofmode zip fails to verify")

    data = ""
    result = {}
    date_create = None
    # ProofMode metadata extraction
    with ZipFile(proofmode_path, "r") as proofmode:

        public_pgp = proofmode.read("pubkey.asc").decode("utf-8")

        for file in proofmode.namelist():
            x = proofmode.getinfo(file).date_time
            current_date_create = datetime.datetime(
                x[0], x[1], x[2], x[3], x[4], x[5], 0
            )
            if date_create is None or current_date_create < date_create:
                date_create = current_date_create

            if os.path.splitext(file)[1] == ".csv" and "batchproof.csv" not in file:

                base_file_name = os.path.splitext(file)[0]
                base_file_name = os.path.splitext(base_file_name)[0]

                data = proofmode.read(file).decode("utf-8")

                pgp = proofmode.read(base_file_name + ".asc").decode("utf-8")

                heading = None

                # Convert CSV to JSON
                csv_reader = csv.reader(data.splitlines(), delimiter=",")
                json_metadata_template = {}
                json_metadata = {"proofs": []}
                for row in csv_reader:
                    json_metadata_row = {}
                    # Read Heading
                    if heading == None:
                        column_index = 0
                        for col_name in row:
                            json_metadata_template[col_name] = ""
                            column_index += 1
                        # Add dumy Lat/Long in case proof mode does not generate them
                        json_metadata_template["Location.Latitude"] = 0
                        json_metadata_template["Location.Longitude"] = 0
                        json_metadata_template["Location.Time"] = 0
                        heading = row

                    else:
                        json_metadata_row = copy.deepcopy(json_metadata_template)
                        column_index = 0
                        for item in row:
                            if item.strip() != "":
                                json_metadata_row[heading[column_index]] = item
                            column_index += 1
                        json_metadata["proofs"].append(json_metadata_row)

                json_metadata["pgpSignature"] = pgp
                json_metadata["pgpPublicKey"] = public_pgp
                file_hash = json_metadata["proofs"][0]["File Hash SHA256"]
                json_metadata["sha256hash"] = file_hash
                json_metadata["dateCreate"] = current_date_create.isoformat()
                source_filename = os.path.basename(
                    json_metadata["proofs"][0]["File Path"]
                )
                result[source_filename] = json_metadata

            result["dateCreate"] = date_create.isoformat()

    return result
