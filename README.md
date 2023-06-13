# Integrity Preprocessors

The Intergrity Preprocessors are a set of tools that prepare assets for injestion by integrity-backend. The preprocessor also records hashes of running programs and generates data that will be used in the meta-recorder metadata content.

## Browsertrix

This service waits for completed web crawls from a [browsertrix webrecorder instance](https://github.com/webrecorder/browsertrix-crawler) in pre-defined Browsertrix archive directories, downloads the files from Browsertrix, and prepeares a bundle for the [integrity-backend](https://github.com/starlinglab/integrity-backend), where a wacz/warc processor is used to extract metadata about the file that can be used later for the authentication and preservation.

## Folder

This servce watches a specific set of folders for new files, then prepares the integrity-backend bundle. It can be configued to process any type of file extension, or configured from a pre-defined list of extensions. It also has the capability to process metadata from files coming from proofmode or .wacz files.

This preprocessor is used for dropbox sync services.

If using rclone for syncing, to upload directory structue us
```
cd /root/rclone
docker-compose exec rclone /bin/bash
rclone copy /data/sync/shared-input dropbox:$DROPBOX_PATH_INPUT --create-empty-src-dirs --min-size 5000G
exit
```

## Chat-bot

The chat-bot service is a series of bots that interact with chat protocols. They relay on differnt chat bot applications to prepare the data for injestion.

Currently the 3 bots that are supported are

Archive Slack Bot - Sits in a slack workspace, and listens to rooms it is invited to creating an hourly log of transactions

Archive Telegram Bot - Sits in one or many telegram channels and rooms logging all transactions

Signal Chat Bot - Used to injest file on 1:1 chats from users using Signal 

