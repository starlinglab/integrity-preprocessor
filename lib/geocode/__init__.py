# Adapted from integrity-backend
# https://github.com/starlinglab/integrity-backend/blob/65da0c51684cb02da1a83b5a989a2e087e1be543/integritybackend/geocoder.py

import geocoder


def reverse_geocode(lat, lon):
    """Retrieves reverse geocoding informatioon for the given latitude and longitude.

    Args:
        lat, long: latitude and longitude to reverse geocode, as floats

    Returns:
        geolocation JSON or None if address doesn't exist

    """
    # TODO: Add some kind of throttling and/or caching to prevent us from sending more than 1 req/sec.
    response = geocoder.osm([lat, lon], method="reverse")
    if response.status_code != 200:
        raise Exception(
            f"Reverse geocode lookup for ({lat}, {lon}) failed with: {response.status}"
        )

    if response.status == "ERROR - No results found":
        return None
    return _json_to_address(response.json)


def _json_to_address(geo_json):
    """Convert geocoding JSON to a uniform format for our own use."""
    if (osm_address := geo_json.get("raw", {}).get("address")) is None:
        # _logger.warning("Reverse geocoding result did not include raw.address")
        return None
    address = {}
    address["countryCode"] = osm_address.get("country_code")
    address["city"] = _get_preferred_key(
        osm_address, ["city", "town", "municipality", "village"]
    )
    address["countryName"] = osm_address.get("country")
    address["provinceState"] = _get_preferred_key(
        osm_address, ["state", "region", "state_district"]
    )
    address["address"] = geo_json["address"]
    return address


def _get_preferred_key(some_dict, keys):
    for key in keys:
        if key in some_dict:
            return some_dict.get(key)
    return None
