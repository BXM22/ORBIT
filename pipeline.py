from exceptions import ValidationError
import requests
import psycopg2  #this is for postgres

API = "https://api.wheretheiss.at/v1/satellites/25544"
DSN = "postgresql://postgres:postgres@localhost:5432/iss"

def extract():
    resp = requests.get(API,timeout = 10) #request and timesout for 10 sec
    resp.raise_for_status()
    return resp.json() #getting the data

def validate(p:dict ):
    # stop the script if a value is outside the possible range
    assert -90 <= p["latitude"] <= 90, f"bad latitude: {p['latitude']}"
    assert -180 <= p["longitude"] <= 180, f"bad longitude: {p['longitude']}"
    assert 300 <= p["altitude"] <= 500, f"bad altitude: {p['altitude']}"

def load(p):
    #this will open the connection to the postgres
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw_iss_positions
                (observed_at, latitude, longitude, altitude_km, velocity_kmh)
            VALUES (to_timestamp(%s), %s, %s, %s, %s)
            ON CONFLICT (observed_at) DO NOTHING
            """,
            (p["timestamp"], p["latitude"], p["longitude"], p["altitude"], p["velocity"]),
        )

if __name__ == "__main__":
    payload = extract()
    validate(payload)
    load(payload)
    print("loaded", payload["timestamp"])