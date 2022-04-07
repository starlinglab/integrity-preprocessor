import json
import os
import datetime
import zipfile
import hashlib
import tempfile

def sha256sum(filename):
    with open(filename,"rb") as f:
        bytes = f.read() # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest();
        return readable_hash
    
def zipFolder(zipfile, path):
    # Iterate over all the files in directory
        for folderName, subfolders, filenames in os.walk(path):
            for filename in filenames:
                #create complete filepath of file in directory
                filePath = os.path.join(folderName, filename)
                # Add file to zip
                zipfile.write(filePath, os.path.basename(filePath))
                
def getRecorderMeta(type):
    return recorder_meta_all


tmpFolder="/tmp"
config = {
    "injestors": {
        "slack_archive_bot_workspace-0": {
            "type": "slack",
            "method": "folder",
            "localpath" : "/mnt/store/slack_archive_bot_workspace-0",
            "targetpath": "/mnt/integrity_store/starling/internal/starling-lab-test/test-bot-archive-slack"
        },
        "telegram_archive_bot_testbot1": {
            "type": "telegram",
            "method": "folder",
            "localpath": "/mnt/store/telegram_archive_bot_testbot1/archive",
            "targetpath": "/mnt/integrity_store/starling/internal/starling-lab-test/test-bot-archive-telegram"
        }
    }
}

def processInjestor(key):
    injestorConfig = config['injestors'][key]

    stagePath=os.path.join(injestorConfig['targetpath'], "tmp")
    outputPath=os.path.join(injestorConfig['targetpath'], "input")

    if not os.path.exists(stagePath):
        os.makedirs(stagePath)

    #############################
    # TELEGRAM BOT FOLDER GROUP #
    #############################
    # Group telegram archive into folders

    if injestorConfig["type"] == "telegram":
        localPath=injestorConfig['localpath']
        for item in os.listdir(localPath):
            if os.path.isfile(os.path.join(localPath,item)):
                fileTimeStamp=os.path.splitext(item)[0]
                fileDateTime=datetime.datetime.fromtimestamp(int(fileTimeStamp))
                currentDateTime=datetime.datetime.utcnow()
                fileTimeDelta=(currentDateTime - (fileDateTime + datetime.timedelta(minutes=1))).total_seconds()
                if fileTimeDelta > 0: 
                    currentFolderDate=datetime.datetime.utcnow().strftime("%Y-%m-%d-%H")
                    dir = os.path.join(localPath,currentFolderDate)
                    if not os.path.isdir(dir):
                         os.mkdir(dir, 0o660)
                    os.rename(os.path.join(localPath,item),os.path.join(localPath,currentFolderDate,item))
        content_meta = {}
        recorder_meta = getRecorderMeta("telegram")

    if injestorConfig["type"] == "slack":
        content_meta = {}
        recorder_meta = getRecorderMeta("slack")


    if injestorConfig["method"] == "folder":
        localPath=injestorConfig['localpath']
        for item in os.listdir(localPath):
            # Process only directories
            if os.path.isdir(os.path.join(localPath,item)):

                # Check if already processed and define datetime value of directory
                dirParts = item.split("-")
                if dirParts[0] != "P":                     
                    # Calculate date/time for the folder
                    if (len(dirParts) == 3):
                        folderDateTime = datetime.datetime.strptime(item, "%Y-%m-%d") + datetime.timedelta(days=1)
                    elif (len(dirParts) == 4):
                        folderDateTime = datetime.datetime.strptime(item, "%Y-%m-%d-%H") + datetime.timedelta(hours=1)
                    else:
                        print("Failed to parse {item}" )
                    # Offset datetime for 1 min to give any writing time to finish
                    folderDateTime=folderDateTime + datetime.timedelta(minutes=1)
                    currentDateTime = datetime.datetime.utcnow()
                    folderTimeDelta=(currentDateTime - folderDateTime).total_seconds()
                    content_meta['channels']=[]
                    # Folder time has passed, process
                    if folderTimeDelta > 0:

                        print(key + " Processing Asset " + item)


                        if injestorConfig["type"] == "slack":
                            content_meta['channels']=[]
                            converstaionFileName = os.path.join(localPath,item,'conversations.json')
                            with open(converstaionFileName) as f:
                                channelData = json.load(f)
                                for chan in channelData:
                                    if channelData[chan]['is_member'] == True:
                                        content_meta['channels'].append(channelData[chan]['name'])


                        if injestorConfig["type"] == "telegram":

                            # Loop through items in archive
                            for archiveName in os.listdir(os.path.join(localPath,item)):

                                # Extract content to temporary folder
                                with tempfile.TemporaryDirectory() as d:
                                    archiveZipFilePath=os.path.join(localPath,item,archiveName)

                                    # Process only zip files
                                    if os.path.splitext(archiveZipFilePath)[1] == "zip":

                                        # Extract all files in zip
                                        with zipfile.ZipFile(archiveZipFilePath , "r") as archive:
                                            archive.extractall(d) 
                                                                                      
                                            # Loop through json files in directory
                                            for archiveContentFileName in os.listdir(d):

                                                # Process only JSON files
                                                if os.path.splittext(os.path.join(d,archiveContentFileName))[1] == "json":

                                                    with open(os.path.join(d,archiveContentFileName),"r") as archiveContentFileHandle:
                                                        channelData = json.load(archiveContentFileHandle)
                                                        channelName = channelData['message']['chat']['type'] + ' - ' + channelData['message']['chat']['title']
                                                        if channelName not in content_meta['channels']:
                                                            content_meta['channels'].append(channelName)                                                

                        # Zip up content of directory to a temp file                        
                        tmpFileName  = os.path.join(tmpFolder,key + str(folderDateTime.timestamp())  + ".zip" )
                        with zipfile.ZipFile(tmpFileName , "w") as archive:
                            zipFolder(archive,os.path.join(localPath,item))
                        
                        # Generate SHA and rename asset
                        sha256asset = sha256sum(tmpFileName)
                        assetFileName = os.path.join(tmpFolder,sha256asset + ".zip")
                        os.rename(tmpFileName, assetFileName)
                        
                        # Generate Bundle
                        bundleFileName = os.path.join(stagePath,sha256asset + ".zip")                    
                        with zipfile.ZipFile(bundleFileName + ".part", "w") as archive:                        
                            archive.write(assetFileName, os.path.basename(assetFileName))
                            archive.writestr(sha256asset + "-meta-content.json", json.dumps(content_meta))
                            archive.writestr(sha256asset + "-meta-recorder.json", json.dumps(recorder_meta))

                        sha256zip = sha256sum(os.path.join(stagePath,sha256asset + ".zip.part"))

                        # Rename file for watcher
                        os.rename(bundleFileName + ".part", os.path.join(outputPath,sha256zip + ".zip"))

                        #Delete tmp file
                        os.remove(assetFileName) 

                        #Rename folder to prevent re-processing
                        os.rename(os.path.join(localPath,item), os.path.join(localPath,"P-" + item))

                        
if os.path.exists("/root/integrity_recorder_report.json"):
    with open('/root/integrity_recorder_report.json', 'r') as f:
        recorder_meta_all = json.load(f)

while True:
    try:
        for key in config["injestors"]:
            processInjestor(key)
    except Exception as inst:
        print(inst)
