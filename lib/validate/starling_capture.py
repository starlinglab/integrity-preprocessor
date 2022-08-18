# This file validates sigs from the Starling Capture android app
# https://github.com/numbersprotocol/starling-capture
#
# There are several different kinds of signatures that need to be validated
# The wiki describes them: https://github.com/numbersprotocol/starling-capture/wiki/Development#verification
#
# This code is loosely based on the upstream verification code:
# https://github.com/numbersprotocol/starling-capture/blob/1.9.2/util/verification/verification/verification.py

from hashlib import sha256
import json

from .common import sha256sum, Validate

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_keys.datatypes import PublicKey
from eth_keys.exceptions import BadSignature


class StarlingCapture(Validate):

    auth_msg_desc = "SHA256 hash of meta.json"

    def __init__(
        self, asset_path: str, meta_raw: str, sigs: dict, *args, **kwargs
    ) -> None:
        """

        Args:
            asset_path: the filesystem path to the asset file
            meta_raw: the unmodified JSON bytes from the "meta" section of the request
            sigs: parsed JSON from the "signature" section of the request
        """

        self.asset_path = asset_path
        self.meta_raw = meta_raw
        self.meta = json.loads(self.meta_raw)
        self.meta_hash_bytes = sha256(self.meta_raw.encode()).digest()
        self.meta_hash = self.meta_hash_bytes.hex()
        self.sigs = sigs
        self.json = []
        self.provider = "starling-capture"

    def name(self) -> str:
        return "starling-capture"

    def validate(self) -> bool:
        """
        Validate hashes and signatures for Starling Capture data.

        Returns:
            True if everything verified, False if not

        Raises:
            ValueError or KeyError if fields are missing
            Exception if hashes aren't all the same in the JSON
            File I/O errors if there's an issue reading the asset file
            NotImplementedError if one of the signature providers is not recognized
            Any errors raised due to signature bytes being malformed
        """

        return self._validate_create_hashes() and self._validate_all_sigs()

    def _validate_create_hashes(self) -> bool:
        """
        Validate asset hashes in the data sent to the create action.

        Returns:
            True if the hashes matched the asset, False if not

        Raises:
            ValueError or KeyError if fields are missing
            Exception if hashes aren't all the same in the JSON
            File I/O errors if there's an issue reading the asset file
        """

        data = {"meta": self.meta, "signature": self.sigs}

        # First check all hashes match

        meta_hash = data["meta"]["proof"]["hash"]
        sig_hash = data["signature"][0]["proofHash"]

        if meta_hash != sig_hash:
            raise Exception("The meta hash does not equal the first signature hash")

        if len(data["signature"]) > 1:
            # Check all hashes for each signature match
            for sig in data["signature"][1:]:
                if sig.get("proofHash") != sig_hash:
                    raise Exception("Not all proofHash fields of signatures match")

        # Now actually verify the hash
        asset_hash = sha256sum(self.asset_path)
        return sig_hash == asset_hash

    def _validate_all_sigs(self) -> bool:
        """
        Validate all signatures.

        Returns:
            True if all signatures verified, False if not

        Raises:
            NotImplementedError if one of the signature providers is not recognized
            Any errors raised due to signature bytes being malformed
        """

        for sig in self.sigs:
            if sig["provider"] == "AndroidOpenSSL":
                if not self._validate_androidopenssl(self.meta_raw, sig):
                    return False
                self.json.append(
                    {
                        "provider": self.provider,
                        "algorithm": "starling-capture-androidopenssl",
                        "signature": sig["signature"],
                        "publicKey": sig["publicKey"],
                        "authenticatedMessage": self.meta_hash,
                        "authenticatedMessageDescription": self.auth_msg_desc,
                    }
                )
            elif sig["provider"] == "Zion":
                # Four options:
                # Old app (<1.9.2): Zion classic, Zion session classic
                # New app (1.9.2): Zion, Zion session

                if len(sig["signature"]) == 130:
                    # The signature is Zion signature (not session-based)
                    # Try Zion then Zion classic and succeed if either works
                    # No way to tell them apart except by trying

                    if self._validate_zion(self.meta_hash, sig):
                        self.json.append(
                            {
                                "provider": self.provider,
                                "algorithm": "starling-capture-zion",
                                "signature": sig["signature"],
                                "publicKey": sig["publicKey"],
                                "authenticatedMessage": self.meta_hash,
                                "authenticatedMessageDescription": self.auth_msg_desc,
                            }
                        )
                    elif self._validate_zion_classic(self.meta_hash_bytes, sig):
                        self.json.append(
                            {
                                "provider": self.provider,
                                "algorithm": "starling-capture-zion-classic",
                                "signature": sig["signature"],
                                "publicKey": sig["publicKey"],
                                "authenticatedMessage": self.meta_hash,
                                "authenticatedMessageDescription": self.auth_msg_desc,
                            }
                        )
                    else:
                        return False

                elif (
                    "Session" in sig["publicKey"]
                    and "SessionSignature" not in sig["publicKey"]
                ):
                    # The signature is Zion session-based classic signature
                    if not self._validate_zion_session_classic(self.meta_raw, sig):
                        return False
                    self.json.append(
                        {
                            "provider": self.provider,
                            "algorithm": "starling-capture-zion-session-classic",
                            "signature": sig["signature"],
                            "publicKey": sig["publicKey"],
                            "authenticatedMessage": self.meta_hash,
                            "authenticatedMessageDescription": self.auth_msg_desc,
                        }
                    )

                elif (
                    "Session" in sig["publicKey"]
                    and "SessionSignature" in sig["publicKey"]
                ):
                    # The signature is Zion session-based signature
                    if not self._validate_zion_session(self.meta_raw, sig):
                        return False
                    self.json.append(
                        {
                            "provider": self.provider,
                            "algorithm": "starling-capture-zion-session",
                            "signature": sig["signature"],
                            "publicKey": sig["publicKey"],
                            "authenticatedMessage": self.meta_hash,
                            "authenticatedMessageDescription": self.auth_msg_desc,
                        }
                    )

                else:
                    raise Exception(
                        f"Unrecognized Zion signature with length {len(sig['signature'])}"
                    )

            else:
                # Not AndroidOpenSSL or Zion provider
                raise NotImplementedError(f"Provider {sig['provider']} not implemented")

        return True

    def validated_sigs_json(self, short=False) -> list:
        return self._shorten(self.json) if short else self.json

    @staticmethod
    def _verify_ecdsa_sig(msg: str, key_hex: str, sig_hex: str) -> bool:
        # Adapted from signature verification example
        # https://www.pycryptodome.org/en/latest/src/signature/dsa.html

        key = ECC.import_key(bytes.fromhex(key_hex))
        h = SHA256.new(msg.encode())
        verifier = DSS.new(key, "fips-186-3", encoding="der")
        try:
            verifier.verify(h, bytes.fromhex(sig_hex))
            return True
        except ValueError:
            return False

    @staticmethod
    def _validate_androidopenssl(meta_raw: str, signature: dict) -> bool:
        return StarlingCapture._verify_ecdsa_sig(
            meta_raw, signature["publicKey"], signature["signature"]
        )

    @staticmethod
    def _validate_zion_classic(meta_hash_bytes: bytes, signature: dict) -> bool:
        message = encode_defunct(meta_hash_bytes)
        try:
            # pylint: disable=no-value-for-parameter
            addr = Account.recover_message(
                message, signature="0x" + signature["signature"]
            )
        except BadSignature:
            return False
        # Signer's Ethereum address
        pk = PublicKey.from_compressed_bytes(
            bytes.fromhex(signature["publicKey"][-66:])
        )
        return addr == pk.to_checksum_address()

    @staticmethod
    def _validate_zion_session_classic(meta_raw: str, signature: dict) -> bool:
        # Extract key from after "Session" label
        # 182 is the length of a hex-encoded, DER-encoded EC key
        key_hex = signature["publicKey"][
            len("Session:\n") : len("Session:\n") + 182 + 1
        ]
        return StarlingCapture._verify_ecdsa_sig(
            meta_raw, key_hex, signature["signature"]
        )

    @staticmethod
    def _validate_zion(meta_hash_hex: str, signature: dict) -> bool:
        message = encode_defunct(text=meta_hash_hex)
        try:
            # pylint: disable=no-value-for-parameter
            addr = Account.recover_message(
                message, signature="0x" + signature["signature"]
            )
        except BadSignature:
            return False
        # Signer's Ethereum address
        pk = PublicKey.from_compressed_bytes(
            bytes.fromhex(signature["publicKey"][-66:])
        )
        return addr == pk.to_checksum_address()

    @staticmethod
    def _validate_zion_session(meta_raw: str, signature: dict) -> bool:
        lines = signature["publicKey"].split("\n")
        session_public_key = lines[1]
        zion_session_sig = lines[4]

        # First verify session key software signature is valid
        session_sig_valid = StarlingCapture._verify_ecdsa_sig(
            meta_raw, session_public_key, signature["signature"]
        )
        if not session_sig_valid:
            return False

        # Next verify Zion sig of session key
        # Similar to _validate_zion
        message = encode_defunct(text=sha256(session_public_key.encode()).hexdigest())
        try:
            # pylint: disable=no-value-for-parameter
            addr = Account.recover_message(message, signature="0x" + zion_session_sig)
        except BadSignature:
            return False
        # Signer's Ethereum address
        pk = PublicKey.from_compressed_bytes(
            bytes.fromhex(signature["publicKey"][-66:])
        )
        return addr == pk.to_checksum_address()
