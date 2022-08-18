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
    sc = sc_from_dir(
        "official-examples/1.9.2/c960348e388050e9d9f6b806b572dae4385456cecfd4b72af9d2523cdc768c37"
    )
    assert sc.validate()
    sc = sc_from_dir(
        "bad/1.8.0/034305235db1ac3fcd6580765f893c53e3aea07e7f2c3096600cb533ac92e94f"
    )
    assert not sc.validate()


def test_zion_classic():
    sc = sc_from_dir(
        "official-examples/1.8.0/b61f3e4bcfa1dd383fa93f7a47907b2d1ea4b2172ee1d74bceee313710b98d53"
    )
    assert sc.validate()
    sc = sc_from_dir(
        "bad/1.8.0/b61f3e4bcfa1dd383fa93f7a47907b2d1ea4b2172ee1d74bceee313710b98d53"
    )
    assert not sc.validate()


def test_zion_session_classic():
    sc = sc_from_dir(
        "official-examples/1.8.0/d7a07fafcbafceb5d626d673f0aabdb4db9d4ce6058f4e9859380831e556aa5a"
    )
    assert sc.validate()
    sc = sc_from_dir(
        "bad/1.8.0/d7a07fafcbafceb5d626d673f0aabdb4db9d4ce6058f4e9859380831e556aa5a"
    )
    assert not sc.validate()


def test_zion():
    sc = sc_from_dir(
        "official-examples/1.9.2/6ddbba58d8f907bb10da37d9053cf18b52d239e5c8a8105fbba576215b26e85b"
    )
    assert sc.validate()
    sc = sc_from_dir(
        "bad/1.9.2/6ddbba58d8f907bb10da37d9053cf18b52d239e5c8a8105fbba576215b26e85b"
    )
    assert not sc.validate()


def test_zion_session():
    sc = sc_from_dir(
        "official-examples/1.9.2/7e96c9fe16f96540de449a422852138d723c9ae80269fe4ae0e802323bf6ac7d"
    )
    assert sc.validate()
    sc = sc_from_dir(
        "bad/1.9.2/7e96c9fe16f96540de449a422852138d723c9ae80269fe4ae0e802323bf6ac7d"
    )
    assert not sc.validate()


def test_validated_sigs_json():
    sc = sc_from_dir(
        "official-examples/1.9.2/7e96c9fe16f96540de449a422852138d723c9ae80269fe4ae0e802323bf6ac7d"
    )
    assert sc.validate()
    assert sc.validated_sigs_json() == [
        {
            "provider": "starling-capture",
            "algorithm": "starling-capture-androidopenssl",
            "signature": "3045022100ba4eafa98acaf842d6958a62ca7a63b49fd54526f5b143bb55216948a5898136022007961f817810f0430e3d14352a18dff83be187036f16c113b811afb9ae9ce32e",
            "publicKey": "3059301306072a8648ce3d020106082a8648ce3d0301070342000445b7b92750636fbfbe13ea29859f1f2d9e31a56fb831fd965fda76b8eae09dba5964a449851915144d66eaee23d6242ad5cef18defd9bdad0d23cfb1f2aff0dd",
            "authenticatedMessage": "ffc5a2b7dcbfba83182a589176822604971375d9ac551a2da7fe2b2b7f317ea2",
            "authenticatedMessageDescription": "SHA256 hash of meta.json",
        },
        {
            "provider": "starling-capture",
            "algorithm": "starling-capture-zion-session",
            "signature": "3046022100fb8b03679c9c7a0f744d0effc8e9f1c14bacd03f89c3ec584aafa8677588bba7022100d080cd5e9a6bfab798fdc6f16b9a1f17c6f5715eaf8f7f5101dca43483fa4d8d",
            "publicKey": "Session:\n3059301306072a8648ce3d020106082a8648ce3d03010703420004d2c12031633a45ae1871909f129345312ea99aa9c38e865a73bc3016e8d0dad4662fe0cdb41e4e3ea1e6bb63f8ac7bf343c18db9c3b298673421888e2c43dc03\n\nSessionSignature:\n50306e825c5a439f7a0fa5f4f4ff37a4cbc452694ba13296569039099d8b619a20632a47000a898b87fc4bf2fe41d78aac9d515c3409570751c620ac3d8a58111c\n\nReceive:\n03aced43f9dddc120291f5cdf73580fbb592b5b21054ce61eb73cbaf98efcbe82e\n\nSend:\n03aced43f9dddc120291f5cdf73580fbb592b5b21054ce61eb73cbaf98efcbe82e",
            "authenticatedMessage": "ffc5a2b7dcbfba83182a589176822604971375d9ac551a2da7fe2b2b7f317ea2",
            "authenticatedMessageDescription": "SHA256 hash of meta.json",
        },
    ]
