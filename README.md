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

Visit http://127.0.0.1:8000/admin/ to review models and seeded data.

### Demo login (Sayed / Django admin)

| Field    | Value      |
|----------|------------|
| Username | `sayed`    |
| Password | `sayed123` |

Sayed's user has `is_staff=True` so he can access `/admin/` for the driver dashboard during the hackathon.

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
├── core/               # Main app (models, admin, seed)
│   ├── models.py
│   ├── admin.py
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
