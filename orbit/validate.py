def validate(p:dict ):
    # stop the script if a value is outside the possible range
    assert -90 <= p["latitude"] <= 90, f"bad latitude: {p['latitude']}"
    assert -180 <= p["longitude"] <= 180, f"bad longitude: {p['longitude']}"
    assert 300 <= p["altitude"] <= 500, f"bad altitude: {p['altitude']}"
