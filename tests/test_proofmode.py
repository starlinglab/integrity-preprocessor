from .context import validate


def test_bad():
    p = validate.ProofMode("tests/assets/proofmode/bad.zip")
    assert p.validate() == False


def test_nojson():
    p = validate.ProofMode("tests/assets/proofmode/no-json.zip")
    assert p.validate() == False


def test_good():
    p = validate.ProofMode("tests/assets/proofmode/good.zip")
    assert p.validate() == True
    assert p.validated_sigs_json() == [
        {
            "algorithm": "proofmode-pgp-rsa",
            "custom": {
                "0b8d8b5f15046343fd32f451df93acc2bdd9e6373be478b968e4cad6b6647351.proof.csv": {
                    "authenticatedMessage": "0dadf8d8d2edbf25137f50058c6b90c6c6ccae969fe99bd6ffbc96a009280f83",
                    "authenticatedMessageDescription": "SHA256 "
                    "hash of "
                    "the signed "
                    "file",
                    "signature": "-----BEGIN PGP SIGNATURE-----\n"
                    "Version: BCPG v1.71\n"
                    "\n"
                    "iQIcBAABCAAGBQJjh22vAAoJEP0ufvrVWf+EzOkQAMYzmrvKS1TZChzeCGasbqqA\n"
                    "PjM6hsGaOC8oV0GvhwmEYrbL/Pq52Oche7RFVcnRUFPUwI6nRTBZDbYyzFr34sDp\n"
                    "VCv6xWPGFdHYi23iHQIAkYgdXK9IT44G+/IBJTPQ/ndueqKiF8coyYbO4WwC3xPQ\n"
                    "OTUJyMgcIgM8UP6kAZLYP09uCwGSUMyLnUUU/3yDD0Jo1R/FJoZD36BtHOSjPgcz\n"
                    "KkFjnNxxjtl/eN59oh3lIf1/TsCJyokuFhC1DIMrWb82L2ScJp0u8T/o1+AAGNBe\n"
                    "AFT1ze7Xywp1pU3bQwDnUO9ZHmTXPKjqRSuSZD2ssdRp2sx2Sz9erSHmpPH6R1gI\n"
                    "dIaAsC2pnqLcqzVMxZo46BWZiUmuBhFahzl+Q04nOcfp4Ff75guhw2Vnd1ET3RMk\n"
                    "4+I4FnZ3Rk1GogUtxU/O1nUWGt3NijTC13xKvvi0tCsp4tXZ+bB8QjKBM+CTDdha\n"
                    "5LRZ+XlrOEMB2RyI0zwpV6R3ftlubk74G1vJ3d/AqtqoVhpO1lNKjS/7RuqrJuxa\n"
                    "cX4/oBlZUcHHIr8e2ddTUDYqhh9TigaoWWNFIpvwIMoZFW6XcXhB68rDcSr9Gl+1\n"
                    "SXwD8Y3JNd3eQBH9HTPLoY1kMV5YwJaFaJ7SERpuIxrZUN3a3dsD0KvWhicy0kUA\n"
                    "dCRY5IARbtM4RrB9ic67\n"
                    "=E/J0\n"
                    "-----END PGP SIGNATURE-----\n",
                },
                "0b8d8b5f15046343fd32f451df93acc2bdd9e6373be478b968e4cad6b6647351.proof.json": {
                    "authenticatedMessage": "14d1b28f6b96f998ee0d96b96af49ce27b98292a882e7f84a37fc6cb1d7dca59",
                    "authenticatedMessageDescription": "SHA256 "
                    "hash of "
                    "the "
                    "signed "
                    "file",
                    "signature": "-----BEGIN PGP SIGNATURE-----\n"
                    "Version: BCPG v1.71\n"
                    "\n"
                    "iQIcBAABCAAGBQJjh22vAAoJEP0ufvrVWf+ErhQP/RKsE70qMBMW3l2TIxFOmD/5\n"
                    "M9oJSOqDZFxf8W9zE3jQwpuqaEWgVjyBWAD2B4kppsHTntC2xyOvbc6CB+K2Y5wb\n"
                    "cPI86bmgLR9ygTnXsxRtOR3X99CrwN+z6WcMi7uvYjPGjgiN9MCSPYyUa68vJ56z\n"
                    "Q/CdT0seCIUWuaSmGnG1ShgGCMKqCCcY1zzhTiBKkxwis3PIoWUZvpzGayVkudXH\n"
                    "SV+Yg3UG+UlqlwwmJ9gZQwGd4q/koNC+TC2F1GPmv0rTNuK9q7y5gvw19+jtnwgK\n"
                    "apqEH6q7X15XeQuQLQSsBXOQgBnELOARxJakmH/hkXUmGlvKTl94cO0qWdEoMd/A\n"
                    "FuQH/704oETQsOekbRxqI7gwTk8wPZ7KxBwbIpW7cu5xV9RGk/qetY+AVj5eZFq6\n"
                    "LhUugTZbdiLc6cN0DaMZ9TJXvFEmXoKrALqxBF0iMbigg+Y6xmBlvamCYdYbGb9w\n"
                    "3pb2atQ6YKmIMhcD7SInj1XbkFEHXIq5rPemb8HRxOcOIi/zdsPpdvRZSswo8YWG\n"
                    "+givf93ysBIxKOPiOW2mAEb8mo726E8mCtqmtzXgz03FSnauvWUPZfJpsTaiPX+S\n"
                    "IJ0X4QOUQqL7/NIUTz0I02kKWYl/JqoKqGN2gjmO5W471RWKFrtaNISIakbDPzbg\n"
                    "VEU9J7JyZjXKP/zIwTmO\n"
                    "=MvmH\n"
                    "-----END PGP SIGNATURE-----\n",
                },
                "smallest_jpeg.jpg": {
                    "authenticatedMessage": "0b8d8b5f15046343fd32f451df93acc2bdd9e6373be478b968e4cad6b6647351",
                    "authenticatedMessageDescription": "SHA256 hash of the signed file",
                    "signature": "-----BEGIN PGP SIGNATURE-----\n"
                    "Version: BCPG v1.71\n"
                    "\n"
                    "iQIcBAABCAAGBQJjh22wAAoJEP0ufvrVWf+E9k0P/jicmi5uu7evFYvpyokVRCS9\n"
                    "gicOCYpqIFGVKtDPszj0GTSpuw5NmOorZjTJwQVi944kxZQ5I1T9/VGO0+rpBs3S\n"
                    "9Q+zNOsXROTWnqpklB8Fq1rXf/gnO1caqEfg5nr3PSN+szqyBowlfTm07Ek+0A78\n"
                    "Y5kf4t8y7dE1A/s0nls2wZ/dyxCNpcxcoOJe4WIafANVMR8OoP17PrlDGhvezu/k\n"
                    "uqwADnFukSkHYY5begCY4PoDpTAomr4N0T7nIv0TITXhuZjXN5GaEzm6bAOMngsm\n"
                    "Nbhfw/9EBwg/icvQmhYbPRZQiuFL++K1srJTbo5Ey5UOb1Y7fEPX7pTAP31iRkSi\n"
                    "5fPhD7tkkBc5J7nG3Bd6cFOJxqTmxImX3EnMUWt1YoPa0bkCoHgfgDgCfpbPp8mq\n"
                    "KIMBUDglwlhnIQxbJB5VmA9fgUmLrfDX7ZbEEwnoO8CHG5ZfWHC66suwLPv3KIYP\n"
                    "YRoBzBucJZsOX8vAc76t5/m5WoUFNuNw0YHtEunMeX6GHzDlM8vxZ7MXZ/m2mSdo\n"
                    "3w44LmM+Qc0764Kcg3FFR9ZM8u8Qg5IFQqhwCwDpkNqD2VlXUfMQDMxf5FAnRHuw\n"
                    "lcJNpyFBYavtwBMXdPg7Slsowyg7OoNOOjmHN7SUaTOBAW5ceRK8mGVScWmhrb/M\n"
                    "PDynwxYBtMypTvhYeZaC\n"
                    "=xAmm\n"
                    "-----END PGP SIGNATURE-----\n",
                },
            },
            "provider": "ProofMode v0.0.17-RC-1 autogenerated=false",
            "publicKey": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n"
            "Version: BCPG v1.71\n"
            "\n"
            "mQINBGOHbaMBEADKpWzUopGRXsfywZeNLlvmIjL0EZIWW7IhwrudY5f9iAjlEd7Q\n"
            "KO94WDrXeOVACTG/eI0Q7qPtUMWG6zDUBoReUIihbJNG77lQETgx4zqbuWVblxV+\n"
            "1enc51AoRwAnbyd1OagcZnuAdO4CcPsS4JPFiGAfKeLfRaXlEOwh6iw6D2CMjZTI\n"
            "NAjRGugd0NSKUpSvPsevNIM16H/PvyLJTFjp6BWYbv9zUVyWisZONExFshqlqP0b\n"
            "g8MdxKJ4a6US3b7JXe/xSQAvRNeKC1V6K0jfo3PrrYeTe5tid80yJDPncIKs9K6t\n"
            "PaLsfExlfKTw7pe58R88VrbiV9eYtMaf5mfx4IqzYZlocQNsiWZ4UT8TRV5mhiTX\n"
            "O4opxbuR1ChfdzFSLgvvwIJxtpaMIZc+bw7VocNbLDaCOnqnI3obydlLA/2A1j3q\n"
            "ycH/T1NEl6w085LKT5ZwGOpa4zodT4xvuMLtNkQc5NlFbRKgkcvuSgRjUOzYOKwC\n"
            "QHLzoeOh5MgWWsr3gxsgWEE+c84Z0EvEvCH6vXBw5f7tsTjy5CQBNdrJ3TGeMuDY\n"
            "XlpWzEvlE7airaX68J+mKVjwH8/i1luozK0xy7dT3EmDnpur0tVhO9jR02O6HhVg\n"
            "o4NxSGKYJ6rPLGLBNNKyByV+cIPNSvdLPc5B98QP3FyPn0VuCg39vQW+NQARAQAB\n"
            "tBtub29uZUBwcm9vZm1vZGUud2l0bmVzcy5vcmeJAi4EEwECABgFAmOHba8CG4ME\n"
            "CwkIBwYVCAIJCgsCHgEACgkQ/S5++tVZ/4QEIhAAwAPIKnle0oDv6ioJfcBhADqK\n"
            "77thdnehS5DDE53SiyjveS8ytZTlHWdZkB2QvTTuHa0+8QpvP6vWi8onCjOviNqM\n"
            "N0gEH1YrqFznEp+py5mF1H1vZa9MNS+ZwSRlcTZQs2q8VrBVsT+TwQ0+juEOeAhN\n"
            "hNZjhnVkJXtbjkKkGUco5v3vm2y1vnpIQH2sdK7aPu6d+VOZWJmnt934d7LPcwoo\n"
            "8DiPgFwymuBIoBN4ZJDkokUC3EhlA9Wp55q8mNvY0E+M3PLxsJcMsJWP0OXJGCNo\n"
            "wYenPHnuOAKiSdoY1zPYPmlAGzf+TIweQwKk9gKrgZcujIOLuNjtMeM6qx/jhD2o\n"
            "74mtaAcR+5O1wmvrrWELpi09vPgbmJsjWAQ9HjakJGSOU/lJU9jcGyg07g9gS7xj\n"
            "8qft+y5XynytROa71li9xADLiWr6EVoSTqDB7DPccwlWVJjsPMQznc8/jEuxG5NV\n"
            "VHVH6BQgLovtSofLsod7+rRhJ9hXB/aylU7otFf8VGGCAwWNIK5OVHpZR0A0JBJ4\n"
            "/78WoZqI8W4T/+4T9emjbr6zbYDux76WwQImFJrSABc5yYTHmv0O50kJI8TWejIy\n"
            "JonmwVEem14Mbm4tYm16QW9gBMPdwnpzS0Z64e5v5+iLZuc9iVuwR8KDLaWEE0mC\n"
            "AY0ZvyWxsUakEayEkbq5Ag0EY4dtrwEQAK5PjGygXc/6pSdREDkK3MtGxsBlZLjC\n"
            "WHJbfuaK2RIFxm9kLYvw7cF0Rf4ZM7ZAGF6H2WrA66WtDujJSfdPznHGHKm85u8y\n"
            "2sPcme48x/1aKzfchiL3Qw/Uc+dIdZjLgG0GS3EPJ9WqcgeBFDTTCWg8kbS3QrQy\n"
            "AhMV7VAEieJuTcjMY7wYX0gAudVEDpXDZKur8K0K+ciNjWscbyF7l5KWBZ+5I/Ff\n"
            "lqQ9HjrSKEbIkjyvEp06rKK18Sw1Fl169y/1TYuZSEhuUThU91RxKzObxtJ6rp+6\n"
            "4Y6fHO7nsTS21sAO7wylewqXE7dPl1EglYLdeiybe6Q8oBw+UzrbyJnKlLwLvRC7\n"
            "iPvsvjObnEZUnoBvfdfd8527cErMSnZuOg8+1l2UNOAT4MxGBHCWuK2H4kpBjspR\n"
            "OV8ekIVrx6TxBkD2BHfxcffpcqIZWgW/xS46zUG9AFDarXSllYXRLCPG6/ddVha4\n"
            "silBv0zcWLSwSe33QJJ8/fTt4QFLlt+Z81Sg2GAhKrh5OlB/Jl/+dTIcmmnx6YIM\n"
            "WsAUhECmNgRRrphFlOykldIoJshlsi+o+voSaKMVHAIy4tRi2AzZTzuZPqWsll46\n"
            "Cm69tS7KvbJGt2vk2tjb5Uq/YIQ54jOjeO7p77JxGWC8I0Xzq43If1DYspbwVade\n"
            "6/NEWv9jMSMZABEBAAGJAh8EGAECAAkFAmOHba8CGwwACgkQ/S5++tVZ/4RUtg//\n"
            "QgLgPi2b0KN+ov9q6Hs9tQoN935i5twejX9GzbcHWXHzEZOBpqEN9qTuJmRLAPrF\n"
            "X2T/vYoli2xhS5zG2h+eFRTWMl60LyncpK19Yvij7EIsrR8sPa2e3GIgfzyyvL9Q\n"
            "Ly6K2W3ysutUviZ1TYGKlw8XTsnxvKm8efbqCY1Dmp3C7Zee1cCvP23u3TOO+09g\n"
            "/6SFa0WYkWFi4xXkWspSymU4R6IW4JSQ0eQDGNWT1zGx5KSfmvFg1HnWJytNFhWj\n"
            "mbkrm13TV8Ke8f+Z7s8PnIBm2puXuFM8z82E8Wo+aQdjDaiPBm7rLEQ0a9rO5cyB\n"
            "aNj+St55y0D/t7pUup0kC2d8VhNxTmh6NcReSkb9DBIrNh0oE940lxi5SEP880u8\n"
            "kskJyDo91S7Dq9gZ190kHu7QSuN4uWwNWoPU6ycLHCy6NhDcFvqGP+IjmyvF1Ptg\n"
            "RSBW4tmbYYqlsEPpzrFKeNTIFq/ObpaaDD689wW2xdwfvqmfXos2aWiLRBIrX+7q\n"
            "HicRJ5uEqzaBDN50Btodnx1QKljhsFnikf5DftwF2yQeShzjMLeBB8dJ3cC0em8B\n"
            "+6Aolv8oohc/bKV7uk013O554iGS3C906cMCvOAGl/x6ZFwKuOHndJrY1GefNIBL\n"
            "7gkKTSVRCoDx/zcgs9VzPVLyGA515rcurNJ0B/qrcAw=\n"
            "=JxUH\n"
            "-----END PGP PUBLIC KEY BLOCK-----\n",
        }
    ]
