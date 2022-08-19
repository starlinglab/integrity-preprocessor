import pytest
import requests

URL = "http://127.0.0.1:58694/v1/assets/create"
# For token "test"
JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJvcmdhbml6YXRpb25faWQiOiJoeXBoYWNvb3AiLCJjb2xsZWN0aW9uX2lkIjoibXktY29sbGVjdGlvbiIsImF1dGhvciI6eyJAdHlwZSI6IlBlcnNvbiIsImlkZW50aWZpZXIiOiJodHRwczovL2h5cGhhLmNvb3AiLCJuYW1lIjoiVGVzdCBNY1Rlc3RmYWNlIn0sImNvcHlyaWdodCI6IkNvcHlyaWdodCAoQykgMjAyMiBIeXBoYSBXb3JrZXIgQ28tb3BlcmF0aXZlLiBBbGwgUmlnaHRzIFJlc2VydmVkLiJ9.NnLM8XQA1b6eg7ISnZRDoF-1OVJVjHF-MMFWqRxtMa8"

# Multipart info


@pytest.fixture
def files():
    img_hash = "7e96c9fe16f96540de449a422852138d723c9ae80269fe4ae0e802323bf6ac7d"
    asset_dir = f"tests/assets/starling-capture/official-examples/1.9.2/{img_hash}/"
    return {
        "file": ("foo.jpg", open(f"{asset_dir}{img_hash}.jpg", "rb"), "image/jpeg"),
        "meta": (
            "information.json",
            open(asset_dir + "information.json", "rb"),
            "application/json",
        ),
        "signature": (
            "signature.json",
            open(asset_dir + "signature.json", "rb"),
            "application/json",
        ),
    }


@pytest.fixture
def bad_files():
    img_hash = "7e96c9fe16f96540de449a422852138d723c9ae80269fe4ae0e802323bf6ac7d"
    asset_dir = f"tests/assets/starling-capture/bad/1.9.2/{img_hash}/"
    return {
        "file": ("foo.jpg", open(f"{asset_dir}{img_hash}.jpg", "rb"), "image/jpeg"),
        "meta": (
            "information.json",
            open(asset_dir + "information.json", "rb"),
            "application/json",
        ),
        "signature": (
            "signature.json",
            open(asset_dir + "signature.json", "rb"),
            "application/json",
        ),
    }


def test_no_jwt(files):
    r = requests.post(URL, files=files)
    assert r.status_code == 401


def test_good_post(files):
    r = requests.post(URL, headers={"Authorization": f"Bearer {JWT}"}, files=files)
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "status_code": 200}


def test_missing_sig(files):
    del files["signature"]
    r = requests.post(URL, headers={"Authorization": f"Bearer {JWT}"}, files=files)
    assert r.status_code == 400
    assert r.json() == {
        "status": "error",
        "status_code": 400,
        "error": "No signatures uploaded",
    }


def test_missing_meta(files):
    del files["meta"]
    r = requests.post(URL, headers={"Authorization": f"Bearer {JWT}"}, files=files)
    assert r.status_code == 400
    assert r.json() == {
        "status": "error",
        "status_code": 400,
        "error": "No metadata uploaded",
    }


def test_missing_asset(files):
    del files["file"]
    r = requests.post(URL, headers={"Authorization": f"Bearer {JWT}"}, files=files)
    assert r.status_code == 400
    assert r.json() == {
        "status": "error",
        "status_code": 400,
        "error": "No asset uploaded",
    }


def test_bad_sig(bad_files):
    r = requests.post(URL, headers={"Authorization": f"Bearer {JWT}"}, files=bad_files)
    assert r.status_code == 400
    assert r.json() == {
        "status": "error",
        "status_code": 400,
        "error": "Hashes or signatures did not validate",
    }
