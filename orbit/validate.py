from orbit.exceptions import ValidationError

def validate(p: dict) -> None:
    errors = []
    if not (-90 <= p["latitude"] <= 90):
        errors.append(f"latitude out of range: {p['latitude']}")
    if not (-180 <= p["longitude"] <= 180):
        errors.append(f"longitude out of range: {p['longitude']}")
    if not (300 <= p["altitude"] <= 500):
        errors.append(f"altitude out of range: {p['altitude']}")
    if errors:
        raise ValidationError("; ".join(errors))