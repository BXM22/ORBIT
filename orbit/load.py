import psycopg2  #this is for postgres
import logging
from orbit.config import DSN

log = logging.getLogger(__name__)
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
        if cur.rowcount == 1:
            log.info("inserted new row for %s", p["timestamp"])
        else:
            log.info("duplicate reading for %s, skipped", p["timestamp"])
