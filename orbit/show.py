import sys

import psycopg2

from orbit.config import DSN

def latest(n=10):
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT observed_at, latitude, longitude, altitude_km, velocity_kmh
            FROM raw_iss_positions
            ORDER BY observed_at DESC
            LIMIT %s
            """,
            (n,),
        )
        return cur.fetchall()

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"{'observed_at':<26}{'lat':>9}{'lon':>10}{'alt km':>9}{'km/h':>10}")
    for t, lat, lon, alt, vel in latest(n):
        print(f"{t:%Y-%m-%d %H:%M:%S%z}  {lat:>9.3f}{lon:>10.3f}{alt:>9.1f}{vel:>10.1f}")

if __name__ == "__main__":
    main()
