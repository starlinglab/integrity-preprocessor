from .context import validate


def test_good_sig():
    s = validate.Sig66(
        "tests/assets/sig66/0V8A0017.JPG", "tests/assets/sig66/pubkey.pem"
    )
    assert s.validate() == True
    assert s.validated_sigs_json() == [
        {
            "algorithm": "sig66-ecdsa",
            "authenticatedMessage": "f045904c52ce337f9218c09647407a6a3211b7fc662a42bc27f8772e84a78352b1cb7774f42eff9e60cd0e163c9b554bc9223c823835b0432cda8027ea74ece2",
            "authenticatedMessageDescription": "SHA256 hash of image data concatenated "
            "with SHA256 hash of metadata",
            "provider": "sig66",
            "publicKey": "-----BEGIN PUBLIC KEY-----\n"
            "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEdT4gm5QlCj+/NCieoWZklO5d6Ss9\n"
            "mtUcIf7H6TAEYqHZdYbzwbO+gMnWI4Sgdn5duUxYko3WQLP7DXbpfMGhYw==\n"
            "-----END PUBLIC KEY-----\n",
            "signature": "MEUCIQDTrX+tL9bwXDSFpcjlVb+Lb1ZPYvNqB5WJE/8Y1U9XwwIgPXINJ4OODxKSDjjW06Tmn+YmvNWibsH9GDVt7KUr4dg=",
        }
    ]


def test_bad_sig():
    assert (
        validate.Sig66(
            "tests/assets/sig66/BAD_0V8A0017.JPG", "tests/assets/sig66/pubkey.pem"
        ).validate()
        == False
    )
