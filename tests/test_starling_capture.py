import os
import json

from .context import validate


def sc_from_dir(dir_path: str) -> validate.StarlingCapture:
    dir_path = os.path.join("tests/assets/starling-capture", dir_path)

    asset_path = os.path.join(dir_path, os.path.basename(dir_path) + ".jpg")

    with open(os.path.join(dir_path, "information.json"), "r") as f:
        meta_raw = f.read()
    with open(os.path.join(dir_path, "signature.json"), "r") as f:
        sigs = json.load(f)

    return validate.StarlingCapture(asset_path, meta_raw, sigs)


def test_validate_androidopenssl():
    sc = sc_from_dir(
        "official-examples/1.8.0/034305235db1ac3fcd6580765f893c53e3aea07e7f2c3096600cb533ac92e94f"
    )
    assert sc.validate()


def test_validated_sigs_json():
    # TODO
    pass
