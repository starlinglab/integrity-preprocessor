# This module was extracted from integrity-backend.
# This specific file was based on handlers.py:
# https://github.com/starlinglab/integrity-backend/blob/cd6554f0b4685973382f25305a5d4f90ef942d58/integritybackend/handlers.py
# And multipart.py:
# https://github.com/starlinglab/integrity-backend/blob/cd6554f0b4685973382f25305a5d4f90ef942d58/integritybackend/multipart.py

import os
import sys
from contextlib import contextmanager
import traceback
from datetime import datetime, timezone
import base64
import json
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import common
import validate


from aiohttp import web
from aiohttp_jwt import JWTMiddleware
import dotenv

import integrity_recorder_id

logging = common.logging
sha256sum = validate.sha256sum


DEBUG = os.environ.get("HTTP_DEBUG") == "1"

dotenv.load_dotenv()

JWT_SECRET = os.environ["JWT_SECRET"]
LOCAL_PATH = os.environ["LOCAL_PATH"]
OUTPUT_PATH = os.environ["OUTPUT_PATH"]
KEYS_FILE = os.environ.get("KEYS_FILE")

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))

TMP_PATH = os.path.join(LOCAL_PATH, "tmp")
ARCHIVE_PATH = os.path.join(LOCAL_PATH, "archive")


KEYS = []


def setup():
    os.makedirs(TMP_PATH, exist_ok=True)
    os.makedirs(ARCHIVE_PATH, exist_ok=True)

    if KEYS_FILE:
        with open(KEYS_FILE, "r") as f:
            for line in f.readlines():
                line = line.strip()
                if line == "" or line.startswith("#"):
                    continue
                if len(line) == 66 and line[:2] in ["02", "03"]:
                    KEYS.append(line)
                else:
                    raise Exception(f"Line is KEYS_FILE is not valid: {line}")


class ClientError(Exception):
    # Raised to trigger status code 400 responses
    pass


@contextmanager
def error_handling_and_response():
    """Context manager to wrap the core of a handler implementation with error handlers.
    Yields:
        response: dict containing a status and any errors encountered
    """
    response = {"status": "ok", "status_code": 200}
    try:
        yield response
    except Exception as err:
        response["error"] = f"{err}"
        response["status"] = "error"
        if isinstance(err, ClientError):
            response["status_code"] = 400
            if DEBUG:
                logging.info(f"Status 400: {err}")
        else:
            response["status_code"] = 500
            # Print error info for unexpected errors
            logging.info(traceback.format_exc())


global_meta_recorder = None


def get_meta_recorder() -> dict:
    global global_meta_recorder

    if DEBUG:
        return {}

    if global_meta_recorder is not None:
        return global_meta_recorder

    with open(integrity_recorder_id.INTEGRITY_PREPROCESSOR_TARGET_PATH, "r") as f:
        global_meta_recorder = json.load(f)

    # Alter to match:
    # https://github.com/starlinglab/integrity-schema/blob/c9248b63f2e6235d4cfe6592c29a171932050110/integrity-backend/input-starling-capture-examples/3e11cc57daf3bad8375935cad4878123acc8d769551ff90f1b1bb0dc597-meta-recorder.json
    # Just add external values dict

    service = next(
        (
            s
            for s in global_meta_recorder["recorderMetadata"]
            if s["service"] == "integrity-backend"
        ),
        None,
    )
    if service is None:
        global_meta_recorder = None
        raise Exception("No recorder metadata found for integrity-backend")

    service["info"].append(
        {
            "type": "external",
            "values": {"name": ""},
        }
    )
    return global_meta_recorder


async def data_from_multipart(request):
    jwt = request.get("jwt_payload")

    multipart_data = {}

    # https://github.com/starlinglab/integrity-schema/blob/076fb516b3389cc536e8c21eef2e4df804adb3f5/integrity-backend/input-starling-capture-examples/3e11cc57daf3bad8375935cad4878123acc8d769551ff90f1b1bb0dc597-meta-content.json
    meta_content = {
        "name": "Authenticated content",
        "description": "Content captured with Starling Capture application",
        "author": jwt.get("author"),
        "extras": {},
        "private": {
            "providerToken": jwt,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    meta_recorder = get_meta_recorder()
    meta_recorder["timestamp"] = datetime.utcnow().isoformat() + "Z"

    reader = await request.multipart()
    part = None
    while True:
        part = await reader.next()
        if part is None:
            # No more parts, we're done reading.
            break
        if part.name == "file":
            multipart_data["asset_fullpath"] = await write_file(part)
        elif part.name == "meta":
            multipart_data["meta_raw"] = await part.text()
            multipart_data["meta"] = json.loads(multipart_data["meta_raw"])
            meta_content["mime"] = multipart_data["meta"]["proof"]["mimeType"]
            meta_content["dateCreated"] = (
                datetime.fromtimestamp(
                    multipart_data["meta"]["proof"]["timestamp"] / 1000,
                    timezone.utc,
                )
                .replace(tzinfo=None)
                .isoformat()
                + "Z"
            )
            meta_content["private"][
                "b64AuthenticatedMetadata"
            ] = base64.standard_b64encode(multipart_data["meta_raw"].encode()).decode()
        elif part.name == "signature":
            multipart_data["signature"] = await part.json()
            meta_content["private"]["signatures"] = multipart_data["signature"]
        elif part.name == "caption":
            meta_content["extras"]["caption"] = await part.text()
        elif part.name == "target_provider":
            meta_content["private"]["targetProvider"] = await part.text()
        elif part.name == "tag":
            if DEBUG:
                # No meta_recorder data available
                continue
            service = next(
                (
                    s
                    for s in meta_recorder["recorderMetadata"]
                    if s["service"] == "integrity-backend"
                ),
            )
            info = next((i for i in service["info"] if i["type"] == "external"))
            info["values"]["name"] = await part.text()
        else:
            logging.info("Ignoring multipart part %s", part.name)

    return multipart_data, meta_content, meta_recorder


async def write_file(part):
    # Write file in temporary directory, named after epoch in milliseconds
    if part.filename and "." in part.filename:
        tmp_file = (
            os.path.join(TMP_PATH, str(int(time.time() * 1000)))
            + os.path.splitext(part.filename)[1]
        )
    else:
        # No filename, assume it's a JPEG
        tmp_file = os.path.join(TMP_PATH, str(int(time.time() * 1000))) + ".jpg"

    # Mode "x" will throw an error if a file with the same name already exists.
    with open(tmp_file, "xb") as f:
        while True:
            chunk = await part.read_chunk()
            if not chunk:
                # No more chunks, done reading this part.
                break
            f.write(chunk)

    return tmp_file


# TODO: should be read from a config file
ROOT_PATH = "/mnt/integrity_store"


async def metadata_append_browsertrix(data, jwt):
    # print(jwt)

    collection = data["collection"]
    organization = data["organization"]
    crawl_id = data["crawl_id"]
    meta_data = data["meta_data"]

    TARGET_ROOT_PATH = f"{ROOT_PATH}/starling/internal/{organization}/{collection}/"
    os.makedirs(f"{TARGET_ROOT_PATH}/preprocessor_metadata", exist_ok=True)
    metaPath = TARGET_ROOT_PATH + "preprocessor_metadata"

    if not os.path.exists(metaPath):
        os.makedirs(metaPath)

    metaFilename = f"{metaPath}/{crawl_id}.json"
    text_file = open(metaFilename, "w")
    text_file.write(json.dumps(meta_data))
    text_file.close()
    logging.info(f"Writing additional metadata to {metaPath}/{crawl_id}.json")


async def metadata_append(request):
    with error_handling_and_response() as response:
        jwt = request["jwt_payload"]
        # todo add security

        data = (await request.content.read()).decode("UTF-8")
        datajson = json.loads(data)

        if datajson["preprocessor"] == "browsertrix":
            await metadata_append_browsertrix(datajson, jwt)
        else:
            raise Exception(f"Unsupported preprocessor")

        return web.json_response(response, status=response.get("status_code"))


async def create(request):
    with error_handling_and_response() as response:
        jwt = request["jwt_payload"]
        if not jwt.get("collection_id") or not jwt.get("organization_id"):
            raise ClientError("JWT is missing collection or organization ID")

        # Extract data from post and create metadata files
        data, meta_content, meta_recorder = await data_from_multipart(request)
        meta_raw = data.get("meta_raw")
        sigs = data.get("signature")
        asset_path = data.get("asset_fullpath")

        logging.info(f"create called: {asset_path}")

        # Make sure all sections actually existed in multipart
        if meta_raw is None:
            raise ClientError("No metadata uploaded")
        if sigs is None:
            raise ClientError("No signatures uploaded")
        if asset_path is None:
            raise ClientError("No asset uploaded")

        # Validate the data
        sc = validate.StarlingCapture(asset_path, meta_raw, sigs)
        if not sc.validate():
            raise ClientError("Hashes or signatures did not validate")

        # Add validatedSignatures
        meta_content["validatedSignatures"] = sc.validated_sigs_json()

        # Add device verification info if available
        if sc.zion_key and sc.zion_key in KEYS:
            for sig in meta_content["validatedSignatures"]:
                if "zion" in sig["algorithm"]:
                    # Should only be one Zion sig, so this is the one
                    sig["deviceInfo"] = "Public key is known"
                    break

        final_dir = os.path.join(
            OUTPUT_PATH,
            jwt["organization_id"],
            jwt["collection_id"],
        )

        if DEBUG:
            os.makedirs(final_dir, exist_ok=True)

        os.makedirs(f"{final_dir}/tmp/", exist_ok=True)
        os.makedirs(f"{final_dir}/input/", exist_ok=True)
        out_file = common.add_to_pipeline(
            asset_path,
            meta_content,
            meta_recorder,
            f"{final_dir}/tmp/",
            f"{final_dir}/input/",
        )
        logging.info(f"Added file to pipeline {out_file}")

    return web.json_response(response, status=response.get("status_code"))


app = web.Application(
    middlewares=[
        JWTMiddleware(
            JWT_SECRET,
            request_property="jwt_payload",
            algorithms="HS256",
        )
    ]
)
app.add_routes([web.post("/v1/assets/create", create)])
app.add_routes([web.post("/v1/assets/metadata/append", metadata_append)])

if __name__ == "__main__":
    setup()
    web.run_app(app, host=HOST, port=PORT)
