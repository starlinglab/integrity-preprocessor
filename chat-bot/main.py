from copy import deepcopy

import json
import os
import datetime
import zipfile
import hashlib
import tempfile

# Kludge
import sys

sys.path.append(
    os.path.dirname(os.path.realpath(__file__)) + "/../integrity_recorder_id"
)
import integrity_recorder_id

metdata_file_timestamp = 0


def getRecorderMeta(type):
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


default_author = {
    "@type": "Organization",
    "identifier": "https://starlinglab.org",
    "name": "Starling Lab",
}

default_content = {
    "name": "Chat bot archive",
    "mine": "application/wacz",
    "description": "Archive collected by chat bot",
    "author": default_author,
}


def generate_metadata_content(
    bot_type, meta_channels, meta_date_created, meta_min_date, meta_max_date
):

    min_date = ""
    max_date = ""
    if meta_min_date > -1:
        min_date = (
            datetime.datetime.utcfromtimestamp(meta_min_date).isoformat() + "Z",
        )
    if meta_max_date > -1:
        max_date = (
            datetime.datetime.utcfromtimestamp(meta_max_date).isoformat() + "Z",
        )
    if meta_min_date > -1:
        cosmetic_date = datetime.datetime.utcfromtimestamp(meta_min_date).strftime(
            "%B, %d %Y"
        )
    else:
        cosmetic_date = "an unknown date"

    meta_content = deepcopy(default_content)
    
    bot_name= bot_type.title()
    meta_content["name"] = f"{bot_name} archive on {cosmetic_date}"

    channel_text = ""
    if len(meta_channels) > 1:
        channel_list = ",".join("meta_channels")
        channel_text = f" of [ {channel_list} ]"

    meta_content[
        "description"
    ] = f"Archive of {channel_text} by {bot_name} bot starting on {min_date}"

    extras = {}
    private = {}

    extras["channels"] = meta_channels
    extras["dateRange"] = {"from": min_date, "to": max_date}

    meta_content["dateCreated"] = meta_date_created
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
config = {
    "injestors": {
        "slack_archive_bot_workspace-0": {
            "type": "slack",
            "method": "folder",
            "localpath": "/mnt/store/slack_archive_bot_workspace-0",
            "targetpath": "/mnt/integrity_store/starling/internal/starling-lab-test/test-bot-archive-slack",
        },
        "telegram_archive_bot_testbot1": {
            "type": "telegram",
            "method": "folder",
            "localpath": "/mnt/store/telegram_archive_bot_testbot1/archive",
            "targetpath": "/mnt/integrity_store/starling/internal/starling-lab-test/test-bot-archive-telegram",
        },
    }
}


def processInjestor(key):
    injestorConfig = config["injestors"][key]

    stagePath = os.path.join(injestorConfig["targetpath"], "tmp")
    outputPath = os.path.join(injestorConfig["targetpath"], "input")

    if not os.path.exists(stagePath):
        os.makedirs(stagePath)

    #############################
    # TELEGRAM BOT FOLDER GROUP #
    #############################
    # Group telegram archive into folders

    meta_bot_type = injestorConfig["type"]
    meta_channels = []
    meta_date_created = ""
    meta_min_date = -1
    meta_max_date = -1

    if injestorConfig["type"] == "telegram":
        localPath = injestorConfig["localpath"]
        for item in os.listdir(localPath):
            if os.path.isfile(os.path.join(localPath, item)):
                fileTimeStamp = os.path.splitext(item)[0]
                fileDateTime = datetime.datetime.fromtimestamp(int(fileTimeStamp))
                currentDateTime = datetime.datetime.utcnow()
                fileTimeDelta = (
                    currentDateTime - (fileDateTime + datetime.timedelta(minutes=1))
                ).total_seconds()
                if fileTimeDelta > 0:
                    currentFolderDate = datetime.datetime.utcnow().strftime(
                        "%Y-%m-%d-%H"
                    )
                    dir = os.path.join(localPath, currentFolderDate)
                    if not os.path.isdir(dir):
                        os.mkdir(dir, 0o660)
                    os.rename(
                        os.path.join(localPath, item),
                        os.path.join(localPath, currentFolderDate, item),
                    )
        content_meta = {}
        recorder_meta = getRecorderMeta("telegram_bot")

    if injestorConfig["type"] == "slack":
        content_meta = {}
        recorder_meta = getRecorderMeta("slack_bot")

    meta_channels = []
    if injestorConfig["method"] == "folder":
        localPath = injestorConfig["localpath"]
        for item in os.listdir(localPath):
            # Process only directories
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

                            converstaionFileName = os.path.join(
                                localPath, item, "conversations.json"
                            )
                            with open(converstaionFileName) as f:
                                channelData = json.load(f)
                                for chan in channelData:
                                    if channelData[chan]["is_member"] == True:
                                        meta_channels.append(channelData[chan]["name"])
                            archive_file_name = os.path.join(
                                localPath, item, "archive.jsonl"
                            )
                            with open(archive_file_name, "r") as f:
                                lines = f.readlines()
                                for line in lines:
                                    channelData = json.loads(line)
                                    if meta_min_date == -1 or meta_min_date > float(
                                        channelData["ts"]
                                    ):
                                        meta_min_date = float(channelData["ts"])
                                    if meta_max_date < float(channelData["ts"]):
                                        meta_max_date = float(channelData["ts"])

                        if injestorConfig["type"] == "telegram":
                            print("telergram processing")

                            # Loop through items in archive
                            for archiveName in os.listdir(
                                os.path.join(localPath, item)
                            ):

                                # Extract content to temporary folder
                                with tempfile.TemporaryDirectory() as d:
                                    archiveZipFilePath = os.path.join(
                                        localPath, item, archiveName
                                    )
                                    if (
                                        os.path.splitext(archiveZipFilePath)[1]
                                        == ".zip"
                                    ):

                                        # Extract all files in zip
                                        with zipfile.ZipFile(
                                            archiveZipFilePath, "r"
                                        ) as archive:
                                            archive.extractall(d)

                                            # Loop through json files in directory
                                            for archiveContentFileName in os.listdir(d):

                                                # Process only JSON files
                                                if (
                                                    os.path.splitext(
                                                        os.path.join(
                                                            d, archiveContentFileName
                                                        )
                                                    )[1]
                                                    == ".json"
                                                ):
                                                    print(
                                                        "Processing "
                                                        + archiveContentFileName
                                                    )
                                                    with open(
                                                        os.path.join(
                                                            d, archiveContentFileName
                                                        ),
                                                        "r",
                                                    ) as archiveContentFileHandle:
                                                        channelData = json.load(
                                                            archiveContentFileHandle
                                                        )
                                                        channelName = ( channelData["message"]["chat"]["type"] + " - " + channelData["message"]["chat"]["title"])
                                                        if (meta_min_date == -1 or meta_min_date> channelData["message"]["date"]):
                                                            meta_min_date = channelData["message"]["date"]
                                                        if (meta_max_date < channelData["message"]["date"]):
                                                            meta_max_date = channelData["message"]["date"]

                                                        if (channelName not in meta_channels):
                                                            meta_channels.append(channelName)

                    # Zip up content of directory to a temp file
                    tmpFileName = os.path.join(
                        tmpFolder, key + str(folderDateTime.timestamp()) + ".zip"
                    )
                    with zipfile.ZipFile(tmpFileName, "w") as archive:
                        zipFolder(archive, os.path.join(localPath, item))

                    content_meta = generate_metadata_content(
                        meta_bot_type,
                        meta_channels,
                        meta_date_created,
                        meta_min_date,
                        meta_max_date,
                    )

                    # Generate SHA and rename asset
                    sha256asset = sha256sum(tmpFileName)
                    assetFileName = os.path.join(tmpFolder, sha256asset + ".zip")
                    os.rename(tmpFileName, assetFileName)

                    # Generate Bundle
                    bundleFileName = os.path.join(stagePath, sha256asset + ".zip")
                    with zipfile.ZipFile(bundleFileName + ".part", "w") as archive:
                        archive.write(assetFileName, os.path.basename(assetFileName))
                        archive.writestr(
                            sha256asset + "-meta-content.json", json.dumps(content_meta)
                        )
                        archive.writestr(
                            sha256asset + "-meta-recorder.json",
                            json.dumps(recorder_meta),
                        )

                    sha256zip = sha256sum(
                        os.path.join(stagePath, sha256asset + ".zip.part")
                    )
                    # Rename file for watcher
                    os.rename(
                        bundleFileName + ".part",
                        os.path.join(outputPath, sha256zip + ".zip"),
                    )
                    # Delete tmp file
                    os.remove(assetFileName)

                    # Rename folder to prevent re-processing
                    os.rename(
                        os.path.join(localPath, item),
                        os.path.join(localPath, "P-" + item),
                    )


# Update IDs
integrity_recorder_id.build_recorder_id_json()

while True:
    try:
        for key in config["injestors"]:
            processInjestor(key)
    except Exception as inst:
        raise inst
