import json
import os
import subprocess
from zipfile import ZipFile
import shutil

from .common import Validate, read_file, sha256sum


class ProofMode(Validate):

    algorithm = "proofmode-pgp-rsa"
    auth_msg_desc = "SHA256 hash of the signed file"

    def __init__(
        self,
        zip_path: str,
        tmp_dir: str = "/tmp/integrity-preprocessor/proofmode",
        *args,
        **kwargs
    ) -> None:
        self.zip_path = zip_path
        # Use tmp dir named after this ZIP
        self.tmp_dir = os.path.join(
            tmp_dir, os.path.basename(os.path.splitext(self.zip_path)[0])
        )
        os.makedirs(self.tmp_dir, exist_ok=True)

        # JSON
        self.provider = None
        self.public_key = None
        self.files = {}

    def name(self) -> str:
        return "proofmode"

    def validate(self) -> bool:
        with ZipFile(self.zip_path, "r") as zipf:
            # Get dearmored key
            dearmored_key_path = os.path.join(self.tmp_dir, "dearmored_key")
            zipf.extract("pubkey.asc", path=self.tmp_dir)
            self._dearmor_gpg_key(
                os.path.join(self.tmp_dir, "pubkey.asc"), dearmored_key_path
            )

            self.public_key = read_file(os.path.join(self.tmp_dir, "pubkey.asc"))

            for file in zipf.namelist():
                if (
                    file.endswith(".asc")
                    and file != "pubkey.asc"
                    and file.count(".") > 1
                ):
                    # It's a signature of a metadata file, not the data (image) sig
                    # Original file filename is in there, ex: proof.csv.asc
                    # Validate signature
                    sig_path = file
                    msg_path = file[:-4]  # Remove .asc
                    sig_path = zipf.extract(sig_path, path=self.tmp_dir)
                    msg_path = zipf.extract(msg_path, path=self.tmp_dir)
                    if not self._validate_gpg_sig(
                        dearmored_key_path, sig_path, msg_path
                    ):
                        shutil.rmtree(self.tmp_dir)
                        return False
                    # It validated, add it to the data
                    self.files[os.path.basename(msg_path)] = {
                        "signature": read_file(sig_path),
                        "authenticatedMessage": sha256sum(msg_path),
                        "authenticatedMessageDescription": self.auth_msg_desc,
                    }

                if os.path.splitext(file)[1] == ".json":
                    with zipf.open(file) as proofmode:
                        metadata = json.load(proofmode)
                        file_hash = metadata["File Hash SHA256"]
                        file_name = os.path.basename(metadata["File Path"])
                        self.provider = metadata["Notes"]

                    # Validate data signature
                    data_path = zipf.extract(file_name, path=self.tmp_dir)
                    sig_path = zipf.extract(file_hash + ".asc", path=self.tmp_dir)
                    if not self._validate_gpg_sig(
                        dearmored_key_path, sig_path, data_path
                    ):
                        shutil.rmtree(self.tmp_dir)
                        return False

                    # It validated, add it to the data
                    self.files[file_name] = {
                        "signature": read_file(sig_path),
                        "authenticatedMessage": sha256sum(data_path),
                        "authenticatedMessageDescription": self.auth_msg_desc,
                    }

        shutil.rmtree(self.tmp_dir)
        return True

    def validated_sigs_json(self, short=False) -> list:
        j = [
            {
                "provider": self.provider,
                "algorithm": self.algorithm,
                "publicKey": self.public_key,
                "custom": self.files,
            }
        ]
        return self._shorten(j) if short else j

    def _dearmor_gpg_key(self, key, out):
        """
        Write dearmored version of a PEM-encoded gpg key.

        All arguments are paths.
        """

        # --yes to allow file overwriting
        subprocess.run(["gpg", "--yes", "-o", out, "--dearmor", key], check=True)

    def _validate_gpg_sig(self, key, sig, msg):
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
