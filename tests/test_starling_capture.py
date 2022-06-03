import json
from .context import validate

sc = validate.StarlingCapture()


def test_validate_create_hashes():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        sigs = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta = json.load(f)
    assert sc._validate_create_hashes(
        "tests/assets/starling-capture/good/session/asset.jpg", meta, sigs
    )


def test_validate_androidopenssl_session():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert sc._validate_androidopenssl(meta_raw, signatures[0]) == True


def test_validate_bad_androidopenssl_session():
    with open("tests/assets/starling-capture/bad/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert sc._validate_androidopenssl(meta_raw, signatures[0]) == False


def test_validate_androidopenssl_no_session():
    with open("tests/assets/starling-capture/good/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert sc._validate_androidopenssl(meta_raw, signatures[0]) == True


def test_validate_bad_androidopenssl_no_session():
    with open("tests/assets/starling-capture/bad/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert sc._validate_androidopenssl(meta_raw, signatures[0]) == False


def test_validate_zion_session():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert sc._validate_zion(meta_raw, signatures[1]) == True


def test_validate_bad_zion_session():
    with open("tests/assets/starling-capture/bad/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert sc._validate_zion(meta_raw, signatures[1]) == False


def test_validate_zion_no_session():
    with open("tests/assets/starling-capture/good/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert sc._validate_zion(meta_raw, signatures[1]) == True


def test_validate_bad_zion_no_session():
    with open("tests/assets/starling-capture/bad/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert sc._validate_zion(meta_raw, signatures[1]) == False
