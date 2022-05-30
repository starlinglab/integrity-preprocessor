# WACZ files are web archives (WARC) with metadata
# That metadata can include signatures, see the spec on this here:
# https://github.com/webrecorder/specs/blob/main/wacz-auth/spec.md
#
# This file uses a remote authsign server to verify domain-name identity + timestamp
# sigs, and manually verifies anonymous signatures in this file.

import base64
import json
from zipfile import ZipFile

import requests
from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS


class Wacz:
    def __init__(self, verify_url: str) -> None:
        """

        verify_url is a URL pointing to the authsign /verify endpoint.
        It is not needed to verify locally-signed WACZs.
        """

        self.verify_url = verify_url

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
            bool indicating if signature verified or not
        """

        with ZipFile(wacz_path, "r") as wacz:
            digest = json.loads(wacz.read("datapackage-digest.json"))
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
                except ValueError as e:
                    return False
            else:
                # Assume it's a domain signature
                r = requests.post(self.verify_url, json=digest["signedData"])
                if r.status_code == 200:
                    return True
                elif r.status_code == 400:
                    return False
                # Unexpected status code
                r.raise_for_status()
