from copy import deepcopy

import json
import os
import datetime
import zipfile
import hashlib
import tempfile
from zipfile import ZipFile
import io
import csv
import dotenv

# Kludge
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../common")
import common


dotenv.load_dotenv()

CONFIG_FILE = os.environ.get("CONFIG_FILE")

with open(CONFIG_FILE) as f:
    config = json.load(f)


default_content = config["content"]
default_author = default_content["author"]


def start_metadata_content(injestor):
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

    return meta_content


def genreate_folder_metadata(meta_content, meta_channels, meta_min_date, meta_max_date):

    # Calculate dates
    min_date = ""
    max_date = ""
    meta_date_create = ""
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

    # Populate
    bot_name = bot_type.title()
    meta_content["name"] = f"{bot_name} archive on {cosmetic_date}"

    channel_text = ""
    if len(meta_channels) > 0:
        channel_list = ",".join(meta_channels)
        channel_text = f" of [ {channel_list} ]"

    meta_content[
        "description"
    ] = f"Archive{channel_text} by {bot_name} bot starting on {cosmetic_date}{cosmetic_time}"

    meta_content["extras"]["channels"] = meta_channels
    meta_content["extras"]["dateRange"] = {"from": min_date, "to": max_date}

    meta_content["dateCreated"] = meta_date_create
    return {"contentMetadata": meta_content}


def generate_metadata_content(meta_chat, injestor):
    bot_type = injestor["type"]
    meta_min_date = meta_chat["minDate"]
    meta_max_date = meta_chat["maxDate"]
    meta_channels = meta_chat["channels"]

    meta_date_create = ""
    cosmetic_time = ""
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

    meta_content = deepcopy(default_content)

    bot_name = bot_type.title()
    meta_content["name"] = f"{bot_name} archive on {cosmetic_date}"

    channel_text = ""
    if len(meta_channels) > 0:
        channel_list = ",".join(meta_channels)
        channel_text = f" of [ {channel_list} ]"

    meta_content[
        "description"
    ] = f"Archive{channel_text} by {bot_name} bot starting on {cosmetic_date}{cosmetic_time}"

    extras = {}
    private = {}

    extras["channels"] = meta_channels
    extras["dateRange"] = {"from": min_date, "to": max_date}

    if bot_type == "slack":
        private["slack"] = {}
        private["slack"]["botAccount"] = injestor["botAccount"]
        private["slack"]["workspace"] = injestor["workspace"]
    if bot_type == "signal":
        private["signal"] = {}
        private["signal"]["phone"] = injestor["phone"]
    if bot_type == "telegram":
        private["telegram"] = {}
        private["telegram"]["botAccount"] = injestor["botAccount"]

    meta_content["dateCreated"] = meta_date_create
    meta_content["extras"] = extras
    meta_content["private"] = private
    meta_content["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    return {"contentMetadata": meta_content}


def sha256sum(filename):
    with open(filename, "rb") as f:
        bytes = f.read()  # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash


def zipFolder(zipfile, path):
    # Iterate over all the files in directory
    for folderName, subfolders, filenames in os.walk(path):
        for filename in filenames:
            # create complete filepath of file in directory
            filePath = os.path.join(folderName, filename)
            # Add file to zip
            zipfile.write(filePath, os.path.basename(filePath))


tmpFolder = "/tmp"


def add_to_pipeline(source_file, content_meta, recorder_meta, stagePath, outputPath):

    # Generate SHA and rename asset
    sha256asset = sha256sum(source_file)
    ext = os.path.splitext(source_file)[1]

    # Generate Bundle
    bundleFileName = os.path.join(stagePath, sha256asset + ".zip")
    with zipfile.ZipFile(bundleFileName + ".part", "w") as archive:
        archive.write(source_file, sha256asset + ext)
        archive.writestr(sha256asset + "-meta-content.json", json.dumps(content_meta))
        archive.writestr(
            sha256asset + "-meta-recorder.json",
            json.dumps(recorder_meta),
        )

    sha256zip = sha256sum(os.path.join(stagePath, sha256asset + ".zip.part"))
    # Rename file for watcher
    os.rename(
        bundleFileName + ".part",
        os.path.join(outputPath, sha256zip + ".zip"),
    )


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
        with open(converstaionFileName) as f:
            channelData = json.load(f)
            for chan in channelData:
                if "is_member" in channelData[chan] and channelData[chan]["is_member"] == True:
                    meta["channels"].append(channelData[chan]["name"])

    # Generate min date/time for slack
    archive_file_name = os.path.join(localPath, folder, "archive.jsonl")
    if os.path.exists(archive_file_name):
        with open(archive_file_name, "r") as f:
            lines = f.readlines()
            for line in lines:
                channelData = json.loads(line)
                if meta["minDate"] == -1 or meta["minDate"] > float(channelData["ts"]):
                    meta["minDate"] = float(channelData["ts"])
                if meta["maxDate"] < float(channelData["ts"]):
                    meta["maxDate"] = float(channelData["ts"])
    return meta


def parse_chat_metadata_from_telegram(localPath, folder):
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


def process_injestor(key):
    injestorConfig = config["injestors"][key]

    stagePath = os.path.join(injestorConfig["targetpath"], "tmp")
    outputPath = os.path.join(injestorConfig["targetpath"], "input")

    if not os.path.exists(stagePath):
        os.makedirs(stagePath)

    content_meta = start_metadata_content(injestorConfig)

    #############################
    # TELEGRAM BOT FOLDER GROUP #
    #############################
    # Group telegram archive into folders

    meta_bot_type = injestorConfig["type"]
    meta_channels = []
    meta_date_created = ""
    meta_min_date = -1
    meta_max_date = -1
    meta_data = {}

    if injestorConfig["type"] == "telegram":
        localPath = injestorConfig["localpath"]
        telegram_parse_events_into_folders(localPath)
        recorder_meta = common.get_recorder_meta("telegram_bot")

    if injestorConfig["type"] == "slack":
        recorder_meta = common.get_recorder_meta("slack_bot")
        meta_channels = []

    if injestorConfig["type"] == "signal":
        recorder_meta = common.get_recorder_meta("signal_bot")

    # Process file mode
    if injestorConfig["method"] == "file":
        localPath = injestorConfig["localpath"]
        for item in os.listdir(localPath):
            if os.path.isfile(os.path.join(localPath, item)):
                filesplit = os.path.splitext(item)
                filename = filesplit[0]
                fileext = filesplit[1]

                # Only look for zip files
                if fileext == ".zip":
                    with open(localPath + "/" + filename + ".json", "r") as f:
                        signal_metadata = json.load(f)
                        content_meta["private"]["signal"] = signal_metadata

                    # additional specific processing
                    if "processing" in injestorConfig:
                        if injestorConfig["processing"] == "proofmode":
                            content_meta["name"] = ("Authenticated image",)
                            content_meta["description"] = (
                                "Image with ProofMode metadata received via Signal",
                            )
                            content_meta["private"][
                                "proofmode"
                            ] = common.parse_proofmode_data(
                                localPath + "/" + filename + ".zip"
                            )

                    add_to_pipeline(
                        localPath + "/" + filename + ".zip",
                        content_meta,
                        recorder_meta,
                        stagePath,
                        outputPath,
                    )
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

    # Process folder mode
    if injestorConfig["method"] == "folder":
        localPath = injestorConfig["localpath"]

        # Loop through date/time structured directories
        for item in os.listdir(localPath):
            if os.path.isdir(os.path.join(localPath, item)):

                # Check if already processed and define datetime value of directory
                dirParts = item.split("-")
                if dirParts[0] != "P":
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

                        print(key + " Processing Asset " + item)

                        if injestorConfig["type"] == "slack":
                            meta_chat = parse_chat_metadata_from_slack(localPath, item)

                        if injestorConfig["type"] == "telegram":
                            print("telergram processing")
                            meta_chat = parse_chat_metadata_from_telegram(
                                localPath, item
                            )

                        # Zip up content of directory to a temp file
                        tmpFileName = os.path.join(
                            tmpFolder, key + str(folderDateTime.timestamp()) + ".zip"
                        )
                        with zipfile.ZipFile(tmpFileName, "w") as archive:
                            zipFolder(archive, os.path.join(localPath, item))

                        content_meta = generate_metadata_content(
                            meta_chat,
                            injestorConfig,
                        )

                        add_to_pipeline(
                            tmpFileName,
                            content_meta,
                            recorder_meta,
                            stagePath,
                            outputPath,
                        )

                        # Rename folder to prevent re-processing
                        os.rename(
                            os.path.join(localPath, item),
                            os.path.join(localPath, "P-" + item),
                        )


while True:
    try:
        for key in config["injestors"]:
            process_injestor(key)
    except Exception as inst:
        raise inst
