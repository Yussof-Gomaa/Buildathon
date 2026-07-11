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

Django does **not** serve CSS/JS when running with gunicorn unless you collect static files first. This project uses **WhiteNoise** for that.

**One command:**

```bash
./start.sh
```

Or manually:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py collectstatic --noinput   # required before deploy
gunicorn buildathon.wsgi:application --bind 0.0.0.0:8000
```

For local dev: `./start.sh dev` (uses `runserver` instead of gunicorn).

Optional env vars: `PORT=8080 ./start.sh`

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
- **Rides** — one completed sample ride with 3 passengers (fare math sanity check)
- **Costs** — diesel (DAY period) and owner payment (MONTH period)

Re-run `python manage.py seed_data` anytime — it is idempotent (`get_or_create`).

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
