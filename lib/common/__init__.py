import copy
import sys
import os
import json
import csv
import shutil
from zipfile import ZipFile
import datetime
import subprocess
import hashlib
import logging
import integrity_recorder_id
import urllib.parse
from warcio.archiveiterator import ArchiveIterator

integrity_recorder_id.build_recorder_id_json()

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
            sha256asset + "-meta-content.json", json.dumps(content_meta_data)
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


def dearmor_gpg_key(key, out):
    """
    Write dearmored version of a PEM-encoded gpg key.

    All arguments are paths.
    """

    # --yes to allow file overwriting
    subprocess.run(["gpg", "--yes", "-o", out, "--dearmor", key], check=True)


def verify_gpg_sig(key, sig, msg):
    """
    Verify if gpg signature is correct

    All arguments are paths. The key path should be absolute.
    The key path has to be to a dearmored key, not a original key from ProofMode.

    True is returned if the signature verified, False if not.
    """

    proc = subprocess.run(
        ["gpg", "--no-default-keyring", "--keyring", key, "--verify", sig, msg],
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    # Some other unexpected return code, means an error has occured
    proc.check_returncode()


def sha256sum(filename):
    with open(filename, "rb") as f:
        bytes = f.read()  # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash


def extract_wacz_user_agent(wacz_path):
    with ZipFile(wacz_path, "r") as wacz:
        warc = next((s for s in wacz.namelist() if s.endswith(".warc.gz")), None)
        if warc is None:
            return None

        with wacz.open(warc) as warcf:
            for record in ArchiveIterator(warcf):
                if record.rec_type == "request":
                    return record.http_headers.get_header("User-Agent")
    return None


def parse_wacz_data_extra(wacz_path):
    # WACZ metadata extraction
    with ZipFile(wacz_path, "r") as wacz:
        d = json.loads(wacz.read("datapackage-digest.json"))
        extras = {}

        if "signedData" in d:
            # auth sign data
            if "domain" in d["signedData"]:
                extras["authsignSoftware"] = d["signedData"]["software"]
                extras["authsignDomain"] = d["signedData"]["domain"]
            elif "publicKey" in d["signedData"]:
                extras["localsignSoftware"] = d["signedData"]["software"]
                extras["localsignPublicKey"] = d["signedData"]["publicKey"]
                extras["localsignSignaturey"] = d["signedData"]["signature"]
            else:
                logging.warning(f"{wacz_path} WACZ missing signature")

        user_agent = extract_wacz_user_agent(wacz_path)

        d = json.loads(wacz.read("datapackage.json"))
        extras["waczVersion"] = d["wacz_version"]
        extras["software"] = d["software"]
        extras["dateCrawled"] = d["created"]
        if user_agent:
            extras["userAgentCrawled"] = user_agent

        if "title" in d:
            extras["waczTitle"] = d["title"]

        extras["pages"] = {}
        if "pages/pages.jsonl" in wacz.namelist():
            with wacz.open("pages/pages.jsonl") as jsonl_file:
                for line in jsonl_file.readlines():
                    d = json.loads(line)
                    if "url" in d:
                        extras["pages"][d["id"]] = d["url"]
        else:
            logging.info("Missing pages/pages.jsonl in archive %s", wacz_path)

        return extras


## Proof mode processing
def parse_proofmode_data(proofmode_path):
    data = ""
    result = {}
    date_create = None
    # ProofMode metadata extraction
    with ZipFile(proofmode_path, "r") as proofmode:

        public_pgp = proofmode.read("pubkey.asc").decode("utf-8")

        # In dir named after proofmode ZIP
        this_tmp_dir = os.path.join(
            TMP_DIR, os.path.basename(os.path.splitext(proofmode_path)[0])
        )
        if not os.path.exists(this_tmp_dir):
            os.mkdir(this_tmp_dir)

        dearmored_key_path = os.path.join(this_tmp_dir, "dearmored_key")
        proofmode.extract("pubkey.asc", path=this_tmp_dir)
        dearmor_gpg_key(os.path.join(this_tmp_dir, "pubkey.asc"), dearmored_key_path)

        for file in proofmode.namelist():
            if file.endswith(".asc") and file != "pubkey.asc" and file.count(".") > 1:
                # It's a signature of a metadata file, not the data (image) sig
                # Original file filename is in there, ex: proof.csv.asc
                # Verify signature
                sig_path = file
                msg_path = file[:-4]  # Remove .asc
                sig_path = proofmode.extract(sig_path, path=this_tmp_dir)
                msg_path = proofmode.extract(msg_path, path=this_tmp_dir)
                if not verify_gpg_sig(dearmored_key_path, sig_path, msg_path):
                    raise Exception(f"Signature file {file} failed to verify")

            # Extract file creation date from zip
            # and create a py datetime opject
            x = proofmode.getinfo(file).date_time
            current_date_create = datetime.datetime(
                x[0], x[1], x[2], x[3], x[4], x[5], 0
            )
            if date_create is None or current_date_create < date_create:
                date_create = current_date_create

            if os.path.splitext(file)[1] == ".json" and "batchproof" not in file:

                base_file_name = os.path.splitext(file)[0]
                base_file_name = os.path.splitext(base_file_name)[0]

                with proofmode.open(file) as f:
                    json_meta = json.load(f)

                source_filename = os.path.basename(json_meta["File Path"])
                file_hash = json_meta["File Hash SHA256"]

                result[source_filename] = json_meta

                # Verify data signature (usually JPEG)
                data_path = proofmode.extract(source_filename, path=this_tmp_dir)
                sig_path = proofmode.extract(file_hash + ".asc", path=this_tmp_dir)
                if not verify_gpg_sig(dearmored_key_path, sig_path, data_path):
                    raise Exception(
                        f"Signature for data/image file {source_filename} did not verify: {file_hash + '.asc'}"
                    )

            result["dateCreate"] = date_create.isoformat()

    shutil.rmtree(this_tmp_dir)

    return result
