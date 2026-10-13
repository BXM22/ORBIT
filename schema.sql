CREATE TABLE IF NOT EXISTS raw_iss_positions (
    observed_at  TIMESTAMPTZ PRIMARY KEY,
    latitude     DOUBLE PRECISION NOT NULL,
    longitude    DOUBLE PRECISION NOT NULL,
    altitude_km  DOUBLE PRECISION NOT NULL,
    velocity_kmh DOUBLE PRECISION NOT NULL,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
