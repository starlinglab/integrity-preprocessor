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
from wacz.validate import Validation, OUTDATED_WACZ
from wacz.util import WACZ_VERSION

from .common import Validate


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


class Wacz(Validate):

    auth_msg_desc = "The hash of datapackage.json in the WACZ file"

    def __init__(self, wacz_path: str, *args, **kwargs) -> None:
        self.wacz_path = wacz_path
        # JSON
        self.is_domain_sig = False
        self.provider = None
        self.algorithm = None
        self.public_key = None
        self.signature = None
        self.auth_msg = None
        self.custom = None

    def name(self) -> str:
        return "wacz"

    def get_public_key(self) -> str:
        """
        Get the base64-encoded DER-encoded ECDSA public key used to sign a WACZ.

        "" is returned if the provided WACZ does not have a key.
        """

        with ZipFile(self.wacz_path, "r") as wacz:
            return (
                json.loads(wacz.read("datapackage-digest.json"))
                .get("signedData", {})
                .get("publicKey", "")
            )

    def validate(self) -> bool:
        """
        Validates a WACZ file.

        Raises:
            Exception if WACZ is malformed or missing signature

        Returns:
            bool indicating if WACZ validated or not
        """

        # First verify everything but the signature
        # Valid indexes, valid compression, etc
        # This code is adapted from:
        # https://github.com/webrecorder/py-wacz/blob/3177b12e38df43dac8b9031b402d2e2e726c9fc6/wacz/main.py#L117

        validate = Validation(self.wacz_path)
        version = validate.version
        validation_tests = []

        if version == OUTDATED_WACZ:
            return False
        elif version == WACZ_VERSION:
            validation_tests += [
                validate.check_required_contents,
                validate.frictionless_validate,
                validate.check_file_paths,
                validate.check_file_hashes,
            ]
        else:
            return False

        for func in validation_tests:
            success = func()
            if success is False:
                return False

        # All validation steps succeeded

        # Next, verify the hashes and signature
        # This is done by myself here, because the wacz package does not support
        # anonymous signatures.

        with ZipFile(self.wacz_path, "r") as wacz:
            digest = json.loads(wacz.read("datapackage-digest.json"))

            if "signedData" not in digest:
                # Unsigned WACZ, not allowed
                return False

            # Validate hash
            with wacz.open("datapackage.json", "r") as fh:
                _, hash = hash_stream("sha256", fh)
            if hash != digest["hash"] or hash != digest["signedData"]["hash"]:
                return False

            # Validate signature
            if digest["signedData"].get("publicKey"):
                # Field exists, assume this is an anonymous signature

                self.is_domain_sig = False
                self.provider = digest["signedData"]["software"]
                self.algorithm = "wacz-anonymous-ecdsa-sig"
                self.public_key = digest["signedData"]["publicKey"]
                self.signature = digest["signedData"]["signature"]
                self.auth_msg = digest["signedData"]["hash"]

                # Adapted from signature verification example
                # https://www.pycryptodome.org/en/latest/src/signature/dsa.html

                key = ECC.import_key(
                    base64.standard_b64decode(digest["signedData"]["publicKey"])
                )
                h = SHA256.new(digest["signedData"]["hash"].encode())
                verifier = DSS.new(key, "fips-186-3", encoding="der")
                try:
                    verifier.verify(
                        h, base64.standard_b64decode(digest["signedData"]["signature"])
                    )
                    return True
                except ValueError:
                    # Try interpreting sig as binary instead, this was the old way
                    verifier = DSS.new(key, "fips-186-3", encoding="binary")
                    try:
                        verifier.verify(
                            h,
                            base64.standard_b64decode(
                                digest["signedData"]["signature"]
                            ),
                        )
                        return True
                    except ValueError:
                        return False
            else:
                # Assume it's a domain signature

                self.is_domain_sig = True
                self.provider = digest["signedData"]["software"]
                self.algorithm = "wacz-domain-ecdsa-sig"
                self.custom = digest["signedData"]

                # Verify it using authsign package, this is the same as POSTing
                # to the /verify endpoint of an authsign server
                # Got code from here:
                # https://github.com/webrecorder/py-wacz/blob/3177b12e38df43dac8b9031b402d2e2e726c9fc6/wacz/validate.py#L241-L255

                verifier = Verifier()
                if verifier(digest["signedData"]):
                    return True
                else:
                    return False

    def validated_sigs_json(self, short=False) -> list:
        if self.is_domain_sig:
            j = [
                {
                    "provider": self.provider,
                    "algorithm": self.algorithm,
                    "custom": self.custom,
                }
            ]
        else:
            j = [
                {
                    "provider": self.provider,
                    "algorithm": self.algorithm,
                    "publicKey": self.public_key,
                    "signature": self.signature,
                    "authenticatedMessage": self.auth_msg,
                    "authenticatedMessageDescription": self.auth_msg_desc,
                }
            ]
        return self._shorten(j) if short else j
