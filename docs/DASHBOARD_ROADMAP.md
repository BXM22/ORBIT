# ORBIT Dashboard Roadmap — a step-by-step tutorial

This is the README's "dashboard on top of the summary view" roadmap item,
written as a guided exercise like `docs/HARDENING_ROADMAP.md`. Work through
it yourself — each step shows what to build and why, with a worked example,
and a check before moving on.

**Do this after** the testing/observability work in `HARDENING_ROADMAP.md`,
or at least after Steps 1–3 of it (structured validation, logging, env
config). A dashboard reads from the pipeline's output — it's easier to
trust and debug that output once the pipeline itself logs clearly and
doesn't silently crash on bad data.

## Why a separate API layer

A browser can't talk to Postgres directly — there's no driver for that over
HTTP, and you don't want to expose a raw DB connection to the internet
anyway. You need a small web service in between that:

1. Runs a SQL query against Postgres.
2. Returns the result as JSON.
3. Lets React (or `curl`, or anything else) call it over plain HTTP.

That's it — this "API layer" is a handful of routes, not a big framework
commitment.

**Scope for this roadmap:** one minimal FastAPI service with 2 read-only
endpoints, and one minimal React page that polls one of them and renders
something. No auth, no websockets, no build pipeline beyond
Vite's default — those are extensions, not prerequisites.

---

## Step 1 — Add a read-only API service

**Why:** this is the only new piece of infrastructure the dashboard
actually needs. FastAPI is a reasonable choice here specifically because
it gives you request/response validation and auto-generated docs
(`/docs`) for almost no code — useful while you're still learning what
shape your frontend needs the data in.

**What to create:** `api.py` at the repo root (sibling to `pipeline.py`,
same flat-layout reasoning as `exceptions.py` — one file doesn't need a
package yet).

```python
# api.py
import os
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DSN = os.environ.get("ORBIT_DSN", "postgresql://postgres:postgres@localhost:5432/iss")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default dev port
    allow_methods=["GET"],
)

@app.get("/positions/latest")
def latest_position():
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT observed_at, latitude, longitude, altitude_km, velocity_kmh
            FROM raw_iss_positions
            ORDER BY observed_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
    if row is None:
        return {}
    return {
        "observed_at": row[0].isoformat(),
        "latitude": row[1],
        "longitude": row[2],
        "altitude_km": row[3],
        "velocity_kmh": row[4],
    }

@app.get("/positions/summary")
def daily_summary():
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM iss_daily_summary ORDER BY day DESC LIMIT 14")
        cols = [c.name for c in cur.description]
        rows = cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]
```

Note this reuses `ORBIT_DSN` the same way `pipeline.py` does (Step 3 of the
hardening roadmap) — the two services share config, not code, which is fine
at this size.

Add to `requirements.txt`:

```
fastapi
uvicorn[standard]
```

**Check your work:** run `uvicorn api:app --reload --port 8000`, then in
another terminal `curl http://localhost:8000/positions/latest` — confirm
you get back JSON matching the most recent row in `raw_iss_positions`.
Visit `http://localhost:8000/docs` and confirm FastAPI's auto-generated
Swagger UI lists both endpoints.

---

## Step 2 — Scaffold the React app

**Why:** Vite is the fastest path to a working React dev server with no
config — appropriate here since the frontend's job is "fetch JSON, render
it," not anything that needs a heavier framework (Next.js, routing,
server rendering).

**What to create:** a new `frontend/` directory, separate from the Python
code, using Vite's React-TS template.

```bash
cd /Users/brennenmeregillano/Desktop/Code/ORBIT
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

This gives you `frontend/src/App.tsx` as the starting point, and a dev
server on port 5173 — matching the CORS origin already set in `api.py`.

**Check your work:** `npm run dev` inside `frontend/`, open
`http://localhost:5173`, confirm you see Vite's default React starter page.

---

## Step 3 — Fetch and display the latest position

**Why:** this is the smallest possible slice that proves the whole chain
(Postgres → FastAPI → React) actually works end to end, before adding any
visual polish.

**What to change:** replace the contents of `frontend/src/App.tsx`:

```tsx
import { useEffect, useState } from "react";

type Position = {
  observed_at: string;
  latitude: number;
  longitude: number;
  altitude_km: number;
  velocity_kmh: number;
};

export default function App() {
  const [position, setPosition] = useState<Position | null>(null);

  useEffect(() => {
    const fetchLatest = () =>
      fetch("http://localhost:8000/positions/latest")
        .then((res) => res.json())
        .then(setPosition)
        .catch(console.error);

    fetchLatest();
    const interval = setInterval(fetchLatest, 10_000); // poll every 10s
    return () => clearInterval(interval);
  }, []);

  if (!position) return <p>Loading...</p>;

  return (
    <div style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>ORBIT — ISS Live Position</h1>
      <p>Observed at: {new Date(position.observed_at).toLocaleString()}</p>
      <p>Latitude: {position.latitude}</p>
      <p>Longitude: {position.longitude}</p>
      <p>Altitude: {position.altitude_km} km</p>
      <p>Velocity: {position.velocity_kmh} km/h</p>
    </div>
  );
}
```

**Check your work:** with both `uvicorn api:app --reload` and
`npm run dev` running, open `http://localhost:5173` and confirm the page
shows real numbers from your database, and that they update roughly every
10 seconds as the pipeline (if it's running on its own schedule) writes
new rows. Stop the FastAPI server and confirm the page shows a console
error instead of silently breaking — this tells you the fetch is real,
not mocked.

---

## Step 4 — Plot it on a map (optional polish)

**Why:** lat/long numbers on a page are correct but not very compelling.
A map is the difference between "a JSON viewer" and "a dashboard."

**What to add:** `react-leaflet` + `leaflet`, a free open-source mapping
library with no API key required (unlike Mapbox/Google Maps).

```bash
cd frontend
npm install react-leaflet leaflet
```

```tsx
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// inside App, once `position` is loaded:
<MapContainer center={[position.latitude, position.longitude]} zoom={3} style={{ height: "400px" }}>
  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
  <Marker position={[position.latitude, position.longitude]}>
    <Popup>{position.altitude_km} km altitude</Popup>
  </Marker>
</MapContainer>
```

**Check your work:** confirm a world map renders with a marker roughly
where the ISS actually is right now (cross-check against
`https://wheretheiss.at` in a browser tab).

---

## Step 5 — Chart the daily summary (optional polish)

**Why:** this is where `/positions/summary` (and the `iss_daily_summary`
SQL view it's built on) actually gets used, turning raw rows into a trend
you can read at a glance.

**What to add:** a lightweight charting library — `recharts` is a
reasonable default for simple line/bar charts in React.

```bash
npm install recharts
```

Fetch `/positions/summary` the same way as Step 3, then render it with
`<LineChart>` (max altitude or avg velocity per day over the last 14 days)
— follow Recharts' own quickstart example for the exact JSX, since the
API shape depends on which columns `iss_daily_summary` exposes.

**Check your work:** confirm the chart has one point per day and the
values roughly match what you'd get running `SELECT * FROM
iss_daily_summary ORDER BY day DESC LIMIT 14;` directly in `psql`.

---

## Later extensions (not covered here)

- **Auth** — only relevant if you deploy this somewhere public; skip
  entirely for local/learning use.
- **WebSockets instead of polling** — nicer UX, more complexity; polling
  every 10s is plenty for something updating every 10 minutes at the
  source.
- **Deploying the frontend** — e.g. to Vercel/Netlify, pointing at a
  deployed FastAPI instance instead of `localhost:8000`. Out of scope
  until the pipeline itself is deployed somewhere other than your laptop.

## When you're done

- Update the README roadmap checkbox for "dashboard on top of the summary
  view."
- Consider whether `api.py` wants its own tests (same mocking approach as
  `pipeline.py` — see `docs/HARDENING_ROADMAP.md` Steps 4–6) once it has
  more than two endpoints.
