from copy import deepcopy

import csv
import datetime
import dotenv
import io
import json
import os
import tempfile
import zipfile
from zipfile import ZipFile
import traceback

# Kludge
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import common
logging = common.logging

# Load Configurations
dotenv.load_dotenv()

CONFIG_FILE = os.environ.get("CONFIG_FILE")

with open(CONFIG_FILE) as f:
    config = json.load(f)

default_content = config["content"]
tmpFolder = "/tmp"

def start_metadata_content(ingestor, meta_chat):
    """Prepares content metadata.
    Args:
        ingestor: injestor dict elemtn for this bot
        meta_chat: meta data about chat
    Raises:
        Exception not at this time
    """

    meta_content_object = common.metadata()

    bot_type = ingestor["type"]
    bot_metadata={
        "chatbot": bot_type
    }    

    min_date=""
    max_date=""
    # Prepares bo specific metadata content
    if bot_type == "slack":
        bot_metadata["slack"] = {}
        bot_metadata["slack"]["botAccount"] = ingestor["botAccount"]
        bot_metadata["slack"]["workspace"] = ingestor["workspace"]
    if bot_type == "signal":
        bot_metadata["signal"] = {}
        if "phone" in ingestor:
            bot_metadata["signal"]["phone"] = ingestor["phone"]
    if bot_type == "telegram":
        bot_metadata["telegram"] = {}
        bot_metadata["telegram"]["botAccount"] = ingestor["botAccount"]    

    if "minDate" in meta_chat:
        meta_min_date = meta_chat["minDate"]
        meta_max_date = meta_chat["maxDate"]
        meta_channels = meta_chat["channels"]

        # Find start and end date. Prepare cosmetic description date
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
        

        meta_content_object.set_name( f"{bot_type.title()} archive on {cosmetic_date}")

        # Prepare channel list
        channel_text = ""
        if len(meta_channels) > 0:
            channel_list = ",".join(meta_channels)
            channel_text = f" of [ {channel_list} ]"

        meta_content_object.set_description(f"Archive{channel_text} by {bot_type.title()} bot starting on {cosmetic_date}{cosmetic_time}")

        bot_metadata_extras= {
            "channels": meta_channels,
            "dateRange" : {"from": min_date, "to": max_date}
        }
        meta_content_object.add_private_key({"chatbot":bot_metadata})
        meta_content_object.add_extras_key({"chatbot": bot_metadata_extras})

        meta_content_object.createdate_utcfromtimestamp(meta_date_create)

    return meta_content_object


def zip_folder(zipfile, path):
    """Creates a zip file from a folder
    Args:
        zipfile: path to zipfile location
        path: path to zip, this will also be the root of the zip
    Raises:
        Exception not at this time
    """
    # Iterate over all the files in directory
    for folderName, subfolders, filenames in os.walk(path):
        for filename in filenames:
            # create complete filepath of file in directory
            filePath = os.path.join(folderName, filename)
            # Add file to zip
            zipfile.write(filePath, os.path.basename(filePath))

# 
# folders representing Y-M-D-Hr format
def telegram_parse_events_into_folders(localpath):
    """Parses and groups event files created by telegram bot into
    folders representing Y-M-D-Hr format
    Args:
        localpath: path to telegram bot archives
    Raises:
        Exception not at this time
    """
    # Create Date/Time Diretory Structure and move files into it
    for item in os.listdir(localpath):
        if os.path.isfile(os.path.join(localpath, item)):
            fileTimeStamp = os.path.splitext(item)[0]
            fileDateTime = datetime.datetime.fromtimestamp(int(fileTimeStamp))
            currentDateTime = datetime.datetime.utcnow()
            fileTimeDelta = (
                currentDateTime - (fileDateTime + datetime.timedelta(minutes=1))
            ).total_seconds()
            if fileTimeDelta > 0:
                currentFolderDate = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H")
                dir = os.path.join(localpath, currentFolderDate)
                if not os.path.isdir(dir):
                    os.mkdir(dir, 0o660)
                os.rename(
                    os.path.join(localpath, item),
                    os.path.join(localpath, currentFolderDate, item),
                )

def slack_parse_chat_metadata(localpath, folder):
    """Parses files created by slack into content-metadata
    Args:
        localpath: path to telegram bot archives
        folder: target folder in localpath
    Raises:
        Exception not at this time
    """
    meta = {"dateCreated": "", "maxDate": -1, "minDate": -1, "channels": []}
    # Generate channels for slack
    converstaionFileName = os.path.join(localpath, folder, "conversations.json")
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
    archive_file_name = os.path.join(localpath, folder, "archive.jsonl")
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


def telegram_parse_chat_metadata(localpath, folder):
    """Parses files created by telegram into content-metadata
    Args:
        localpath: path to telegram bot archives
        folder: target folder in localpath
    Raises:
        Exception not at this time
    """
    logging.info(f"Telegram - Pasing {folder}")
    meta = {"dateCreated": "", "maxDate": -1, "minDate": -1, "channels": []}
    for archiveName in os.listdir(os.path.join(localpath, folder)):

        # Extract content to temporary folder
        with tempfile.TemporaryDirectory() as d:
            archiveZipFilePath = os.path.join(localpath, folder, archiveName)
            if os.path.splitext(archiveZipFilePath)[1] == ".zip":

                # Extract all files in zip
                with zipfile.ZipFile(archiveZipFilePath, "r") as archive:
                    archive.extractall(d)

                # Loop through json files in directory
                for archiveContentFileName in os.listdir(d):

                    # Process only JSON files
                    current_full_path = os.path.join(d, archiveContentFileName)
                    if os.path.splitext(current_full_path)[1] == ".json":
                        logging.info("Processing " + archiveContentFileName)
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

# Process ingestor
def process_ingestor(ingestor):
    """Main process loop of chatbot ingestor
    Args:
        ingestor: name of chatbot ingestor to process
    Raises:
        Exception not at this time
    """
    ingestor_config = config["ingestors"][ingestor]
    user_config = {}

    # Load userConfig if exists 
    if "userConfig" in ingestor_config:
        with open(ingestor_config["userConfig"]) as f:
            user_config = json.load(f)

    # Prepeare folders
    stage_path = os.path.join(ingestor_config["targetpath"], "tmp")
    output_path_default = os.path.join(ingestor_config["targetpath"], "input")
    output_path = output_path_default

    if not os.path.exists(stage_path):
        os.makedirs(stage_path)

    meta_bot_type = ingestor_config["type"]
    meta_channels = []
    meta_min_date = -1
    meta_max_date = -1
    meta_data = {}
    recorder_meta = {}
    # Prepare injestor specific tasks
    if ingestor_config["type"] == "telegram":
        localpath = ingestor_config["localpath"]
        telegram_parse_events_into_folders(localpath)
        recorder_meta = common.get_recorder_meta("telegram_bot")

    if ingestor_config["type"] == "slack":
        recorder_meta = common.get_recorder_meta("slack_bot")
        meta_channels = []

    if ingestor_config["type"] == "signal":
        recorder_meta = common.get_recorder_meta("signal_bot")

    # Process file mode injestor (Signal)
    if ingestor_config["method"] == "file":
        localpath = ingestor_config["localpath"]
        archived_path = localpath + "/archived"
        error_path = localpath + "/error"

        # Move to archived folder
        if not os.path.isdir(archived_path):
            os.mkdir(archived_path, 0o660)
        if not os.path.isdir(error_path):
            os.mkdir(error_path, 0o660)

        content_meta_object = start_metadata_content(ingestor_config, {})
        for item in os.listdir(localpath):
            if os.path.isfile(os.path.join(localpath, item)):
                try:

                    filesplit = os.path.splitext(item)
                    filename = filesplit[0]
                    fileext = filesplit[1]

                    # set datCreate to file date/time
                    date_file_created = os.path.getmtime(os.path.join(localpath, item))
                    content_meta_object.createdate_utcfromtimestamp(date_file_created)
                    
                    # Only look for zip files
                    if fileext == ".zip":
                        signal_metadata  = {}
                        logging.info(f"FileMode - Parsing {item}")
                        with open(localpath + "/" + filename + ".json", "r") as f:
                            signal_metadata = json.load(f)                            

                        # additional specific processing
                        logging.info(f"FileMode - Parsing {item} - Matching {signal_metadata['source']}")

                        ##TODO## Assumes signal
                        if signal_metadata["source"] in user_config:
                            user = user_config[signal_metadata["source"]]
                            output_path=user["targetpath"]
                            logging.info(f"FileMode - Parsing {item} - Matched " + user["author"]["name"])
                            content_meta_object.author(user["author"])

                        content_meta_object.add_private_element("signal", signal_metadata)

                        # Preform any specific file format processing
                        if "processing" in ingestor_config:
                            logging.info(f"FileMode - parsing {item} - processing {ingestor_config['processing']}")
                            content_meta_proofmode={}

                            if ingestor_config["processing"] == "proofmode":
                                content_meta_object.process_proofmode(
                                    localpath + "/" + filename + ".zip"
                                )

                        content_meta_object.description(content_meta_object._content["description"] + " received via Signal")

                        out_file = common.add_to_pipeline(
                            localpath + "/" + filename + ".zip",
                            content_meta_object.get_content(),
                            recorder_meta,
                            stage_path,
                            output_path
                        )
                        logging.info(f"FileMode - parsing {item} - wrote file {out_file}")
                        os.rename(
                            localpath + "/" + filename + ".zip",
                            archived_path + "/" + filename + ".zip",
                        )
                        os.rename(
                            localpath + "/" + filename + ".json",
                            archived_path + "/" + filename + ".json",
                        )
                        logging.info(f"FileMode - parsing {item} - Moved to Archive")
                # General failed exception
                except Exception as e:
                    logging.exception(e)
                    logging.error(f"FileMode - processing {item} - " + str(e))
                    os.rename(
                        localpath + "/" + filename + ".zip",
                        error_path + "/" + filename + ".zip",
                    )
                    os.rename(
                        localpath + "/" + filename + ".json",
                        error_path + "/" + filename + ".json",
                    )
                    f = open(error_path + "/" + filename + ".log", "a")
                    f.write(str(e))
                    f.write(traceback.format_exc())
                    f.close()

    # Process folder mode
    if ingestor_config["method"] == "folder":
        localpath = ingestor_config["localpath"]

        # Loop through date/time structured directories
        for item in os.listdir(localpath):
            if os.path.isdir(os.path.join(localpath, item)):
                try:    
                    # Check if already processed and define datetime value of directory
                    dirParts = item.split("-")
                    if dirParts[0] != "P" and dirParts[0] != "S" and dirParts[0] != "E":
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
                            logging.info("Failed to parse {item}")
                        # Offset datetime for 1 min to give any writing time to finish
                        folderDateTime = folderDateTime + datetime.timedelta(minutes=1)
                        currentDateTime = datetime.datetime.utcnow()
                        folderTimeDelta = (currentDateTime - folderDateTime).total_seconds()

                        # Folder time has passed, process
                        if folderTimeDelta > 0:

                            if ingestor_config["type"] == "slack":
                                logging.info(f"FolderMode - Parsing {item} ({ingestor}) Slack")
                                meta_chat = slack_parse_chat_metadata(localpath, item)
                            elif ingestor_config["type"] == "telegram":
                                logging.info(f"FolderMode - Parsing {item} ({ingestor}) Telegram")
                                meta_chat = telegram_parse_chat_metadata(localpath, item)
                            else:
                                logging.info(f"FolderMode - Skipping {item} ({ingestor}) UNKNOWN MODE")


                            # No data to deal with, skip folder
                            if meta_chat is None:
                                logging.info(f"FolderMode - Skipping {item} - meta_chat empty")
                                os.rename(
                                    os.path.join(localpath, item),
                                    os.path.join(localpath, "S-" + item),
                                )
                                continue

                            # Zip up content of directory to a temp file
                            temp_filename = os.path.join(
                                tmpFolder, ingestor + str(folderDateTime.timestamp()) + ".zip"
                            )
                            with zipfile.ZipFile(temp_filename, "w") as archive:
                                zip_folder(archive, os.path.join(localpath, item))

                            content_meta = start_metadata_content(
                                ingestor_config,
                                meta_chat
                            )

                            out_file = common.add_to_pipeline(
                                temp_filename,
                                content_meta,
                                recorder_meta,
                                stage_path,
                                output_path,
                            )
                            logging.info(f"FolderMode - Output {item} - Write file {out_file}")

                            # Rename folder to prevent re-processing
                            os.rename(
                                os.path.join(localpath, item),
                                os.path.join(localpath, "P-" + item),
                            )
                except Exception as e:
                    logging.exception(e)
                    logging.error(f"FolderMode - Processing {item} - " + str(e))
                    os.rename(
                        os.path.join(localpath, item),
                        os.path.join(localpath, "E-" + item),
                    )
                    f = open(os.path.join(localpath, "E-" + item, "/error.log"), "a")
                    f.write(str(e))
                    f.write(traceback.format_exc())
                    f.close()

# Main loop
while True:
    try:
        for ingestor in config["ingestors"]:
            process_ingestor(ingestor)
    except Exception as inst:
        raise inst
