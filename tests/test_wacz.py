from .context import verify


def test_good_anon_sig():
    assert verify.Wacz().verify("tests/assets/wacz/good/anon-sig.wacz") == True


def test_bad_anon_sig():
    assert verify.Wacz().verify("tests/assets/wacz/bad/anon-sig.wacz") == False


def test_get_public_key():
    assert (
        verify.Wacz().get_public_key("tests/assets/wacz/good/anon-sig.wacz")
        == "MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEdyJB4zGpvCzhNblldx8b12sz+ECGk8Ryq4y+bg9woRu3OSKWO2uS+n8CD258iVvg0hP0JRg4C7YxGc7lqGsI9bHj0NaC9b4NXazeuR80iVCg96oTYIOLdWcII9rfaFMU"
    )


def test_good_domain_sig():
    assert verify.Wacz().verify("tests/assets/wacz/good/domain-sig.wacz") == True


def test_bad_domain_sig():
    assert verify.Wacz().verify("tests/assets/wacz/bad/domain-sig.wacz") == False
