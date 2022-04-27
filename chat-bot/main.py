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
    "mine": "application/zip",
    "description": "Archive collected by chat bot",
    "author": default_author,
    "dateCreated": "",
    "extras": {},
    "private": {},
    "timestamp": {},
}


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
        meta_date_create = (datetime.datetime.nowutc().isoformat() + "Z",)

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


def generate_metadata_content(
    bot_type, meta_channels, meta_min_date, meta_max_date, injestor
):

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
        meta_date_create = (datetime.datetime.nowutc().isoformat() + "Z",)

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
config = {
    "injestors": {
        "slack_archive_bot_workspace-0": {
            "type": "slack",
            "method": "folder",
            "localpath": "/mnt/store/slack_archive_bot_workspace-0",
            "targetpath": "/mnt/integrity_store/starling/internal/starling-lab-test/test-bot-archive-slack",
            "workspace": "test-environment",
            "botAccount": "Name of bot",
        },
        "telegram_archive_bot_testbot1": {
            "type": "telegram",
            "method": "folder",
            "localpath": "/mnt/store/telegram_archive_bot_testbot1/archive",
            "targetpath": "/mnt/integrity_store/starling/internal/starling-lab-test/test-bot-archive-telegram",
            "botAccount": "bot name here",
        },
        "signal_bot_testbot1": {
            "type": "signal",
            "method": "file",
            "processing": "proofmode",
            "localpath": "/mnt/store/signal_archive_bot",
            "targetpath": "/mnt/integrity_store/starling/internal/starling-lab-test/test-bot-archive-signal-proofmode",
        },
    }
}

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


def processInjestor(key):
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
        recorder_meta = getRecorderMeta("telegram_bot")

    if injestorConfig["type"] == "slack":
        recorder_meta = getRecorderMeta("slack_bot")
        meta_channels = []

    if injestorConfig["type"] == "signal":
        recorder_meta = getRecorderMeta("signal_bot")

    # Process file mode
    if injestorConfig["method"] == "file":
        localPath = injestorConfig["localpath"]
        for item in os.listdir(localPath):
            if os.path.isfile(os.path.join(localPath, item)):
                filesplit = os.path.splitext(item)
                filename = filesplit[0]
                fileext = filesplit[1]
                if fileext == ".zip":
                    with open(localPath + "/" + filename + ".json", "r") as f:
                        signal_metadata = json.load(f)
                        content_meta["private"]["signal"] = signal_metadata

                    if "processing" in injestorConfig:
                        if injestorConfig["processing"] == "proofmode":
                            content_meta["name"] = ("Authenticated image",)
                            content_meta["description"] = (
                                "Image with ProofMode metadata received via Signal",
                            )
                            content_meta["private"]["proofmode"] = parse_proofmode_data(
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
                                                        channelName = (
                                                            channelData["message"][
                                                                "chat"
                                                            ]["type"]
                                                            + " - "
                                                            + channelData["message"][
                                                                "chat"
                                                            ]["title"]
                                                        )
                                                        if (
                                                            meta_min_date == -1
                                                            or meta_min_date
                                                            > channelData["message"][
                                                                "date"
                                                            ]
                                                        ):
                                                            meta_min_date = channelData[
                                                                "message"
                                                            ]["date"]
                                                        if (
                                                            meta_max_date
                                                            < channelData["message"][
                                                                "date"
                                                            ]
                                                        ):
                                                            meta_max_date = channelData[
                                                                "message"
                                                            ]["date"]

                                                        if (
                                                            channelName
                                                            not in meta_channels
                                                        ):
                                                            meta_channels.append(
                                                                channelName
                                                            )

                    # Zip up content of directory to a temp file
                    tmpFileName = os.path.join(
                        tmpFolder, key + str(folderDateTime.timestamp()) + ".zip"
                    )
                    with zipfile.ZipFile(tmpFileName, "w") as archive:
                        zipFolder(archive, os.path.join(localPath, item))

                    content_meta = generate_metadata_content(
                        meta_bot_type,
                        meta_channels,
                        meta_min_date,
                        meta_max_date,
                        injestorConfig,
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
