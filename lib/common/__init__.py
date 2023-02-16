import copy
import os
import json
import csv
from zipfile import ZipFile
import datetime
import hashlib
import logging
import integrity_recorder_id
from warcio.archiveiterator import ArchiveIterator

import sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../")
import validate
import integrity_recorder_id

integrity_recorder_id.build_recorder_id_json()

from  .metadata import Metadata

__all__ = [
    "Metadata"
]

metdata_file_timestamp = 0

# Dearmored keys go here
# Should be absolute path
TMP_DIR = "/tmp/integrity-preprocessor/common"

os.makedirs(TMP_DIR, exist_ok=True)

logging.basicConfig(
    filename=None,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def add_to_pipeline(source_file, content_meta, recorder_meta, stage_path, output_path):

    # Generate SHA and rename asset
    sha256asset = sha256sum(source_file)
    ext = os.path.splitext(source_file)[1]

    # Generate Bundle
    bundleFileName = os.path.join(stage_path, sha256asset + ".zip")
    with ZipFile(bundleFileName + ".part", "w") as archive:
        archive.write(source_file, sha256asset + ext)
        content_meta_data = {"contentMetadata": content_meta}
        archive.writestr(
            sha256asset + "-meta-content.json", json.dumps(content_meta_data,ensure_ascii=False)
        )
        archive.writestr(
            sha256asset + "-meta-recorder.json",
            json.dumps(recorder_meta),
        )

    sha256zip = sha256sum(os.path.join(stage_path, sha256asset + ".zip.part"))
    # Rename file for watcher
    os.rename(
        bundleFileName + ".part",
        os.path.join(output_path, sha256zip + ".zip"),
    )
    return os.path.join(output_path, sha256zip + ".zip")


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
                logging.info("Recorder Metadata Change Detected")
                metdata_file_timestamp = current_metadata_file_timestamp
    return recorder_meta_all


def sha256sum(filename):
    hasher = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(32 * 1024), b""):
            hasher.update(byte_block)
        return hasher.hexdigest()

def parse_wacz_data_extra(wacz_path):
    md = Metadata()
    md.process_wacz(wacz_path)
    return md.get_content()["extras"]["wacz"]
