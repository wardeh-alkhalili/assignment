# DriverLog

Full-stack Hours of Service trip planner: **Django API** + **React** UI.

The app takes current / pickup / dropoff locations and cycle hours already used, then returns:

- A driving route on OpenStreetMap
- Fuel, 30-minute break, sleeper, pickup, and dropoff stops
- Filled FMCSA-style daily log sheets (one sheet per day)

Rules used (property-carrying, 70-hour / 8-day, no adverse conditions):

- 11-hour driving limit and 14-hour duty window
- 10-hour sleeper berth rest to reset 11/14
- 30-minute break after 8 hours of driving
- 70-hour / 8-day cycle, with a 34-hour restart if needed
- 1 hour on-duty for pickup and 1 hour for dropoff
- Fueling at least once every 1,000 miles

## Database

PostgreSQL is required. Create a local database (defaults match `settings.py`):

```bash
sudo -u postgres psql -c "CREATE USER driverlog WITH PASSWORD 'driverlog';"
sudo -u postgres psql -c "CREATE DATABASE driverlog OWNER driverlog;"
```

Override connection details with environment variables if needed: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.

## Run locally

```bash
cd driverlog
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

In another terminal:

```bash
cd driverlog/web
npm install
npm run dev
```

Open http://localhost:5173

The Vite dev server proxies `/api` to Django on port 8000.

## API

`POST /api/trips/plan/`

```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Indianapolis, IN",
  "dropoff_location": "Kansas City, MO",
  "current_cycle_used": 18
}
```

Maps use OpenStreetMap tiles, Nominatim geocoding, and the public OSRM router (no API key).

## Deploy (Vercel + Django host)

Vercel should host the **React app only**. Django and PostgreSQL do not run well on Vercel, so put the API on Render (or Railway) and point the frontend at it.

### 1. Push the project to GitHub

From the `driverlog` folder:

```bash
cd /home/ward/Documents/assigsmnet/driverlog
git init
git add .
git commit -m "DriverLog Django + React HOS planner"
```

Create a GitHub repo, then:

```bash
git remote add origin https://github.com/YOUR_USER/driverlog.git
git push -u origin main
```

### 2. Deploy the Django API (Render)

1. Go to [https://render.com](https://render.com) and create a **PostgreSQL** database. Copy the **Internal Database URL**.
2. Create a **Web Service** from the GitHub repo.
3. Settings:
   - **Root directory:** leave empty if the repo is `driverlog`
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

After deploy, check `https://your-service.onrender.com/api/health/` — it should return `{"ok": true}`.

### 3. Deploy the React app to Vercel

1. Go to [https://vercel.com/new](https://vercel.com/new) and import the same GitHub repo.
2. Configure the project:
   - **Root Directory:** `web`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Add an environment variable:
   - **Name:** `VITE_API_BASE`
   - **Value:** `https://your-service.onrender.com` (no trailing slash)
4. Deploy.

Open the Vercel URL. The UI will call your Django API for routes and ELD logs.

If you change `VITE_API_BASE` later, you must **redeploy** the frontend. Vite bakes that value in at build time.

