# WACZ files are web archives (WARC) with metadata
# That metadata can include signatures, see the spec on this here:
# https://github.com/webrecorder/specs/blob/main/wacz-auth/spec.md
#
# This file uses a remote authsign server to verify domain-name identity + timestamp
# sigs, and manually verifies anonymous signatures in this file.

import base64
import json
from zipfile import ZipFile
import hashlib

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from authsign.verifier import Verifier


def hash_stream(hash_type, stream):
    """Hashes the stream with given hash_type hasher"""
    try:
        hasher = hashlib.new(hash_type)
    except:
        return 0, ""

    size = 0

    while True:
        buff = stream.read(32 * 1024)
        size += len(buff)
        hasher.update(buff)
        if not buff:
            break

    return size, hash_type + ":" + hasher.hexdigest()


class Wacz:
    def name(self) -> str:
        return "wacz"

    def get_public_key(self, wacz_path: str) -> str:
        """
        Get the base64-encoded DER-encoded ECDSA public key used to sign a WACZ.

        "" is returned if the provided WACZ does not have a key.
        """

        with ZipFile(wacz_path, "r") as wacz:
            return (
                json.loads(wacz.read("datapackage-digest.json"))
                .get("signedData", {})
                .get("publicKey", "")
            )

    def verify(self, wacz_path: str) -> bool:
        """
        Verifies a WACZ file

        Args:
            wacz_path: path to .wacz file

        Raises:
            Exception if WACZ is malformed or missing signature

        Returns:
            bool indicating if signature/hash verified or not
        """

        with ZipFile(wacz_path, "r") as wacz:
            digest = json.loads(wacz.read("datapackage-digest.json"))

            # Validate hash
            with wacz.open("datapackage.json", "r") as fh:
                _, hash = hash_stream("sha256", fh)
            if hash != digest["hash"] or hash != digest["signedData"]["hash"]:
                return False

            # Validate signature
            if digest["signedData"].get("publicKey"):
                # Field exists, assume this is an anonymous signature

                # Adapted from signature verification example
                # https://www.pycryptodome.org/en/latest/src/signature/dsa.html

                key = ECC.import_key(
                    base64.standard_b64decode(digest["signedData"]["publicKey"])
                )
                h = SHA256.new(digest["signedData"]["hash"].encode())
                verifier = DSS.new(key, "fips-186-3", encoding="binary")
                try:
                    verifier.verify(
                        h, base64.standard_b64decode(digest["signedData"]["signature"])
                    )
                    return True
                except ValueError:
                    return False
            else:
                # Assume it's a domain signature
                # Verify it using authsign package, this is the same as POSTing
                # to the /verify endpoint of an authsign server
                # Got code from here:
                # https://github.com/webrecorder/py-wacz/blob/3177b12e38df43dac8b9031b402d2e2e726c9fc6/wacz/validate.py#L241-L255

                verifier = Verifier()
                if verifier(digest["signedData"]):
                    return True
                else:
                    return False
