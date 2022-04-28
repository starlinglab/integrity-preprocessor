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

        for file in proofmode.namelist():
            if os.path.splitext(file)[1] == ".csv" and "batchproof.csv" not in file:
                data = proofmode.read(file).decode("utf-8")
                filename = file
                data_split = data.split("\n")
                current_line = 0
                res = []
                brokenline = 0
                for line in data_split:
                    # Add to arary if its the next line
                    if len(res) <= current_line:
                        res.append("")
                    # Skip over is it is an empty line
                    if len(line.strip()) < 4:
                        current_line = current_line - 1
                    # poorly parsed line here, bring it up one level
                    elif len(line) < 78:
                        current_line = current_line - 1
                        brokenline = 1
                    # this is the next line after the broken lines, so still broken
                    elif brokenline == 1:
                        current_line = current_line - 1
                        brokenline = 0

                    # Add line to current line (moving broken lines up)
                    res[current_line] = res[current_line] + line.strip()
                    current_line = current_line + 1

                heading = None

                with io.StringIO("\n".join(res), newline="\n") as csvfile:
                    csv_reader = csv.reader(
                        csvfile,
                        delimiter=",",
                    )
                    json_metadata_template = {}
                    json_metadata = {}
                    for row in csv_reader:
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
                                    json_metadata[heading[column_index]] = item
                                column_index += 1
                    source_filename = os.path.basename(json_metadata["File Path"])
                    result[source_filename] = json_metadata
    return result
