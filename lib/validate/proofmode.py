import os
import subprocess
from zipfile import ZipFile
import csv
import shutil


class ProofMode:
    def __init__(self, tmp_dir="/tmp/integrity-preprocessor/proofmode"):
        self.tmp_dir = tmp_dir
        os.makedirs(self.tmp_dir, exist_ok=True)

    def name(self) -> str:
        return "proofmode"

    def validate(self, zip_path: str) -> bool:
        # Use tmp dir named after this ZIP
        this_tmp_dir = os.path.join(
            self.tmp_dir, os.path.basename(os.path.splitext(zip_path)[0])
        )
        if not os.path.exists(this_tmp_dir):
            os.mkdir(this_tmp_dir)

        with ZipFile(zip_path, "r") as zipf:
            # Get dearmored key
            dearmored_key_path = os.path.join(this_tmp_dir, "dearmored_key")
            zipf.extract("pubkey.asc", path=this_tmp_dir)
            self._dearmor_gpg_key(
                os.path.join(this_tmp_dir, "pubkey.asc"), dearmored_key_path
            )

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
                    sig_path = zipf.extract(sig_path, path=this_tmp_dir)
                    msg_path = zipf.extract(msg_path, path=this_tmp_dir)
                    if not self._validate_gpg_sig(
                        dearmored_key_path, sig_path, msg_path
                    ):
                        shutil.rmtree(this_tmp_dir)
                        return False

                if os.path.splitext(file)[1] == ".csv" and "batchproof.csv" not in file:
                    # It's a CSV with metadata - use it to verify the data file
                    # Data file is usually a JPEG with a non-standard name
                    csv_reader = csv.reader(
                        zipf.read(file).decode("utf-8").splitlines(), delimiter=","
                    )
                    next(csv_reader)  # Skip header row
                    row = next(csv_reader)
                    file_hash = row[0]
                    file_name = os.path.basename(row[-3])

                    # Validate data signature
                    data_path = zipf.extract(file_name, path=this_tmp_dir)
                    sig_path = zipf.extract(file_hash + ".asc", path=this_tmp_dir)
                    if not self._validate_gpg_sig(
                        dearmored_key_path, sig_path, data_path
                    ):
                        shutil.rmtree(this_tmp_dir)
                        return False

        shutil.rmtree(this_tmp_dir)
        return True

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
