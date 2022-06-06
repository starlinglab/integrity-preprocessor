from .context import validate


def test_bad():
    p = validate.ProofMode("tests/assets/proofmode/bad.zip")
    assert p.validate() == False


def test_good():
    p = validate.ProofMode("tests/assets/proofmode/good.zip")
    assert p.validate() == True
    assert p.validated_sigs_json() == [
        {
            "algorithm": "proofmode-pgp-rsa",
            "custom": {
                "0b8d8b5f15046343fd32f451df93acc2bdd9e6373be478b968e4cad6b6647351.proof.csv": {
                    "authenticatedMessage": "9043daeac0e7e12e9cc6b5a3e505d2f3ccf41b037130d0ad055917d99471ffd8",
                    "authenticatedMessageDescription": "SHA256 "
                    "hash "
                    "of "
                    "the "
                    "signed "
                    "file",
                    "signature": "-----BEGIN "
                    "PGP "
                    "SIGNATURE-----\n"
                    "Version: "
                    "BCPG "
                    "v1.71\n"
                    "\n"
                    "iQIcBAABCAAGBQJing+HAAoJEMgOMxs3dUSrJZEP/R9kJZRlRSkmoT0CFgT7Uvat\n"
                    "AGkuDs1c7pxuSMOxTn8g454LQQlsr7dYJdyeX1tv1NHk09dgi1telOB20BF1gS0G\n"
                    "ZEs8Nboi4rkDfQLKim8szH8uIiXqKlFHOmshuX0Ce/8CFrENQdQpZQrD3fDfdrJ/\n"
                    "851BkaKmQdQvei1xDZ1KTXmC/sPGRCfdJa1IBj7FtuCGsNh9bPVpgMfjeUkz/9jZ\n"
                    "X0jzqhWFx0LKkRxJERiQxGYDYPI8qkQRs0L32R/PImD7NhrOODPNAmthWephTXZn\n"
                    "6Px0kOk7jpEnqYG56DVW9Uy7IhETkqmN/EqYAjL4QAD6lEaGzIwIGvNaBU3XUJOM\n"
                    "6yLxqrKLTyIqqeVvhvyTOKf7s/EG1khlCk8qlrpWjZ+Nqbcd/yRHBV2GTiG5CPrS\n"
                    "VnN/3IjoZpddyUGgnjdcTQXmB4vhIBhevRIwFhS0PEE+lt/SlJjb5m+kdRxjBTKh\n"
                    "ivKa8bigpA1c5ZRI1yCUMtIFWDdMLoUoXzuWbJU5QKmO1Kt0nmQmVwhHJ8LZM/GY\n"
                    "Dmer4C2SXHz3oC9FnUr7O3IqXlDV2zNu37rQbcj2cjFw5UdVsNNHZ5Zyd8rMlsKI\n"
                    "/hY/eP+7lsFFOqC4JOAXHUqIAjhgpPbhG5kmdkGCmBl0qUb07WzLZrgOwhe/rfGI\n"
                    "tO9mFuPzD+GCANMcXpl0\n"
                    "=NZQZ\n"
                    "-----END "
                    "PGP "
                    "SIGNATURE-----\n",
                },
                "smallest_jpeg.jpg": {
                    "authenticatedMessage": "0b8d8b5f15046343fd32f451df93acc2bdd9e6373be478b968e4cad6b6647351",
                    "authenticatedMessageDescription": "SHA256 "
                    "hash of "
                    "the "
                    "signed "
                    "file",
                    "signature": "-----BEGIN PGP "
                    "SIGNATURE-----\n"
                    "Version: BCPG v1.71\n"
                    "\n"
                    "iQIcBAABCAAGBQJing+EAAoJEMgOMxs3dUSrq94P/iAeitoeA6jVtTn5NtmTYS0o\n"
                    "hHdSqxltUlzLg3cN1WndKYSCRowVj9h2a6FnxIg528jaKoJbkZpsTu77lDVGjhJL\n"
                    "U1WWBHytBkS0+39ohm19MAKpXcVJ40sGO9yjHzcLm3HJZjAkSA27Ct/6ja1aVKAR\n"
                    "JohDUiPbv+WhgFEIFZo55+5YpR59DFtD6Ae2DRO3dgPMe5lqqBh/pIeu1fvUE8MC\n"
                    "FcO3E5KjIG+3wY9FOWBLlwjqKfbNvSv+pWFI6NHKyQ3C+ng3xIa8/KeTbW3rw1oU\n"
                    "rZjjVgl1rgMz7hEUwzUkgp9ilP44chSpxlwgj6dc9fUy4bznoKp3sXHyOcar19qj\n"
                    "p30DWvAglCDRHiTIVe3yLjvbZl1XH3XJs9Wefo/Zh7sukP5sMasEGLq34dzSisXW\n"
                    "gci7agHPnjYJxWGDEdywQLgSR8pnjFMys/eoGJPF/qYskAhnROw+yTFRzsBm3Y0p\n"
                    "b/F+WlGoHN8Lz3yi21CirmAOlshDPFTTQgx2rdTsSDwa26zc/1eVTOyLXe6FrtaK\n"
                    "glNN41ajxbRcYZsBeq+jeYBZUWiQcPNEG8+zkt3ah1rTUi/TurSwesN6WQNtGuJD\n"
                    "Gg1HvlwlE0cCSZT7uSU3bAKvwXAX6XD4D+ws+pkaRpTM/sEEsc6EzbvNGrPU3oQ8\n"
                    "IgMUv1PooeXBcP8zn8/y\n"
                    "=Xe/3\n"
                    "-----END PGP "
                    "SIGNATURE-----\n",
                },
            },
            "provider": "ProofMode v0.0.16-ALPHA-2",
            "publicKey": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n"
            "Version: BCPG v1.71\n"
            "\n"
            "mQINBGKaD2wBEACxKqK4U7YlA6KFGAj7iUk81fyTgel5ncOQiSKysp47xqXbb0bd\n"
            "tRk2hNc7ZQuwMqFzme8DTRn7wllwjCmL2rB9rBgPNR9KanHBomlDs7IlR6rnrtCn\n"
            "NFEhka944ui5UMbR1r7B+uzVNb3iHHUIjDFsZvFjXJK0HkUFAnZG/1Wld5IHqAjg\n"
            "2X5g6blHnOhbc+nFumnEAPKJJQM5PdGc7DAi6JvjPk78iZpjOV4drJSxGZeTWZFS\n"
            "GhR31gdrdcEWKo4VrVfODGEadjD1mBBQsNquJJoA4Zm1GwU0j66fjtHVITi76Hmw\n"
            "2h8mn04W8/FtJuHy73d7HgpSQMP4X9ipvTr401jsATEYSTFDJoQ8R5Vs6s3I1rJC\n"
            "khQDAbhwU3DnUeS1+JK7NjSyOg0s/OBdOUsPVxvX6Pg/Dq7B1fHqw0Xl/CuKv02B\n"
            "ODNN/c79YajRuOHhIn9cabaTISBExfnz3TTZnNJKioQtfW0hIVUfJg4fTzZgX0Wm\n"
            "ivxFMpTeq/RNV7Ekl7pp6UK/oknbdus9Z0ZSP+c9cWE8M/Bp+1Pomjf5n9ufQ9mG\n"
            "WrPPayZh/vKx3dh9nJ0IAEgJFSiJSmOsjUa0MJ4f4kohxAdWcAx5HvGQu2mveXcN\n"
            "IOYv4TaJ96TRXlpAVoCRIPzDiEoazlS4KKhdt/AtZNqgNy1T9Z1p8cGWjQARAQAB\n"
            "tBtub29uZUBwcm9vZm1vZGUud2l0bmVzcy5vcmeJAi4EEwECABgFAmKaD3sCG4ME\n"
            "CwkIBwYVCAIJCgsCHgEACgkQyA4zGzd1RKs+zRAAqsEm8IhpBQXUuG3BR4OwCEVF\n"
            "tpXVoku7lT5ACOfZvtOQO9kHglt4nZbFiRsyXCGah6KJGvkQKwkCRzaNgmmTnZFc\n"
            "k2Wgwh6jZSGzuvDR2f29UsOK4QOKk1ip8S01BjjVb3pwxM5Qymqrd19NP26QnUyq\n"
            "KDMSoiY2v1VsERAZekvuLjEZpnxtK3yVH7hbxWoNTM7q5qbxIakj6eDVbTaA0Mw3\n"
            "ohZerdoh3JtnoL+js8RvUsX9Swgc/eydh+1Qu+IMVw3x7CZb3E0+S2DDGKFnXO0G\n"
            "VMbT9rtpCHZYiVMArz+jUveie2SzCzwTmJzoyZwDkUZyur7wDS1+fBACEYyLYING\n"
            "SV4Iw4Q0qufIWbEDsCixFZy/PUcAd/SfDfOb5J7me7cb4UIy8TXKR+FPUcVvjDTx\n"
            "fdwxt7W+ah1BfX+t38kvwRF9b7KdhlhVWKLBwTCGUSS3r6zp6wedSHNeKwggMbjD\n"
            "mhxTt11ab5uW1XPedCqBKVQpOUu6s5kiGIlHheNhk1wLTj7vu7ZP12+xM6LS1dXV\n"
            "RIdWCYTAdFVxM237mRM50WNiiqhSDQisvR6HuebxFnFzflA+wU6Ft1gNcQ192/TP\n"
            "U62cohpZ3sUCZ/TJN/+6PMQ/UBlmZy2MGady4cid37n6YZsA/XTOR2DJvo6KlCry\n"
            "MK+hMjYy06kRNeG0adu5Ag0EYpoPewEQALyOvVyiaYMm+cuk/CrqCJLPjK9jpXfw\n"
            "VbnCXwT9z+1L5kC6CS2sQ07yusc7Dbts/H1DBcKzXu1/oIma8fROrBVJ6TqbWQpK\n"
            "r/lLWMGA0/h6FtB8OLstz8/yYfjWgz+yGUo4SqyVWFy6YyQX3+BLxJyMPC9hcbqq\n"
            "Rwtua4PKCB6yi9u4GIfB/+Ir/PaNGAXqTl7yQ2nG0+qhkamFSkPIK4qHTZOuNazO\n"
            "Gr0dF6hNNo8Somo9TuTsZ9M3rptZgCe9b7arCv6FBbWV+ByGyIbr3iqAmLnv4qBS\n"
            "32NjRiaR4aQdxExfW7x9zesM5/WtWWFQzjdzvC4ZaT84/Ix1m1VmiU+A2gbTcmjl\n"
            "ISmc20lyxvo7ti33Ra3tSlCajXvGazVjM6xYVgvJTcK11WVIiY79H6JepiczbW4r\n"
            "KiAulrchnw8OArdLyiVoV7ul63/P8sx8mwoPAq/ZapoTCOcAJuFd8Ld3LQwIK3NA\n"
            "zOPzTmJm+Wqr5xI3RZYNfkHCsutdnnaW+pASaC0Ql2o66818BLBhGnnSJNPAo6x2\n"
            "WdyPRTJbufzaI6Xsk9NjPTUonZxhvRw+/nmR/4PSAJsm+TNvdWYFq2xSaUS7STrb\n"
            "/xEVcC6mU0jQjrhKAzlG79Ds63GmI7pEtQeU8sOjYnIhuuYy2dH+vVGlYNY7LJWs\n"
            "22Nr1rJZBSlHABEBAAGJAh8EGAECAAkFAmKaD3sCGwwACgkQyA4zGzd1RKsD1g//\n"
            "eJWSxw2O923tmm8dJcLh7p+lzc4OwmxRkxD2rdwkrxsOamUPpPSCYA/8RBKC1muB\n"
            "Veb29DE1Ay/VeXWn7LbpPTtikrc/sbA7MbVrhjnfOT2LbXR6lRkHiqVQYuKWOSkr\n"
            "i2YeaQ0FzlnBwqNjKU86MVwLWpkyGcAU/SBgu8Fwy/lk9DSWczlSuqTUpS9OirxT\n"
            "lI6qtJr84nh4nwCdCzMf2EqlwrDlqolO3EvYzEbLmK4gBUqVmlBuAW3dwIkv83PA\n"
            "T3F9aCebUeKdorpqgE5+n/9uuigQ2xPdZakL6EWcn4ZpJeYz5crkpApkpUWH8OPJ\n"
            "7D6vEABU9j/ARtSO/aEbwz6p4vwUuNjCh6SU0tHhi0/1P0nsY7NEefxsguIugb/F\n"
            "VzmVwUrj04i2rCwEzFgtJTEiVRnKdcmPpwXHz5ydmYfZfonDSNvoMSpozGI426hH\n"
            "brclIFKI2mXcErlrMtOKJV2HUsQTHQ/GCPBP0ZBKh6T3xdi+jfctfDDFgmm4qIR5\n"
            "9xslyjYSRZmorf3qUsXnll5dJPsLYHrfAy2W34prWAv+fvhsTCt39a/MXolICjEQ\n"
            "WinfPGqyK7HWxWiw2ceCrJtv/zFxWLjaGFksB0y+T6r4s8vzvgw3rpRuJx8f2Y31\n"
            "Eqie2gIYti9E8KTVj2tmo1SfvSZMcDoo7yI6Ccr+dWI=\n"
            "=pAyD\n"
            "-----END PGP PUBLIC KEY BLOCK-----\n",
        }
    ]
