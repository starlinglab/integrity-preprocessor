import copy
import sys
import os
import json
import csv
from zipfile import ZipFile
import io

sys.path.append(
    os.path.dirname(os.path.realpath(__file__)) + "/../integrity_recorder_id"
)
import integrity_recorder_id

integrity_recorder_id.build_recorder_id_json()

metdata_file_timestamp = 0


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

## Proof mode processing
def parse_proofmode_data(proofmode_path):
    data = ""
    filename = ""
    result = {}
    # ProofMode metadata extraction
    with ZipFile(proofmode_path, "r") as proofmode:

        public_pgp = proofmode.read("pubkey.asc").decode("utf-8")
        for file in proofmode.namelist():
            if os.path.splitext(file)[1] == ".csv" and "batchproof.csv" not in file:

                base_file_name = os.path.splitext(file)[0]
                base_file_name = os.path.splitext(base_file_name)[0]                

                data = proofmode.read(file).decode("utf-8")
                
                pgp = proofmode.read(base_file_name + ".asc").decode("utf-8")
                print(data.split("\n"))
                filename = file

                heading = None
          
                
                csv_reader = csv.reader(
                    data.splitlines(),
                    delimiter=","
                )             
                json_metadata_template = {}       
                json_metadata = { "proofs": [] }
                for row in csv_reader:
                    json_metadata_row = {}
                    # Read Heading
                    if heading == None:
                        column_index = 0
                        for col_name in row:
                            json_metadata_template[col_name] = ""
                            column_index += 1
                        heading = row

                    else:
                        if json_metadata == None:
                            json_metadata = copy.deepcopy(json_metadata_template)
                        column_index = 0
                        for item in row:
                            if item.strip() != "":
                                json_metadata_row[heading[column_index]] = item
                            column_index += 1
                        json_metadata["proofs"].append(json_metadata_row)
                
                json_metadata["pgpSignature"] = pgp
                json_metadata["pgpPublicKey"] = public_pgp
                json_metadata['sha256hash'] = json_metadata["proofs"][0]["File Hash SHA256"]
                source_filename = os.path.basename(json_metadata["proofs"][0]["File Path"])
                result[source_filename] = json_metadata
    return result