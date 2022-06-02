# This module was extracted from integrity-backend.
# This specific file was based on handlers.py:
# https://github.com/starlinglab/integrity-backend/blob/cd6554f0b4685973382f25305a5d4f90ef942d58/integritybackend/handlers.py
# And multipart.py:
# https://github.com/starlinglab/integrity-backend/blob/cd6554f0b4685973382f25305a5d4f90ef942d58/integritybackend/multipart.py

import os
import shutil
import sys
from contextlib import contextmanager
import traceback
import zipfile
from datetime import datetime, timezone
import base64
import json
import time

from aiohttp import web
from aiohttp_jwt import JWTMiddleware
import dotenv

DEBUG = os.environ.get("HTTP_DEBUG") == "1"

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import verify

if not DEBUG:
    import integrity_recorder_id

sha256sum = verify.sha256sum
sc = verify.StarlingCapture()

if not DEBUG:
    integrity_recorder_id.build_recorder_id_json()

dotenv.load_dotenv()

JWT_SECRET = os.environ.get("JWT_SECRET")
LOCAL_PATH = os.environ.get("LOCAL_PATH")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH")

TMP_PATH = os.path.join(LOCAL_PATH, "tmp")
ARCHIVE_PATH = os.path.join(LOCAL_PATH, "archive")

os.makedirs(TMP_PATH, exist_ok=True)
os.makedirs(ARCHIVE_PATH, exist_ok=True)


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
        print(traceback.format_exc())
        response["error"] = f"{err}"
        response["status"] = "error"
        if type(err) == ValueError:
            response["status_code"] = 400
        else:
            response["status_code"] = 500


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
        "contentMetadata": {
            "name": "Authenticated content",
            "description": "Content captured with Starling Capture application",
            "author": jwt.get("author"),
            "extras": {},
            "private": {
                "providerToken": jwt,
            },
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
            meta_content["contentMetadata"]["mime"] = multipart_data["meta"]["proof"][
                "mimeType"
            ]
            meta_content["contentMetadata"]["dateCreated"] = (
                datetime.fromtimestamp(
                    multipart_data["meta"]["proof"]["timestamp"] / 1000,
                    timezone.utc,
                )
                .replace(tzinfo=None)
                .isoformat()
                + "Z"
            )
            meta_content["contentMetadata"]["private"][
                "meta"
            ] = base64.standard_b64encode(multipart_data["meta_raw"].encode()).decode()
        elif part.name == "signature":
            multipart_data["signature"] = await part.json()
            meta_content["contentMetadata"]["private"]["signature"] = multipart_data[
                "signature"
            ]
        elif part.name == "caption":
            meta_content["contentMetadata"]["extras"]["caption"] = await part.text()
        elif part.name == "target_provider":
            meta_content["contentMetadata"]["private"][
                "targetProvider"
            ] = await part.text()
        elif part.name == "tag":
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
            print("Ignoring multipart part %s", part.name)

    return multipart_data, meta_content, meta_recorder


async def write_file(part):
    # Write file in temporary directory, named after epoch in milliseconds
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


async def create(request):
    with error_handling_and_response() as response:
        jwt = request["jwt_payload"]
        if not jwt.get("collection_id") or not jwt.get("organization_id"):
            raise ValueError("JWT is missing collection or organization ID")

        # Extract data from post and create metadata files
        data, meta_content, meta_recorder = await data_from_multipart(request)
        meta = data["meta"]
        meta_raw = data["meta_raw"]
        sigs = data["signature"]
        asset_path = data["asset_fullpath"]

        # Verify the data
        if not sc._verify_create_hashes(asset_path, meta, sigs):
            raise Exception("Hashes did not match actual asset hash")
        if not sc._verify_all_sigs(meta_raw, sigs):
            raise Exception("Not all signatures verified")

        asset_hash = sha256sum(asset_path)
        tmp_zip_path = os.path.join(LOCAL_PATH, asset_hash) + ".zip"

        # Create zip
        with zipfile.ZipFile(tmp_zip_path, "w") as zipf:
            zipf.writestr(f"{asset_hash}-meta-content.json", json.dumps(meta_content))
            zipf.writestr(f"{asset_hash}-meta-recorder.json", json.dumps(meta_recorder))
            zipf.write(asset_path, asset_hash + os.path.splitext(asset_path)[1])

        # Move zip to input dir, named as the hash of itself
        final_dir = os.path.join(
            OUTPUT_PATH,
            jwt["organization_id"],
            jwt["collection_id"],
        )
        if DEBUG:
            os.makedirs(final_dir, exist_ok=True)
        shutil.copy2(
            tmp_zip_path,
            os.path.join(
                final_dir,
                sha256sum(tmp_zip_path),
            )
            + ".zip",
        )

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

if __name__ == "__main__":
    web.run_app(app)
