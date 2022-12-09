from .context import validate

from pprint import pprint


def test_good_anon_sig():
    w = validate.Wacz("tests/assets/wacz/good/anon-sig.wacz")
    assert w.validate() == True
    assert w.validated_sigs_json() == [
        {
            "algorithm": "ecdsa-key-sig",
            "authenticatedMessage": "sha256:aef48a18637f95a74e8537015a322b3894a88a8a54b310b2e6855d9f370b6b6c",
            "authenticatedMessageDescription": "The hash of datapackage.json in the WACZ "
            "file",
            "provider": "Webrecorder ArchiveWeb.page 0.7.9, using warcio.js 1.5.0",
            "publicKey": "MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEdyJB4zGpvCzhNblldx8b12sz+ECGk8Ryq4y+bg9woRu3OSKWO2uS+n8CD258iVvg0hP0JRg4C7YxGc7lqGsI9bHj0NaC9b4NXazeuR80iVCg96oTYIOLdWcII9rfaFMU",
            "signature": "mFeJLayQT4Si3/JO3BRDFyw0b90TUSMEOmvNwsQfV1Hwz5pMUgEweu0kx67KwFnaSpgCg7Bs2FKkKsKJgS3GIBnCL169sFX/GH44dUofoGmb25JYLQO5DtZ+KzwHQ270",
        }
    ]


def test_bad_anon_sig():
    assert validate.Wacz("tests/assets/wacz/bad/anon-sig.wacz").validate() == False


def test_get_public_key():
    assert (
        validate.Wacz("tests/assets/wacz/good/anon-sig.wacz").get_public_key()
        == "MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEdyJB4zGpvCzhNblldx8b12sz+ECGk8Ryq4y+bg9woRu3OSKWO2uS+n8CD258iVvg0hP0JRg4C7YxGc7lqGsI9bHj0NaC9b4NXazeuR80iVCg96oTYIOLdWcII9rfaFMU"
    )


def test_bad_domain_sig():
    assert validate.Wacz("tests/assets/wacz/bad/domain-sig.wacz").validate() == False


def test_good_domain_sig():
    w = validate.Wacz("tests/assets/wacz/good/domain-sig.wacz")
    assert w.validate() == True
    assert w.validated_sigs_json() == [
        {
            "algorithm": "ecdsa-certificate-sig",
            "custom": {
                "created": "2022-05-31T15:15:23Z",
                "domain": "org1.authsign.stg.starlinglab.org",
                "domainCert": "-----BEGIN CERTIFICATE-----\n"
                "MIIEfTCCA2WgAwIBAgISBGkJkRNUap78KYU6pL98qSH+MA0GCSqGSIb3DQEBCwUA\n"
                "MDIxCzAJBgNVBAYTAlVTMRYwFAYDVQQKEw1MZXQncyBFbmNyeXB0MQswCQYDVQQD\n"
                "EwJSMzAeFw0yMjA1MjkyMzUwNThaFw0yMjA4MjcyMzUwNTdaMCwxKjAoBgNVBAMT\n"
                "IW9yZzEuYXV0aHNpZ24uc3RnLnN0YXJsaW5nbGFiLm9yZzBZMBMGByqGSM49AgEG\n"
                "CCqGSM49AwEHA0IABL8HVkRxIxOXDsPtlgNdxbbo3Niyn25FA4UOMGggJ599hFN7\n"
                "9VIEABtfmQmeTC5YhZqg4WukJ/ZljQOmjplk3+ajggJcMIICWDAOBgNVHQ8BAf8E\n"
                "BAMCB4AwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMCMAwGA1UdEwEB/wQC\n"
                "MAAwHQYDVR0OBBYEFLBEcKcbjw9tO+T7sQNuV0khjDynMB8GA1UdIwQYMBaAFBQu\n"
                "sxe3WFbLrlAJQOYfr52LFMLGMFUGCCsGAQUFBwEBBEkwRzAhBggrBgEFBQcwAYYV\n"
                "aHR0cDovL3IzLm8ubGVuY3Iub3JnMCIGCCsGAQUFBzAChhZodHRwOi8vcjMuaS5s\n"
                "ZW5jci5vcmcvMCwGA1UdEQQlMCOCIW9yZzEuYXV0aHNpZ24uc3RnLnN0YXJsaW5n\n"
                "bGFiLm9yZzBMBgNVHSAERTBDMAgGBmeBDAECATA3BgsrBgEEAYLfEwEBATAoMCYG\n"
                "CCsGAQUFBwIBFhpodHRwOi8vY3BzLmxldHNlbmNyeXB0Lm9yZzCCAQQGCisGAQQB\n"
                "1nkCBAIEgfUEgfIA8AB2ACl5vvCeOTkh8FZzn2Old+W+V32cYAr4+U1dJlwlXceE\n"
                "AAABgRJx1JoAAAQDAEcwRQIgTPbDOuapG4xlFfv9uHM6Zk5saRnY/pbHl0zLcc/m\n"
                "HBYCIQCN2m8xkW1M1iPjBwQc8K0u4dG666H12NIRLSLQL8vf7AB2AEHIyrHfIkZK\n"
                "EMahOglCh15OMYsbA+vrS8do8JBilgb2AAABgRJx1NMAAAQDAEcwRQIhAIE5pB2/\n"
                "AE0Ms8qhlYaH1snhRp/G76us7XKhirPjd72BAiAtPHbdX8TwG850pZm7DUFpcFH0\n"
                "7MpsuSFjwE1PDzC8yDANBgkqhkiG9w0BAQsFAAOCAQEAAdHBB1ty1ugb3CXEO+2d\n"
                "R191LsE7YF7lP65l+U2PxgTJ9rZvId5/LIeMdHuMug22gYDHwoM8rEvD0N6vGb5a\n"
                "Zag0Wt4FZ/fQG2ZaYLzwz65k4VWzRrTwSgX2WPD6iwvCFIqDOfWIIkB6MpyP7FeS\n"
                "fUSkgLrmyOEyQpgHiTyl6RAFMkvwYwGoTVIF8rAO6wLjPv4zTHSFUIlh3F8D1Ono\n"
                "r+5mzaQ/8D0YCOk2iYpflxFYxYWRtjSu6QfLSoIm6J8EpAKBU6YJXERnYkRvWCS3\n"
                "8ZL9LhjQgYvDYqPVaRz9J8DCZ4cxdj2iuCTbsc4Ana760bDsmFixN9mXWEg6of/r\n"
                "SA==\n"
                "-----END CERTIFICATE-----\n"
                "\n"
                "-----BEGIN CERTIFICATE-----\n"
                "MIIFFjCCAv6gAwIBAgIRAJErCErPDBinU/bWLiWnX1owDQYJKoZIhvcNAQELBQAw\n"
                "TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh\n"
                "cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMjAwOTA0MDAwMDAw\n"
                "WhcNMjUwOTE1MTYwMDAwWjAyMQswCQYDVQQGEwJVUzEWMBQGA1UEChMNTGV0J3Mg\n"
                "RW5jcnlwdDELMAkGA1UEAxMCUjMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK\n"
                "AoIBAQC7AhUozPaglNMPEuyNVZLD+ILxmaZ6QoinXSaqtSu5xUyxr45r+XXIo9cP\n"
                "R5QUVTVXjJ6oojkZ9YI8QqlObvU7wy7bjcCwXPNZOOftz2nwWgsbvsCUJCWH+jdx\n"
                "sxPnHKzhm+/b5DtFUkWWqcFTzjTIUu61ru2P3mBw4qVUq7ZtDpelQDRrK9O8Zutm\n"
                "NHz6a4uPVymZ+DAXXbpyb/uBxa3Shlg9F8fnCbvxK/eG3MHacV3URuPMrSXBiLxg\n"
                "Z3Vms/EY96Jc5lP/Ooi2R6X/ExjqmAl3P51T+c8B5fWmcBcUr2Ok/5mzk53cU6cG\n"
                "/kiFHaFpriV1uxPMUgP17VGhi9sVAgMBAAGjggEIMIIBBDAOBgNVHQ8BAf8EBAMC\n"
                "AYYwHQYDVR0lBBYwFAYIKwYBBQUHAwIGCCsGAQUFBwMBMBIGA1UdEwEB/wQIMAYB\n"
                "Af8CAQAwHQYDVR0OBBYEFBQusxe3WFbLrlAJQOYfr52LFMLGMB8GA1UdIwQYMBaA\n"
                "FHm0WeZ7tuXkAXOACIjIGlj26ZtuMDIGCCsGAQUFBwEBBCYwJDAiBggrBgEFBQcw\n"
                "AoYWaHR0cDovL3gxLmkubGVuY3Iub3JnLzAnBgNVHR8EIDAeMBygGqAYhhZodHRw\n"
                "Oi8veDEuYy5sZW5jci5vcmcvMCIGA1UdIAQbMBkwCAYGZ4EMAQIBMA0GCysGAQQB\n"
                "gt8TAQEBMA0GCSqGSIb3DQEBCwUAA4ICAQCFyk5HPqP3hUSFvNVneLKYY611TR6W\n"
                "PTNlclQtgaDqw+34IL9fzLdwALduO/ZelN7kIJ+m74uyA+eitRY8kc607TkC53wl\n"
                "ikfmZW4/RvTZ8M6UK+5UzhK8jCdLuMGYL6KvzXGRSgi3yLgjewQtCPkIVz6D2QQz\n"
                "CkcheAmCJ8MqyJu5zlzyZMjAvnnAT45tRAxekrsu94sQ4egdRCnbWSDtY7kh+BIm\n"
                "lJNXoB1lBMEKIq4QDUOXoRgffuDghje1WrG9ML+Hbisq/yFOGwXD9RiX8F6sw6W4\n"
                "avAuvDszue5L3sz85K+EC4Y/wFVDNvZo4TYXao6Z0f+lQKc0t8DQYzk1OXVu8rp2\n"
                "yJMC6alLbBfODALZvYH7n7do1AZls4I9d1P4jnkDrQoxB3UqQ9hVl3LEKQ73xF1O\n"
                "yK5GhDDX8oVfGKF5u+decIsH4YaTw7mP3GFxJSqv3+0lUFJoi5Lc5da149p90Ids\n"
                "hCExroL1+7mryIkXPeFM5TgO9r0rvZaBFOvV2z0gp35Z0+L4WPlbuEjN/lxPFin+\n"
                "HlUjr8gRsI3qfJOQFy/9rKIJR0Y/8Omwt/8oTWgy1mdeHmmjk7j1nYsvC9JSQ6Zv\n"
                "MldlTTKB3zhThV1+XWYp6rjd5JW1zbVWEkLNxE7GJThEUG3szgBVGP7pSWTUTsqX\n"
                "nLRbwHOoq7hHwg==\n"
                "-----END CERTIFICATE-----\n"
                "\n"
                "-----BEGIN CERTIFICATE-----\n"
                "MIIFYDCCBEigAwIBAgIQQAF3ITfU6UK47naqPGQKtzANBgkqhkiG9w0BAQsFADA/\n"
                "MSQwIgYDVQQKExtEaWdpdGFsIFNpZ25hdHVyZSBUcnVzdCBDby4xFzAVBgNVBAMT\n"
                "DkRTVCBSb290IENBIFgzMB4XDTIxMDEyMDE5MTQwM1oXDTI0MDkzMDE4MTQwM1ow\n"
                "TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh\n"
                "cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwggIiMA0GCSqGSIb3DQEB\n"
                "AQUAA4ICDwAwggIKAoICAQCt6CRz9BQ385ueK1coHIe+3LffOJCMbjzmV6B493XC\n"
                "ov71am72AE8o295ohmxEk7axY/0UEmu/H9LqMZshftEzPLpI9d1537O4/xLxIZpL\n"
                "wYqGcWlKZmZsj348cL+tKSIG8+TA5oCu4kuPt5l+lAOf00eXfJlII1PoOK5PCm+D\n"
                "LtFJV4yAdLbaL9A4jXsDcCEbdfIwPPqPrt3aY6vrFk/CjhFLfs8L6P+1dy70sntK\n"
                "4EwSJQxwjQMpoOFTJOwT2e4ZvxCzSow/iaNhUd6shweU9GNx7C7ib1uYgeGJXDR5\n"
                "bHbvO5BieebbpJovJsXQEOEO3tkQjhb7t/eo98flAgeYjzYIlefiN5YNNnWe+w5y\n"
                "sR2bvAP5SQXYgd0FtCrWQemsAXaVCg/Y39W9Eh81LygXbNKYwagJZHduRze6zqxZ\n"
                "Xmidf3LWicUGQSk+WT7dJvUkyRGnWqNMQB9GoZm1pzpRboY7nn1ypxIFeFntPlF4\n"
                "FQsDj43QLwWyPntKHEtzBRL8xurgUBN8Q5N0s8p0544fAQjQMNRbcTa0B7rBMDBc\n"
                "SLeCO5imfWCKoqMpgsy6vYMEG6KDA0Gh1gXxG8K28Kh8hjtGqEgqiNx2mna/H2ql\n"
                "PRmP6zjzZN7IKw0KKP/32+IVQtQi0Cdd4Xn+GOdwiK1O5tmLOsbdJ1Fu/7xk9TND\n"
                "TwIDAQABo4IBRjCCAUIwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMCAQYw\n"
                "SwYIKwYBBQUHAQEEPzA9MDsGCCsGAQUFBzAChi9odHRwOi8vYXBwcy5pZGVudHJ1\n"
                "c3QuY29tL3Jvb3RzL2RzdHJvb3RjYXgzLnA3YzAfBgNVHSMEGDAWgBTEp7Gkeyxx\n"
                "+tvhS5B1/8QVYIWJEDBUBgNVHSAETTBLMAgGBmeBDAECATA/BgsrBgEEAYLfEwEB\n"
                "ATAwMC4GCCsGAQUFBwIBFiJodHRwOi8vY3BzLnJvb3QteDEubGV0c2VuY3J5cHQu\n"
                "b3JnMDwGA1UdHwQ1MDMwMaAvoC2GK2h0dHA6Ly9jcmwuaWRlbnRydXN0LmNvbS9E\n"
                "U1RST09UQ0FYM0NSTC5jcmwwHQYDVR0OBBYEFHm0WeZ7tuXkAXOACIjIGlj26Ztu\n"
                "MA0GCSqGSIb3DQEBCwUAA4IBAQAKcwBslm7/DlLQrt2M51oGrS+o44+/yQoDFVDC\n"
                "5WxCu2+b9LRPwkSICHXM6webFGJueN7sJ7o5XPWioW5WlHAQU7G75K/QosMrAdSW\n"
                "9MUgNTP52GE24HGNtLi1qoJFlcDyqSMo59ahy2cI2qBDLKobkx/J3vWraV0T9VuG\n"
                "WCLKTVXkcGdtwlfFRjlBz4pYg1htmf5X6DYO8A4jqv2Il9DjXA6USbW1FzXSLr9O\n"
                "he8Y4IWS6wY7bCkjCWDcRQJMEhg76fsO3txE+FiYruq9RUWhiF1myv4Q6W+CyBFC\n"
                "Dfvp7OOGAN6dEOM4+qR9sdjoSYKEBpsr6GtPAQw4dy753ec5\n"
                "-----END CERTIFICATE-----\n",
                "hash": "sha256:a6d08d3709143a395bf3d5d44cb5555d720e431336e993f32504554d6f5d1b15",
                "signature": "MEQCIAdAabbAnXpPvkUqF0kSfaKgA7rHjAnBSC6fVZBEuPZXAiAdmzfBvY5fZCf6712pZYFiVbojqU1wnx4aCnFcnUFXGg==",
                "software": "authsigner 0.4.0",
                "timeSignature": "MIIFRDADAgEAMIIFOwYJKoZIhvcNAQcCoIIFLDCCBSgCAQMxDzANBglghkgBZQMEAgMFADCCAYIGCyqGSIb3DQEJEAEEoIIBcQSCAW0wggFpAgEBBgQqAwQBMC8wCwYJYIZIAWUDBAIBBCDcGzMvYh27F0Qkdnq0lk24mANTgLfnPSJsNG2Gc4scAAIEAdh3CRgPMjAyMjA1MzExNTE1MjRaAQH/oIIBEaSCAQ0wggEJMREwDwYDVQQKEwhGcmVlIFRTQTEMMAoGA1UECxMDVFNBMXYwdAYDVQQNE21UaGlzIGNlcnRpZmljYXRlIGRpZ2l0YWxseSBzaWducyBkb2N1bWVudHMgYW5kIHRpbWUgc3RhbXAgcmVxdWVzdHMgbWFkZSB1c2luZyB0aGUgZnJlZXRzYS5vcmcgb25saW5lIHNlcnZpY2VzMRgwFgYDVQQDEw93d3cuZnJlZXRzYS5vcmcxIjAgBgkqhkiG9w0BCQEWE2J1c2lsZXphc0BnbWFpbC5jb20xEjAQBgNVBAcTCVd1ZXJ6YnVyZzELMAkGA1UEBhMCREUxDzANBgNVBAgTBkJheWVybjGCA4owggOGAgEBMIGjMIGVMREwDwYDVQQKEwhGcmVlIFRTQTEQMA4GA1UECxMHUm9vdCBDQTEYMBYGA1UEAxMPd3d3LmZyZWV0c2Eub3JnMSIwIAYJKoZIhvcNAQkBFhNidXNpbGV6YXNAZ21haWwuY29tMRIwEAYDVQQHEwlXdWVyemJ1cmcxDzANBgNVBAgTBkJheWVybjELMAkGA1UEBhMCREUCCQDB6YYWDajpgjANBglghkgBZQMEAgMFAKCBuDAaBgkqhkiG9w0BCQMxDQYLKoZIhvcNAQkQAQQwHAYJKoZIhvcNAQkFMQ8XDTIyMDUzMTE1MTUyNFowKwYLKoZIhvcNAQkQAgwxHDAaMBgwFgQUkW2j2GDsyoLjS8WdF5Pn6WiHXxQwTwYJKoZIhvcNAQkEMUIEQJPpf3Oct6TUTfLjsypOhMf0svnDRqRqvSenalZR4yR43l0oL9g1mU04n3Rt5EZfN1S87Xe1rgi9ABAmZSR1cXAwDQYJKoZIhvcNAQEBBQAEggIAnLzRUogcm6Hq7o8kPA56WivwQgw+CB5wEO1R3aszax5pdeLDU2O1cpdIokQvfXeytJifnPoScr0FGiua0jip2n9QAcfG+sXRO9b5rc3FVSKI8tQe8YeTsnvCVc5h+Cq0nwk6C0mpA1DSC6M/YJY0Pt+OdP4UttsZrfvml0P9FHVgl1mFskeepMHofnOKUZwBWNRTsenYg2YeE/1Q4YqjTLGcK3QFz5JuRgO4mu2/IOlqKpXVxIZhQCEGgjauvg5xO+guGVIXMqnMzQD/lbPaAmtW0in7Ns/0/WAshT3vEDOW0XYl8u+u8m8S8vjqsrOiWteui2/+ll1tyw+SwrLivdBLPlbLuvYrXUKqCOTVv5TvTnCq998784RmgLJSBalbY3hfD1O5dOKjX+7EvCew7yPZYmJtcM36iK63VdTuzEd2EEs9xgaVvB2q1qgrE7ExN7CGnukbp8rP5gN41w76JSisdCOwtoUZ+4gaP0BmMwT4HZpua4e5MQqkaCqrl3BJRKX9UZF8YaoSVR+G7Qiq9i1YMs+GJS/ZXoucMnr5SVSzSf6Yu3Yy+ll370xg2935mMX/7dpwcSyhLTOYFW/bC5t1Txrcrz1A/bD9cGE9o2D1/rCuOgbBmzFE2pjHjHdPjxaisOnw9T2QhB/ZmJ16Xinz4RT5XeOHo7gMRwG8Kvs=",
                "timestampCert": "-----BEGIN CERTIFICATE-----\n"
                "MIIIATCCBemgAwIBAgIJAMHphhYNqOmCMA0GCSqGSIb3DQEBDQUAMIGVMREwDwYD\n"
                "VQQKEwhGcmVlIFRTQTEQMA4GA1UECxMHUm9vdCBDQTEYMBYGA1UEAxMPd3d3LmZy\n"
                "ZWV0c2Eub3JnMSIwIAYJKoZIhvcNAQkBFhNidXNpbGV6YXNAZ21haWwuY29tMRIw\n"
                "EAYDVQQHEwlXdWVyemJ1cmcxDzANBgNVBAgTBkJheWVybjELMAkGA1UEBhMCREUw\n"
                "HhcNMTYwMzEzMDE1NzM5WhcNMjYwMzExMDE1NzM5WjCCAQkxETAPBgNVBAoTCEZy\n"
                "ZWUgVFNBMQwwCgYDVQQLEwNUU0ExdjB0BgNVBA0TbVRoaXMgY2VydGlmaWNhdGUg\n"
                "ZGlnaXRhbGx5IHNpZ25zIGRvY3VtZW50cyBhbmQgdGltZSBzdGFtcCByZXF1ZXN0\n"
                "cyBtYWRlIHVzaW5nIHRoZSBmcmVldHNhLm9yZyBvbmxpbmUgc2VydmljZXMxGDAW\n"
                "BgNVBAMTD3d3dy5mcmVldHNhLm9yZzEiMCAGCSqGSIb3DQEJARYTYnVzaWxlemFz\n"
                "QGdtYWlsLmNvbTESMBAGA1UEBxMJV3VlcnpidXJnMQswCQYDVQQGEwJERTEPMA0G\n"
                "A1UECBMGQmF5ZXJuMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAtZEE\n"
                "jE5IbzTp3Ahif8I3UWIjaYS4LLEwvv9RfPw4+EvOXGWodNqyYhrgvOfjNWPg7ek0\n"
                "/V+IIxWfB4SICCJ0YMHtiCYXBvQoEzQ1nfu4G9E1P8F5YQrxqMjIZdwA6iOzqJvm\n"
                "vQO6hansgn1gVlkF4i1qWE7ROArhUCgM7jl+mKAS84BGQAeGJEO8B3y5X0Ia8xcS\n"
                "2Wg8223/uvPIululZq5SPUWdYXc0bU2EDieIa3wBxbiQ14ouJ7uo3S+aKBLhV9Yv\n"
                "khxlliVIBp3Nt9Bt4YHeDpVw1m+HIgzii2KKtVkG8+4MIQ9wUej0hYr4uaktCeRq\n"
                "8tnLpb/PrRaM32BEkaSwZgOxFMr3Ax8GXn7u+lPFdfNJDAWdLjLdx2rE1MTHEGg7\n"
                "l/0b5ZG8YQVRhtiPmgORswe2+R7ZVNqjb5rNah4Uqi5K3xdGS1TbGNu2/+MAgCRl\n"
                "RzcENs5Od7rl3m/g8/nW5/++tGHnlOkvsJUfiq5hpBLM6bIQdGNci+MnrhoPa0pk\n"
                "brD4RjvGO/hFUwQ10Z6AJRHsn2bDSWlS2L7LabCqTUxB9gUV/n3LuJMZzdpZumrq\n"
                "S+POrnGOb8tszX25/FC7FbEvNmWwqjByicLm3UsRHOSLotnv21prmlBgaTNPs09v\n"
                "x64zDws0IIqsgN8yZv3ZBGWHa6LLiY2VBTFbbnsCAwEAAaOCAdswggHXMAkGA1Ud\n"
                "EwQCMAAwHQYDVR0OBBYEFG52C3tOT5zhYMptLOknoqKUs3c3MB8GA1UdIwQYMBaA\n"
                "FPpVDYw0ZlFDTPfns6dsla965qSXMAsGA1UdDwQEAwIGwDAWBgNVHSUBAf8EDDAK\n"
                "BggrBgEFBQcDCDBjBggrBgEFBQcBAQRXMFUwKgYIKwYBBQUHMAKGHmh0dHA6Ly93\n"
                "d3cuZnJlZXRzYS5vcmcvdHNhLmNydDAnBggrBgEFBQcwAYYbaHR0cDovL3d3dy5m\n"
                "cmVldHNhLm9yZzoyNTYwMDcGA1UdHwQwMC4wLKAqoCiGJmh0dHA6Ly93d3cuZnJl\n"
                "ZXRzYS5vcmcvY3JsL3Jvb3RfY2EuY3JsMIHGBgNVHSAEgb4wgbswgbgGAQAwgbIw\n"
                "MwYIKwYBBQUHAgEWJ2h0dHA6Ly93d3cuZnJlZXRzYS5vcmcvZnJlZXRzYV9jcHMu\n"
                "aHRtbDAyBggrBgEFBQcCARYmaHR0cDovL3d3dy5mcmVldHNhLm9yZy9mcmVldHNh\n"
                "X2Nwcy5wZGYwRwYIKwYBBQUHAgIwOxo5RnJlZVRTQSB0cnVzdGVkIHRpbWVzdGFt\n"
                "cGluZyBTb2Z0d2FyZSBhcyBhIFNlcnZpY2UgKFNhYVMpMA0GCSqGSIb3DQEBDQUA\n"
                "A4ICAQClyUTixvrAoU2TCn/QoLFytB/BSDw+lXxoorzZuXZPGpUBYf1yRy1Bpe7S\n"
                "d3hiA7VCIkD7OibN4XYIe2+xAR30zBniVxqkoFEQlmXpTEb1C9Kt7mrEE34lGyWj\n"
                "navaRRUV2P+eByCejsILeHT34aDt58AJN/6EozT4syZc7S2O2d9hOWWDZ3/rOCwe\n"
                "47I+bqXwXfMN57n4kAXSUmb2EvOci09tq6bXv7rBljK5Bjcyn1Km8GahDkPqqB+E\n"
                "mmxf4/6LXqIydfaH8gUuUC6mwwdipmjM4Hhx3Y6X4xW7qSniVYmXegoxLOlsUQax\n"
                "Q3x3nys2GxgoiPPuiiNDdPoGPpVhkmJ/fEMQc5ZdEmCSjroAnoA0Ka4yTPlvBCNU\n"
                "83vKWv3cefeTRqs4i/x58B3JhhJU6mzBKZQQdrg9IFVvO+UTJoN/KHb3gzs3Dnw9\n"
                "QQUjgn1PU0AMciGNdSKf8QxviJOpo6HAxCu0yJjBPfQcf2VztPxWUVlxphCnsNKF\n"
                "fIIlqfsgTqzsouiXGqGvh4hqKuPHL+CgquhCmAp3vvFrkhFUWAkNmCtZRmA3ZOda\n"
                "CtPRFFS5mG9ni5q2r+hJcDOuOr/U60O3vJ3uaIFZSeZIFYKoLnhSd/IoIQfv45Ag\n"
                "DgUIrLjqguolBSdvPJ2io9O0rTi7+IQr2jb8JEgpH1WNwC3R4A==\n"
                "-----END CERTIFICATE-----\n"
                "-----BEGIN CERTIFICATE-----\n"
                "MIIH/zCCBeegAwIBAgIJAMHphhYNqOmAMA0GCSqGSIb3DQEBDQUAMIGVMREwDwYD\n"
                "VQQKEwhGcmVlIFRTQTEQMA4GA1UECxMHUm9vdCBDQTEYMBYGA1UEAxMPd3d3LmZy\n"
                "ZWV0c2Eub3JnMSIwIAYJKoZIhvcNAQkBFhNidXNpbGV6YXNAZ21haWwuY29tMRIw\n"
                "EAYDVQQHEwlXdWVyemJ1cmcxDzANBgNVBAgTBkJheWVybjELMAkGA1UEBhMCREUw\n"
                "HhcNMTYwMzEzMDE1MjEzWhcNNDEwMzA3MDE1MjEzWjCBlTERMA8GA1UEChMIRnJl\n"
                "ZSBUU0ExEDAOBgNVBAsTB1Jvb3QgQ0ExGDAWBgNVBAMTD3d3dy5mcmVldHNhLm9y\n"
                "ZzEiMCAGCSqGSIb3DQEJARYTYnVzaWxlemFzQGdtYWlsLmNvbTESMBAGA1UEBxMJ\n"
                "V3VlcnpidXJnMQ8wDQYDVQQIEwZCYXllcm4xCzAJBgNVBAYTAkRFMIICIjANBgkq\n"
                "hkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAtgKODjAy8REQ2WTNqUudAnjhlCrpE6ql\n"
                "mQfNppeTmVvZrH4zutn+NwTaHAGpjSGv4/WRpZ1wZ3BRZ5mPUBZyLgq0YrIfQ5Fx\n"
                "0s/MRZPzc1r3lKWrMR9sAQx4mN4z11xFEO529L0dFJjPF9MD8Gpd2feWzGyptlel\n"
                "b+PqT+++fOa2oY0+NaMM7l/xcNHPOaMz0/2olk0i22hbKeVhvokPCqhFhzsuhKsm\n"
                "q4Of/o+t6dI7sx5h0nPMm4gGSRhfq+z6BTRgCrqQG2FOLoVFgt6iIm/BnNffUr7V\n"
                "DYd3zZmIwFOj/H3DKHoGik/xK3E82YA2ZulVOFRW/zj4ApjPa5OFbpIkd0pmzxzd\n"
                "EcL479hSA9dFiyVmSxPtY5ze1P+BE9bMU1PScpRzw8MHFXxyKqW13Qv7LWw4sbk3\n"
                "SciB7GACbQiVGzgkvXG6y85HOuvWNvC5GLSiyP9GlPB0V68tbxz4JVTRdw/Xn/XT\n"
                "FNzRBM3cq8lBOAVt/PAX5+uFcv1S9wFE8YjaBfWCP1jdBil+c4e+0tdywT2oJmYB\n"
                "BF/kEt1wmGwMmHunNEuQNzh1FtJY54hbUfiWi38mASE7xMtMhfj/C4SvapiDN837\n"
                "gYaPfs8x3KZxbX7C3YAsFnJinlwAUss1fdKar8Q/YVs7H/nU4c4Ixxxz4f67fcVq\n"
                "M2ITKentbCMCAwEAAaOCAk4wggJKMAwGA1UdEwQFMAMBAf8wDgYDVR0PAQH/BAQD\n"
                "AgHGMB0GA1UdDgQWBBT6VQ2MNGZRQ0z357OnbJWveuaklzCBygYDVR0jBIHCMIG/\n"
                "gBT6VQ2MNGZRQ0z357OnbJWveuakl6GBm6SBmDCBlTERMA8GA1UEChMIRnJlZSBU\n"
                "U0ExEDAOBgNVBAsTB1Jvb3QgQ0ExGDAWBgNVBAMTD3d3dy5mcmVldHNhLm9yZzEi\n"
                "MCAGCSqGSIb3DQEJARYTYnVzaWxlemFzQGdtYWlsLmNvbTESMBAGA1UEBxMJV3Vl\n"
                "cnpidXJnMQ8wDQYDVQQIEwZCYXllcm4xCzAJBgNVBAYTAkRFggkAwemGFg2o6YAw\n"
                "MwYDVR0fBCwwKjAooCagJIYiaHR0cDovL3d3dy5mcmVldHNhLm9yZy9yb290X2Nh\n"
                "LmNybDCBzwYDVR0gBIHHMIHEMIHBBgorBgEEAYHyJAEBMIGyMDMGCCsGAQUFBwIB\n"
                "FidodHRwOi8vd3d3LmZyZWV0c2Eub3JnL2ZyZWV0c2FfY3BzLmh0bWwwMgYIKwYB\n"
                "BQUHAgEWJmh0dHA6Ly93d3cuZnJlZXRzYS5vcmcvZnJlZXRzYV9jcHMucGRmMEcG\n"
                "CCsGAQUFBwICMDsaOUZyZWVUU0EgdHJ1c3RlZCB0aW1lc3RhbXBpbmcgU29mdHdh\n"
                "cmUgYXMgYSBTZXJ2aWNlIChTYWFTKTA3BggrBgEFBQcBAQQrMCkwJwYIKwYBBQUH\n"
                "MAGGG2h0dHA6Ly93d3cuZnJlZXRzYS5vcmc6MjU2MDANBgkqhkiG9w0BAQ0FAAOC\n"
                "AgEAaK9+v5OFYu9M6ztYC+L69sw1omdyli89lZAfpWMMh9CRmJhM6KBqM/ipwoLt\n"
                "nxyxGsbCPhcQjuTvzm+ylN6VwTMmIlVyVSLKYZcdSjt/eCUN+41K7sD7GVmxZBAF\n"
                "ILnBDmTGJmLkrU0KuuIpj8lI/E6Z6NnmuP2+RAQSHsfBQi6sssnXMo4HOW5gtPO7\n"
                "gDrUpVXID++1P4XndkoKn7Svw5n0zS9fv1hxBcYIHPPQUze2u30bAQt0n0iIyRLz\n"
                "aWuhtpAtd7ffwEbASgzB7E+NGF4tpV37e8KiA2xiGSRqT5ndu28fgpOY87gD3ArZ\n"
                "DctZvvTCfHdAS5kEO3gnGGeZEVLDmfEsv8TGJa3AljVa5E40IQDsUXpQLi8G+UC4\n"
                "1DWZu8EVT4rnYaCw1VX7ShOR1PNCCvjb8S8tfdudd9zhU3gEB0rxdeTy1tVbNLXW\n"
                "99y90xcwr1ZIDUwM/xQ/noO8FRhm0LoPC73Ef+J4ZBdrvWwauF3zJe33d4ibxEcb\n"
                "8/pz5WzFkeixYM2nsHhqHsBKw7JPouKNXRnl5IAE1eFmqDyC7G/VT7OF669xM6hb\n"
                "Ut5G21JE4cNK6NNucS+fzg1JPX0+3VhsYZjj7D5uljRvQXrJ8iHgr/M6j2oLHvTA\n"
                "I2MLdq2qjZFDOCXsxBxJpbmLGBx9ow6ZerlUxzws2AWv2pk=\n"
                "-----END CERTIFICATE-----\n",
                "version": "0.1.0",
            },
            "provider": "authsigner 0.4.0",
        }
    ]
