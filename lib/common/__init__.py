import copy
import sys
import os
import json
import csv
import shutil
from zipfile import ZipFile
import datetime
import subprocess
import hashlib

import verify
import integrity_recorder_id

integrity_recorder_id.build_recorder_id_json()

metdata_file_timestamp = 0

# Dearmored keys go here
# Should be absolute path
TMP_DIR = "/tmp/integrity-preprocessor/common"

os.makedirs(TMP_DIR, exist_ok=True)


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
                print("Recorder Metadata Change Detected")
                metdata_file_timestamp = current_metadata_file_timestamp
    return recorder_meta_all


def sha256sum(filename):
    with open(filename, "rb") as f:
        bytes = f.read()  # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash


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
