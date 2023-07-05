import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
import geocode


def test_geocoder():
    test_location = {
        "countryCode": "ca",
        "city": "Old Toronto",
        "countryName": "Canada",
        "provinceState": "Ontario",
        "address": "Toronto City Hall, 100, Queen Street West, Financial District, Spadina\u2014Fort York, Old Toronto, Toronto, Ontario, M5H 2N2, Canada",
    }
    res = geocode.reverse_geocode(43.6532, -79.3832)
    assert res == test_location
