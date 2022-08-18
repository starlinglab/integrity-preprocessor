from copy import deepcopy
import csv
import json
import ast

startrow = 0
endrow = 1000000000
filename = "Starling-Caption-Credit.csv"
config_filename = "Starling-Caption-Credit-config.json"

# Load config
with open(config_filename, "r") as config_file:
    config = json.load(config_file)

with open(filename, newline="\n", encoding="utf8") as csvfile:
    csv_reader = csv.reader(
        csvfile,
        delimiter=",",
    )
    heading = None

    countlines = 0
    json_metadata_template = {}

    result = []
    for row in csv_reader:
        # Read Heading
        if heading == None:
            column_index = 0
            for col_name in row:
                if col_name == "":
                    col_name = "col_" + str(column_index)
                json_metadata_template[col_name] = ""
                column_index += 1
            heading = row
        else:

            countlines = countlines + 1

            json_metadata = deepcopy(json_metadata_template)
            column_index = 0
            for item in row:
                if len(item) > 1 and item[1] == "[":
                    json_metadata[heading[column_index]] = ast.literal_eval(item)
                else:
                    json_metadata[heading[column_index]] = item
                column_index += 1

            filename = config["filenameField"]
            if config["filenameSuffix"]:
                filename = f"{filename}{config['filenameSuffix']}"

            entry = {"filename": filename}

            # Process Field Mappings
            for mapping in config["fieldsMap"]:
                if mapping == "sourceId":
                    entry[mapping] = {
                        "key": config["fieldsMap"][mapping],
                        "value": json_metadata[config["fieldsMap"][mapping]],
                    }
                else:
                    entry[mapping] = json_metadata[config["fieldsMap"][mapping]]

            # Process private/public mappsings
            entry["meta_data_private"] = {}
            entry["meta_data_public"] = {}
            meta_data_private = {}
            meta_data_public = {}
            for item in json_metadata:
                if item in config["fieldsPrivate"]:
                    meta_data_private[item] = json_metadata[item]
                else:
                    meta_data_public[item] = json_metadata[item]

            if "org" in config:
                if len(meta_data_private):
                    entry["meta_data_private"][
                        config["org"] + "Metadata"
                    ] = meta_data_private
                entry["meta_data_public"][config["org"] + "Metadata"] = meta_data_public
            else:
                if len(meta_data_private):
                    entry["meta_data_private"] = meta_data_private
                entry["meta_data_public"] = meta_data_public

            if countlines >= startrow:
                result.append(entry)
            if countlines >= endrow:
                break
with open(f"{filename}.json", "w") as outfile:
    json.dump(result, outfile, indent=2)
