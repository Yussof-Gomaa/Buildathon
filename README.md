# Buildathon — Sayed Microbus

Django full-stack app for microbus driver income tracking (Sayed's route in Giza).

## Quick Start

### Prerequisites

- Python 3.10+

### Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations and seed demo data
python manage.py migrate
python manage.py seed_data

# Start the development server
python manage.py runserver
```

Visit http://127.0.0.1:8000/ for the passenger tablet UI.

### Deployment (gunicorn / production)

Most platforms (Railway, Render, Fly.io) split **build** and **start**. Do **not** use `./start.sh` as the start command unless bash + the script are available.

**Build command** (runs once on deploy):

```bash
bash build.sh
```

**Start command** (keep your existing one — works on all platforms):

```bash
gunicorn buildathon.wsgi:application --bind 0.0.0.0:$PORT
```

On platforms without `$PORT`, use `8000`:

```bash
gunicorn buildathon.wsgi:application --bind 0.0.0.0:8000
```

**Local one-liner** (creates venv, setup, run):

```bash
bash start.sh dev
```

**Why `./start.sh` failed in production:** the old script always ran `source .venv/bin/activate`, but PaaS hosts install Python packages globally — there is no `.venv` folder, so bash reported "no such file or directory".

If CSS looks unstyled after deploy, you almost certainly skipped `collectstatic`. Re-run it after any CSS/JS change, then restart gunicorn.

For local dev, `runserver` serves static automatically — no extra step needed.

### Demo login (Sayed)

| Field    | Value      |
|----------|------------|
| Username | `sayed`    |
| Password | `sayed123` |

## Test the full flow

Use two browser tabs (or two devices on the same network):

1. **Sayed's tablet** — http://127.0.0.1:8000/driver/login/
   - Log in as `sayed` / `sayed123`
   - Tap **بدء الرحلة** (Start ride)

2. **Passenger tablet** — http://127.0.0.1:8000/
   - Allow location access (or it will wait)
   - Pick a drop point → see fare → pay via InstaPay QR or Cash

3. **Back on Sayed's tablet** — passenger appears within ~3s (auto-polling)
   - For cash payments: tap **تحقق نقدي** to verify
   - Tap **نزل** when passenger gets off

4. **Expenses** — http://127.0.0.1:8000/driver/expense/
5. **Dashboard** — http://127.0.0.1:8000/driver/dashboard/ (income vs cost by period)

Admin review: http://127.0.0.1:8000/admin/

## Review seeded data

After `seed_data`, check in Django admin:

- **Routes** — "الطريق الرئيسي – الجيزة" (variable pricing) with 6 stops
- **Driver profiles** — Sayed linked to the route, capacity 14, InstaPay handle

No sample rides, passengers, or costs — dashboard shows only what you create during testing.

Re-run `python manage.py seed_data` to reset rides/passengers/costs while keeping route + user.

## Project Structure

```
Buildathon/
├── .venv/              # Python virtual environment
├── requirements.txt    # Python dependencies
├── manage.py           # Django management script
├── buildathon/         # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/               # Main app (models, views, admin, seed)
│   ├── models.py
│   ├── views.py
│   ├── services.py
│   ├── admin.py
│   ├── urls.py
│   ├── templates/core/
│   ├── static/core/
│   └── management/commands/seed_data.py
└── db.sqlite3          # SQLite database
```

## Models (phase 1)

| Model          | Purpose                                              |
|----------------|------------------------------------------------------|
| `Route`        | Fixed microbus path; FIXED or VARIABLE pricing       |
| `RouteStop`    | Ordered stops with per-stop cost increment           |
| `DriverProfile`| Sayed's route, capacity, InstaPay handle             |
| `Ride`         | Active trip session (start/end button grouping)      |
| `Passenger`    | One registration: pickup, drop, fare, payment        |
| `Cost`         | Expense with amortization period tag                 |

## UI routes (phase 2)

| URL | Who | Purpose |
|-----|-----|---------|
| `/` | Passenger | New passenger flow (waiting → pick drop → checkout) |
| `/driver/login/` | Sayed | Driver login |
| `/driver/` | Sayed | Active ride, passenger list, manual add |
| `/driver/expense/` | Sayed | Add expenses |
| `/driver/dashboard/` | Sayed | Income vs cost report |
