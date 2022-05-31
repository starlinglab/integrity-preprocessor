from .context import verify


def test_anon_sig():
    assert verify.Wacz().verify("tests/assets/wacz/anon-sig.wacz") == True


def test_get_public_key():
    assert (
        verify.Wacz().get_public_key("tests/assets/wacz/anon-sig.wacz")
        == "MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEdyJB4zGpvCzhNblldx8b12sz+ECGk8Ryq4y+bg9woRu3OSKWO2uS+n8CD258iVvg0hP0JRg4C7YxGc7lqGsI9bHj0NaC9b4NXazeuR80iVCg96oTYIOLdWcII9rfaFMU"
    )


def test_domain_sig():
    assert verify.Wacz().verify("tests/assets/wacz/domain-sig.wacz") == True
