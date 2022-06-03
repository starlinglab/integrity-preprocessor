from .context import validate


def test_good_sig():
    assert (
        validate.Sig66().validate(
            "tests/assets/sig66/0V8A0017.JPG", "tests/assets/sig66/pubkey.pem"
        )
        == True
    )


def test_bad_sig():
    assert (
        validate.Sig66().validate(
            "tests/assets/sig66/BAD_0V8A0017.JPG", "tests/assets/sig66/pubkey.pem"
        )
        == False
    )
