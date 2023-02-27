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
import fotoware

DEBUG = os.environ.get("HTTP_DEBUG") == "1"

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import validate

if not DEBUG:
    import integrity_recorder_id

sha256sum = validate.sha256sum

if not DEBUG:
    integrity_recorder_id.build_recorder_id_json()

dotenv.load_dotenv()

JWT_SECRET = os.environ["JWT_SECRET"]
LOCAL_PATH = os.environ["LOCAL_PATH"]
OUTPUT_PATH = os.environ["OUTPUT_PATH"]

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))

TMP_PATH = os.path.join(LOCAL_PATH, "tmp")
ARCHIVE_PATH = os.path.join(LOCAL_PATH, "archive")

os.makedirs(TMP_PATH, exist_ok=True)
os.makedirs(ARCHIVE_PATH, exist_ok=True)


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
        else:
            response["status_code"] = 500
            # Print error info for unexpected errors
            print(traceback.format_exc())


global_meta_recorder = None

app = web.Application(
    middlewares=[
        JWTMiddleware(
            JWT_SECRET,
            request_property="jwt_payload",
            algorithms="HS256",
            whitelist=[r"/v1/fotoware*"],
        )
    ]
)
app.add_routes([web.post("/v1/fotoware/ingestedasset", fotoware.fotoware_ingested)])
app.add_routes([web.post("/v1/fotoware/reprocessasset", fotoware.fotoware_reprocess)])
app.add_routes([web.post("/v1/fotoware/finalizeasset", fotoware.fotoware_finalize)])
app.add_routes([web.post("/v1/fotoware/modifiedasset", fotoware.fotoware_modified)])
app.add_routes([web.post("/v1/fotoware/deletedasset", fotoware.fotoware_deleted)])
app.add_routes([web.post("/v1/fotoware/uploadedasset", fotoware.fotoware_uploaded)])

if __name__ == "__main__":
    web.run_app(app, host=HOST, port=PORT)
