from .context import verify


def test_good_sig():
    assert (
        verify.Sig66().verify(
            "tests/assets/sig66/0V8A0017.JPG", "tests/assets/sig66/pubkey.pem"
        )
        == True
    )


def test_bad_sig():
    assert (
        verify.Sig66().verify(
            "tests/assets/sig66/BAD_0V8A0017.JPG", "tests/assets/sig66/pubkey.pem"
        )
        == False
    )
