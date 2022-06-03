from hashlib import sha256
import json

from .common import sha256sum, Validate

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_keys.datatypes import PublicKey


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
        self.meta_hash = sha256(self.meta_raw.encode()).hexdigest()
        self.sigs = sigs
        self.json = []
        self.provider = "starling-capture"

    def name() -> str:
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

        meta = json.loads(self.meta_raw)

        return self._validate_create_hashes(
            self.asset_path, meta, self.sigs
        ) and self._validate_all_sigs(self.meta_raw, self.sigs)

    def _validate_create_hashes(self) -> bool:
        """Validate asset hashes in the data sent to the create action.

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
                        "algorithm": "starling-capture-AndroidOpenSSL",
                        "signature": sig["signature"],
                        "publicKey": sig["publicKey"],
                        "authenticatedMessage": self.meta_hash,
                        "authenticatedMessageDescription": self.auth_msg_desc,
                    }
                )
            elif sig["provider"] == "Zion":
                if not self._validate_zion(self.meta_raw, sig):
                    return False
                self.json.append(
                    {
                        "provider": self.provider,
                        "algorithm": "starling-capture-Zion-session"
                        if sig["publicKey"].startswith("Session")
                        else "starling-capture-Zion",
                        "signature": sig["signature"],
                        "publicKey": sig["publicKey"],
                        "authenticatedMessage": self.meta_hash,
                        "authenticatedMessageDescription": self.auth_msg_desc,
                    }
                )
            else:
                raise NotImplementedError(f"Provider {sig['provider']} not implemented")
        return True

    def validated_sigs_json(self, short=False) -> list:
        return self._shorten(self.json) if short else self.json

    @staticmethod
    def _validate_androidopenssl(meta_raw: str, signature: dict) -> bool:
        # Adapted from signature verification example
        # https://www.pycryptodome.org/en/latest/src/signature/dsa.html

        key = ECC.import_key(bytes.fromhex(signature["publicKey"]))
        h = SHA256.new(meta_raw.encode())
        verifier = DSS.new(key, "fips-186-3", encoding="der")
        try:
            verifier.verify(h, bytes.fromhex(signature["signature"]))
            return True
        except ValueError:
            return False

    @staticmethod
    def _validate_zion(meta_raw: str, signature: dict) -> bool:
        # Content of publicKey field is generated by app
        # Source code is here: https://github.com/starlinglab/starling-capture/blob/fbf55abb205444d5f067d048ff5c5c89682f94b4/app/src/main/java/io/numbersprotocol/starlingcapture/collector/zion/ZionSessionSignatureProvider.kt#L24-L40
        # Either the publicKey field starts with "Session" and the data is signed
        # by an ecdsa session key, or it starts with "Receive" and then the data is
        # signed with an ethereum signature thing.

        if signature["publicKey"].startswith("Session"):
            # Same as _validate_androidopenssl
            key = ECC.import_key(
                bytes.fromhex(
                    # Extract key from after "Session" label
                    # 182 is the length of a hex-encoded, DER-encoded ec key
                    signature["publicKey"][
                        len("Session:\n") : len("Session:\n") + 182 + 1
                    ]
                )
            )
            h = SHA256.new(meta_raw.encode())
            verifier = DSS.new(key, "fips-186-3", encoding="der")
            try:
                verifier.verify(h, bytes.fromhex(signature["signature"]))
                return True
            except ValueError:
                return False

        elif signature["publicKey"].startswith("Receive"):
            # Ethereum signature using ethereum key
            # Result is ethereum address

            message = encode_defunct(text=meta_raw)
            # Ethereum address the signature belongs to
            addr = Account.recover_message(message, signature=signature["signature"])
            # Signer's Ethereum address
            pk = PublicKey.from_compressed_bytes(
                bytes.fromhex(signature["publicKey"][-66:])
            )
            return addr == pk.to_checksum_address()

        else:
            raise Exception(
                "Zion publicKey doesn't start with Session or Receive, unable to parse"
            )
