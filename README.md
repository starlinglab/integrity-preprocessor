# Integrity Preprocessors

The Intergrity Preprocessors are a set of tools that prepare assets for ingestion by [integrity-backend](https://github.com/starlinglab/integrity-backend). The preprocessor also records hashes of running programs and generates data that will be used in the meta-recorder metadata content.

## [Browsertrix](browsertrix/)

This service waits for completed web crawls from a [browsertrix webrecorder instance](https://github.com/webrecorder/browsertrix-crawler) in pre-defined Browsertrix archive directories. It then downloads the files from Browsertrix, and prepares a bundle for the integrity-backend. The  wacz/warc processor is used to extract metadata about the file and included in the content-metadata json.

## [Folder](folder/)

This service watches a specific set of folders for new files, then prepares the integrity-backend bundle. It can be configured to process any type of file extension, or configured from a pre-defined list of extensions. It also has the capability to process metadata from files coming from proofmode or .wacz files.

This preprocessor is used for dropbox sync services.

If using rclone for syncing, to upload directory structure use
```
cd /root/rclone
docker-compose exec rclone /bin/bash
rclone copy /data/sync/shared-input dropbox:$DROPBOX_PATH_INPUT --create-empty-src-dirs --min-size 5000G
exit
```

## Chat-bot

The chat-bot service is a series of bots that interact with chat protocols. They relay on different chat bot applications to prepare the data for ingestion.

Currently the 3 bots that are supported are

Archive Slack Bot - Sits in a slack workspace, and listens to rooms it is invited to creating an hourly log of transactions

Archive Telegram Bot - Sits in one or many telegram channels and rooms logging all transactions

Signal Chat Bot - Used to ingest file on 1:1 chats from users using Signal 

