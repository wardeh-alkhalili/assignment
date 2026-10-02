# DriverLog

Full-stack Hours of Service trip planner: **Django API** + **React** UI.

The app takes current, pickup, and dropoff locations plus cycle hours already used, then returns:

- A driving route on OpenStreetMap
- Fuel, 30-minute break, sleeper, 34-hour restart, pickup, and dropoff stops
- Filled FMCSA-style daily log sheets (one sheet per day)

Each successful plan is stored on the `Trip` model (`current_location`, `pickup_location`, `dropoff_location`, `current_cycle_used`, `result`).

Rules implemented in `trips/services/hos.py` (property-carrying, no adverse-conditions exception):

- 11-hour driving limit and 14-hour duty window
- 10-hour sleeper berth rest resets the 11-hour and 14-hour clocks
- 30-minute off-duty break after 8 hours of driving
- 70-hour cycle, tracked as a running total of driving and on-duty time, reset by a 34-hour off-duty restart
- 1 hour on-duty for pickup and 1 hour for dropoff
- Fuel stop of 30 minutes on-duty at least once every 1,000 miles
- Duty times snap to 15-minute increments
- The trip starts at 06:00 on the current date
- Each log sheet is padded with off-duty time so the four status rows total 24 hours

The daily-log recap uses that running cycle total:

- **A** — cycle hours used at the end of the day
- **B** — hours left (`70 − A`)
- **C** — on-duty hours over the last 5 log days

## Database

PostgreSQL is required. Defaults in `driverlog/settings.py`:

| Variable | Default |
|---|---|
| `POSTGRES_DB` | `driverlog` |
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | `1234` |
| `POSTGRES_HOST` | `127.0.0.1` |
| `POSTGRES_PORT` | `5432` |

Create the database the defaults expect:

```bash
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE driverlog;"
```

If `DATABASE_URL` is set, it replaces those settings through `dj-database-url`. `POSTGRES_SSL` defaults to `true` in that case.

## Run locally

From the repository root (the folder that contains `manage.py`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

In another terminal:

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173

The Vite dev server listens on port 5173 and proxies `/api` to `http://127.0.0.1:8000`. Leave `VITE_API_BASE` unset locally so the UI calls that proxy.

## API

`GET /api/health/`

```json
{"ok": true, "service": "driverlog"}
```

`GET /api/geocode/?q=`

Returns up to 5 Nominatim suggestions when `q` is at least 3 characters. The trip form calls this while typing.

`POST /api/trips/plan/`

```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Indianapolis, IN",
  "dropoff_location": "Kansas City, MO",
  "current_cycle_used": 18
}
```

`current_cycle_used` must be a number from 0 to 70. All three locations are required. Errors come back as `{"error": "..."}` with status 400, 500, or 502.

A successful response includes `inputs`, `locations`, `route` (`geometry`, `legs`, `stops`), `summary`, `events`, `timeline`, and `daily_logs`.

Maps use OpenStreetMap tiles (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`). Places are geocoded with Nominatim (`https://nominatim.openstreetmap.org/search`), with a 1-second pause between the three trip lookups. Driving geometry and durations come from the public OSRM router (`https://router.project-osrm.org/route/v1/driving`). No API key is used. If a leg is longer than 0.2 miles and OSRM reports under 0.05 hours, duration is replaced with miles ÷ 55.

The form also loads two samples: Midwest haul (Chicago → Indianapolis → Kansas City, 18 hours used) and coast to coast (Newark → Philadelphia → Los Angeles, 8 hours used).

## Deploy (Vercel + Django host)

Vercel hosts the React app only. Run Django and PostgreSQL on Render (or Railway) and point the frontend at that API.

### 1. Deploy the Django API (Render)

1. Create a **PostgreSQL** database and copy its connection URL.
2. Create a **Web Service** from this repository.
3. Settings:
   - **Root directory:** the repository root (where `manage.py` is)
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt && python manage.py migrate`
   - **Start command:** `gunicorn driverlog.wsgi:application`
4. Environment variables:

| Name | Value |
|---|---|
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | a long random string |
| `DJANGO_ALLOWED_HOSTS` | your-service.onrender.com |
| `DATABASE_URL` | the Render Postgres URL |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.vercel.app` |

`DJANGO_DEBUG` defaults to `true` when unset. `DJANGO_ALLOWED_HOSTS` defaults to `*`. CORS allows every origin.

After deploy, `https://your-service.onrender.com/api/health/` returns `{"ok": true, "service": "driverlog"}`.

### 2. Deploy the React app to Vercel

1. Import this repository at [https://vercel.com/new](https://vercel.com/new).
2. Configure the project:
   - **Root Directory:** `web`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Environment variable (see `web/.env.example`):
   - **Name:** `VITE_API_BASE`
   - **Value:** `https://your-service.onrender.com` (no trailing slash)

The UI calls `${VITE_API_BASE}/api/trips/plan/` and `${VITE_API_BASE}/api/geocode/`. Changing `VITE_API_BASE` requires a new frontend deploy, because Vite bakes it in at build time.
