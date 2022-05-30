from copy import deepcopy

import json
import os
import datetime
import zipfile
import tempfile
from zipfile import ZipFile
import io
import csv
import dotenv

# Kludge
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import common


dotenv.load_dotenv()

CONFIG_FILE = os.environ.get("CONFIG_FILE")

with open(CONFIG_FILE) as f:
    config = json.load(f)

default_content = config["content"]


def start_metadata_content(injestor, meta_chat):
    bot_type = injestor["type"]
    meta_content = deepcopy(default_content)
    meta_content["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    if bot_type == "slack":
        meta_content["private"]["slack"] = {}
        meta_content["private"]["slack"]["botAccount"] = injestor["botAccount"]
        meta_content["private"]["slack"]["workspace"] = injestor["workspace"]
    if bot_type == "signal":
        meta_content["private"]["signal"] = {}
        if "phone" in injestor:
            meta_content["private"]["signal"]["phone"] = injestor["phone"]

    if bot_type == "telegram":
        meta_content["private"]["telegram"] = {}
        meta_content["private"]["telegram"]["botAccount"] = injestor["botAccount"]

    meta_content["extras"]["botType"] = bot_type

    if "minDate" in meta_chat:
        meta_min_date = meta_chat["minDate"]
        meta_max_date = meta_chat["maxDate"]
        meta_channels = meta_chat["channels"]

        meta_date_create = ""
        cosmetic_time = ""

        # Define min and max dates
        if meta_min_date > -1:
            meta_date_create = min_date = (
                datetime.datetime.utcfromtimestamp(meta_min_date).isoformat() + "Z",
            )
        if meta_max_date > -1:
            meta_date_create = max_date = (
                datetime.datetime.utcfromtimestamp(meta_max_date).isoformat() + "Z",
            )
        if meta_date_create == "":
            meta_date_create = (datetime.datetime.utcnow().isoformat() + "Z",)

        if meta_min_date > -1:
            cosmetic_date = datetime.datetime.utcfromtimestamp(meta_min_date).strftime(
                "%B %d, %Y"
            )
            cosmetic_time = " at " + datetime.datetime.utcfromtimestamp(
                meta_min_date
            ).strftime("%H:%M")

        else:
            cosmetic_date = "an unknown date"

        meta_content["name"] = f"{bot_type.title()} archive on {cosmetic_date}"

        channel_text = ""
        if len(meta_channels) > 0:
            channel_list = ",".join(meta_channels)
            channel_text = f" of [ {channel_list} ]"

        meta_content[
            "description"
        ] = f"Archive{channel_text} by {bot_type.title()} bot starting on {cosmetic_date}{cosmetic_time}"

        meta_content["extras"]["channels"] = meta_channels
        meta_content["extras"]["dateRange"] = {"from": min_date, "to": max_date}

        meta_content["dateCreated"] = meta_date_create

    return meta_content


def zipFolder(zipfile, path):
    # Iterate over all the files in directory
    for folderName, subfolders, filenames in os.walk(path):
        for filename in filenames:
            # create complete filepath of file in directory
            filePath = os.path.join(folderName, filename)
            # Add file to zip
            zipfile.write(filePath, os.path.basename(filePath))


tmpFolder = "/tmp"


# Parses and groups event files created by telegram both into
# folders representing Y-M-D-Hr format
def telegram_parse_events_into_folders(localPath):
    # Create Date/Time Diretory Structure and move files into it
    for item in os.listdir(localPath):
        if os.path.isfile(os.path.join(localPath, item)):
            fileTimeStamp = os.path.splitext(item)[0]
            fileDateTime = datetime.datetime.fromtimestamp(int(fileTimeStamp))
            currentDateTime = datetime.datetime.utcnow()
            fileTimeDelta = (
                currentDateTime - (fileDateTime + datetime.timedelta(minutes=1))
            ).total_seconds()
            if fileTimeDelta > 0:
                currentFolderDate = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H")
                dir = os.path.join(localPath, currentFolderDate)
                if not os.path.isdir(dir):
                    os.mkdir(dir, 0o660)
                os.rename(
                    os.path.join(localPath, item),
                    os.path.join(localPath, currentFolderDate, item),
                )


def parse_chat_metadata_from_slack(localPath, folder):
    meta = {"dateCreated": "", "maxDate": -1, "minDate": -1, "channels": []}
    # Generate channels for slack
    converstaionFileName = os.path.join(localPath, folder, "conversations.json")
    if os.path.exists(converstaionFileName):
        print (f"FolderMode - MetaExtract {folder} Processing Conversations")
        with open(converstaionFileName) as f:
            channelData = json.load(f)
            for chan in channelData:
                if (
                    "is_member" in channelData[chan]
                    and channelData[chan]["is_member"] == True
                ):
                    meta["channels"].append(channelData[chan]["name"])
    # Generate min date/time for slack
    archive_file_name = os.path.join(localPath, folder, "archive.jsonl")
    if os.path.exists(archive_file_name):
        print (f"FolderMode - MetaExtract {folder} Processing Archive")
        with open(archive_file_name, "r") as f:
            lines = f.readlines()
            for line in lines:
                archive_data = json.loads(line)
                if meta["minDate"] == -1 or meta["minDate"] > float(archive_data["ts"]):
                    meta["minDate"] = float(archive_data["ts"])
                if meta["maxDate"] < float(archive_data["ts"]):
                    meta["maxDate"] = float(archive_data["ts"])
    else:
        return None
    return meta


def parse_chat_metadata_from_telegram(localPath, folder):
    print(f"Telegram - Pasing {folder}")
    meta = {"dateCreated": "", "maxDate": -1, "minDate": -1, "channels": []}
    for archiveName in os.listdir(os.path.join(localPath, folder)):

        # Extract content to temporary folder
        with tempfile.TemporaryDirectory() as d:
            archiveZipFilePath = os.path.join(localPath, folder, archiveName)
            if os.path.splitext(archiveZipFilePath)[1] == ".zip":

                # Extract all files in zip
                with zipfile.ZipFile(archiveZipFilePath, "r") as archive:
                    archive.extractall(d)

                # Loop through json files in directory
                for archiveContentFileName in os.listdir(d):

                    # Process only JSON files
                    current_full_path = os.path.join(d, archiveContentFileName)
                    if os.path.splitext(current_full_path)[1] == ".json":
                        print("Processing " + archiveContentFileName)
                        with open(
                            current_full_path,
                            "r",
                        ) as archiveContentFileHandle:
                            channelData = json.load(archiveContentFileHandle)
                            channelName = (
                                channelData["message"]["chat"]["type"]
                                + " - "
                                + channelData["message"]["chat"]["title"]
                            )
                            if (
                                meta["minDate"] == -1
                                or meta["minDate"] > channelData["message"]["date"]
                            ):
                                meta["minDate"] = channelData["message"]["date"]
                            if meta["maxDate"] < channelData["message"]["date"]:
                                meta["maxDate"] = channelData["message"]["date"]

                            if channelName not in meta["channels"]:
                                meta["channels"].append(channelName)
    return meta

# Process injestor
def process_injestor(injestor):
    injestor_config = config["injestors"][injestor]
    user_config = {}

    # Load userConfig 
    if "userConfig" in injestor_config:
        with open(injestor_config["userConfig"]) as f:
            user_config = json.load(f)

    # Prepeare folders
    stage_path = os.path.join(injestor_config["targetpath"], "tmp")
    output_path_default = os.path.join(injestor_config["targetpath"], "input")
    output_path = output_path_default

    if not os.path.exists(stage_path):
        os.makedirs(stage_path)

    meta_bot_type = injestor_config["type"]
    meta_channels = []
    meta_date_created = ""
    meta_min_date = -1
    meta_max_date = -1
    meta_data = {}

    if injestor_config["type"] == "telegram":
        localPath = injestor_config["localpath"]
        telegram_parse_events_into_folders(localPath)
        recorder_meta = common.get_recorder_meta("telegram_bot")

    if injestor_config["type"] == "slack":
        recorder_meta = common.get_recorder_meta("slack_bot")
        meta_channels = []

    if injestor_config["type"] == "signal":
        recorder_meta = common.get_recorder_meta("signal_bot")

    # Process file mode
    if injestor_config["method"] == "file":
        localPath = injestor_config["localpath"]
        for item in os.listdir(localPath):
            if os.path.isfile(os.path.join(localPath, item)):
                content_meta = start_metadata_content(injestor_config, {})
                filesplit = os.path.splitext(item)
                filename = filesplit[0]
                fileext = filesplit[1]

                # set datCreate to file date/time
                date_file_created = os.path.getmtime(os.path.join(localPath, item))
                content_meta["dateCreated"] = datetime.datetime.fromtimestamp(date_file_created).isoformat() + "Z"

                # Only look for zip files
                if fileext == ".zip":
                    print(f"FileMode - Parsing {item}")
                    with open(localPath + "/" + filename + ".json", "r") as f:
                        signal_metadata = json.load(f)
                        content_meta["private"]["signal"] = signal_metadata

                    # additional specific processing
                    print(
                        f"FileMode - Parsing {item} - Matching "
                        + content_meta["private"]["signal"]["source"]
                    )
                    if content_meta["private"]["signal"]["source"] in user_config:
                        user = user_config[content_meta["private"]["signal"]["source"]]
                        output_path=user["targetpath"]
                        print(f"FileMode - Parsing {item} - Matched " + user["author"]["name"])
                        content_meta["author"] = user["author"]

                        ## TODO org and collection

                    if "processing" in injestor_config:
                        print(f"FileMode - parsing {item} - processing Proofmode")
                        if injestor_config["processing"] == "proofmode":
                            content_meta["private"][
                                "proofmode"
                            ] = common.parse_proofmode_data(
                                localPath + "/" + filename + ".zip"
                            )
                            asset_type = "content"
                            for asset_filename in content_meta["private"]["proofmode"]:
                                ext = os.path.splitext(asset_filename)[1]                                
                                if ext == ".jpg" or ext == ".png" or ext == ".heic":
                                    asset_type = "image"
                                if ext == ".wav" or ext == ".m4a" or ext == ".mp3":
                                    asset_type = "audio"
                                if ext == ".mp4" or ext == ".m4v" or ext == ".avi" or ext == ".mov":
                                    asset_type = "video"

                            content_meta["name"] = f"Authenticated {asset_type}"
                            content_meta["description"] = f"{asset_type.title()} with ProofMode metadata received via Signal"                            
                            content_meta["dateCreated"] = content_meta["private"]["proofmode"]['dateCreate']

                    out_file = common.add_to_pipeline(
                        localPath + "/" + filename + ".zip",
                        content_meta,
                        recorder_meta,
                        stage_path,
                        output_path
                    )
                    print(f"FileMode - parsing {item} - wrote file {out_file}")
                    archived = localPath + "/archived"
                    # Move to archived folder
                    if not os.path.isdir(archived):
                        os.mkdir(archived, 0o660)
                    os.rename(
                        localPath + "/" + filename + ".zip",
                        archived + "/" + filename + ".zip",
                    )
                    os.rename(
                        localPath + "/" + filename + ".json",
                        archived + "/" + filename + ".json",
                    )
                    print(f"FileMode - parsing {item} - Moved to Archive")

    # Process folder mode
    if injestor_config["method"] == "folder":
        localPath = injestor_config["localpath"]

        # Loop through date/time structured directories
        for item in os.listdir(localPath):
            if os.path.isdir(os.path.join(localPath, item)):

                # Check if already processed and define datetime value of directory
                dirParts = item.split("-")
                if dirParts[0] != "P" and dirParts[0] != "S":
                    # Calculate date/time for the folder
                    if len(dirParts) == 3:
                        folderDateTime = datetime.datetime.strptime(
                            item, "%Y-%m-%d"
                        ) + datetime.timedelta(days=1)
                    elif len(dirParts) == 4:
                        folderDateTime = datetime.datetime.strptime(
                            item, "%Y-%m-%d-%H"
                        ) + datetime.timedelta(hours=1)
                    else:
                        print("Failed to parse {item}")
                    # Offset datetime for 1 min to give any writing time to finish
                    folderDateTime = folderDateTime + datetime.timedelta(minutes=1)
                    currentDateTime = datetime.datetime.utcnow()
                    folderTimeDelta = (currentDateTime - folderDateTime).total_seconds()

                    # Folder time has passed, process
                    if folderTimeDelta > 0:

                        if injestor_config["type"] == "slack":
                            print(f"FolderMode - Parsing {item} ({injestor}) Slack")
                            meta_chat = parse_chat_metadata_from_slack(localPath, item)
                        elif injestor_config["type"] == "telegram":
                            print(f"FolderMode - Parsing {item} ({injestor}) Telegram")
                            meta_chat = parse_chat_metadata_from_telegram(
                                localPath, item
                            )
                        else:
                            print(f"FolderMode - Skipping {item} ({injestor}) UNKNOWN MODE")


                        # No data to deal with, skip folder
                        if meta_chat is None:
                            print(f"FolderMode - Skipping {item} - meta_chat empty")
                            os.rename(
                                os.path.join(localPath, item),
                                os.path.join(localPath, "S-" + item),
                            )
                            continue

                        # Zip up content of directory to a temp file
                        temp_filename = os.path.join(
                            tmpFolder, injestor + str(folderDateTime.timestamp()) + ".zip"
                        )
                        with zipfile.ZipFile(temp_filename, "w") as archive:
                            zipFolder(archive, os.path.join(localPath, item))

                        content_meta = start_metadata_content(
                            injestor_config,
                            meta_chat
                        )

                        out_file = common.add_to_pipeline(
                            temp_filename,
                            content_meta,
                            recorder_meta,
                            stage_path,
                            output_path,
                        )
                        print(f"FolderMode - Output {item} - Write file {out_file}")

                        # Rename folder to prevent re-processing
                        os.rename(
                            os.path.join(localPath, item),
                            os.path.join(localPath, "P-" + item),
                        )


while True:
    try:
        for injestor in config["injestors"]:
            process_injestor(injestor)
    except Exception as inst:
        raise inst
