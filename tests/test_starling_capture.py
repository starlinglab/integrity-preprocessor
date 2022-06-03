import json
from .context import validate


def test_validate_create_hashes():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        sigs = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta_raw = f.read()
    sc = validate.StarlingCapture(
        "tests/assets/starling-capture/good/session/asset.jpg", meta_raw, sigs
    )
    assert sc._validate_create_hashes() == True


def test_validate_androidopenssl_session():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert (
        validate.StarlingCapture._validate_androidopenssl(meta_raw, signatures[0])
        == True
    )


def test_validate_bad_androidopenssl_session():
    with open("tests/assets/starling-capture/bad/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert (
        validate.StarlingCapture._validate_androidopenssl(meta_raw, signatures[0])
        == False
    )


def test_validate_androidopenssl_no_session():
    with open("tests/assets/starling-capture/good/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert (
        validate.StarlingCapture._validate_androidopenssl(meta_raw, signatures[0])
        == True
    )


def test_validate_bad_androidopenssl_no_session():
    with open("tests/assets/starling-capture/bad/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert (
        validate.StarlingCapture._validate_androidopenssl(meta_raw, signatures[0])
        == False
    )


def test_validate_zion_session():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert validate.StarlingCapture._validate_zion(meta_raw, signatures[1]) == True


def test_validate_bad_zion_session():
    with open("tests/assets/starling-capture/bad/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert validate.StarlingCapture._validate_zion(meta_raw, signatures[1]) == False


def test_validate_zion_no_session():
    with open("tests/assets/starling-capture/good/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert validate.StarlingCapture._validate_zion(meta_raw, signatures[1]) == True


def test_validate_bad_zion_no_session():
    with open("tests/assets/starling-capture/bad/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert validate.StarlingCapture._validate_zion(meta_raw, signatures[1]) == False


def test_validated_sigs_json():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta_raw = f.read()

    sc = validate.StarlingCapture("", meta_raw, signatures)
    assert sc._validate_all_sigs() == True
    assert sc.validated_sigs_json() == [
        {
            "algorithm": "starling-capture-AndroidOpenSSL",
            "authenticatedMessage": "b20b2237c3768491244feb04dd59be0a1bcf730beb6436f775ab0419490c7299",
            "authenticatedMessageDescription": "SHA256 hash of meta.json",
            "provider": "starling-capture",
            "publicKey": "3059301306072a8648ce3d020106082a8648ce3d03010703420004dea6b33c2747d8a53fcf66404f0a46197effe42abbade6b213dd8ee86b9e0857b9f03479bf4abce6a2373e3e46642b82f0fd8f68098c5227e84615168c7638af",
            "signature": "304502210095136726e7bf83b0ad9042e859ee9ba2b7935bfc49af87100cd3d424d85caa25022079c7bbe9cef99a46e3b17eeef72c04231f91e9bc74bee54c476bcb3d86ea8d63",
        },
        {
            "algorithm": "starling-capture-Zion-session",
            "authenticatedMessage": "b20b2237c3768491244feb04dd59be0a1bcf730beb6436f775ab0419490c7299",
            "authenticatedMessageDescription": "SHA256 hash of meta.json",
            "provider": "starling-capture",
            "publicKey": "Session:\n"
            "3059301306072a8648ce3d020106082a8648ce3d03010703420004247e5b35ac7e8b54b191098fb0e1a931543a634a6cf70389e3b7946b87e4e38f190e59d38a4b6de518da84058bfaa9c35321dae0e7b19329a7b0aaa56363ec27\n"
            "\n"
            "Receive:\n"
            "02fd5c07443aa3e87dc271981dee52a8c15d74a086394f63603bb6b0836ec5f811\n"
            "\n"
            "Send:\n"
            "02fd5c07443aa3e87dc271981dee52a8c15d74a086394f63603bb6b0836ec5f811",
            "signature": "3045022100ba94892728e9b7ae7cdc47293fbb681a06e4a7de70f3acbe1880ff704cb6def5022071e7b9ec34cdd60930047d2e3e7e7cb11ced151066532b7bcee8036514a35fff",
        },
    ]
