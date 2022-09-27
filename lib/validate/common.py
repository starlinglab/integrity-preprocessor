import hashlib
from typing import Union


def sha256sum(filename: str) -> str:
    hasher = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(32 * 1024), b""):
            hasher.update(byte_block)
        return hasher.hexdigest()


def read_file(path: str, bin=False) -> Union[str, bytes]:
    with open(path, "rb" if bin else "r") as f:
        return f.read()


class Validate:
    """Parent class for all validators."""

    algorithm = "validate"
    auth_msg_desc = ""
    short_len = 300

    def __init__(self, *args, **kwargs) -> None:
        """Initialize with file(s) to validate and configuration."""
        pass

    def name(self) -> str:
        """Returns a lowercase, filename-safe string representing the validation method."""
        raise NotImplementedError

    def validate(self) -> bool:
        """
        Validate file(s) provided in __init__.

        The arguments for each validator are different, but the result is the same.
        True if the file hash/sig/etc. validated, False if not.
        """
        raise NotImplementedError

    def validated_sigs_json(self, short=False) -> list:
        """
        Get info about the validation for the validatedSignatures field of meta-content.json.

        This must be called after validate().

        If short is True then fields will not be longer than X chars
        """
        raise NotImplementedError

    @classmethod
    def _shorten(cls, json_input: Union[list, dict]) -> Union[list, dict]:
        if isinstance(json_input, dict):
            for k, v in json_input.items():
                if isinstance(v, str) and len(v) > cls.short_len:
                    json_input[k] = v[: cls.short_len] + "[...]"
                else:
                    cls._shorten(json_input[k])
        elif isinstance(json_input, list):
            for i, item in enumerate(json_input):
                if isinstance(item, str) and len(item) > cls.short_len:
                    json_input[i] = item[: cls.short_len] + "[...]"
                else:
                    cls._shorten(json_input[i])
        return json_input
