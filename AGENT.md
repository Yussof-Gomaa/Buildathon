# AGENT.md — Sayed Microbus (Buildathon)

Onboarding doc for AI agents and developers joining this repo mid-hackathon.

---

## Problem statement

**Sayed** is a 47-year-old microbus driver on a fixed route in Giza, six days a week. Fares shift with fuel, traffic, time of day, and what passengers will pay. At end of day, income goes in one pocket; diesel, repairs, and owner payments come out of another. He has no record of what he actually earns — only a feeling for whether the week was good.

**What's invisible:** daily income vs. cost — he can't tell a good week from a lucky one.

**The cost:** he works harder every year with no way to prove it's working.

**Our solution:** two device interfaces on one Django full-stack app (SQLite in-repo):

1. **Passenger UI** — mobile phone; self-service boarding/checkout.
2. **Sayed UI** — tablet on the back of his chair; approve actions, manage the car, log expenses, view dashboard.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Framework | Django 6.0.7 (full-stack — templates + views in same repo) |
| Database | SQLite (`db.sqlite3` at repo root) |
| Auth (Sayed) | Django built-in `User` + `login_required` / staff access |
| Python | 3.10+ (project venv uses 3.14) |
| Deploy helper | gunicorn (in `requirements.txt`) |

**Not yet added:** REST framework, separate frontend, Celery, etc. Keep it minimal.

---

## UI conventions (apply to all future frontend work)

- **Icons first** — primary actions communicated via icons, Arabic text as labels.
- **Arabic-first** — all user-facing copy in Arabic.
- **Font:** Thmaniyah (load in base template when building UI).
- **RTL** — set `dir="rtl"` and `lang="ar"` on HTML root.
- Settings already use `LANGUAGE_CODE = 'ar'` and `TIME_ZONE = 'Africa/Cairo'`.

---

## Architecture decisions (locked in — do not rebuild without asking)

These were confirmed with the product owner before phase 1:

| Decision | Choice |
|----------|--------|
| Pickup stop | **Auto-detect** nearest `RouteStop` to device GPS (haversine); raw lat/lng still stored on `Passenger` |
| Variable fare | **Sum** each `RouteStop.cost` for stops with `order > pickup.order` AND `order <= drop.order` |
| Fixed fare | Every passenger pays `Route.fixed_price` regardless of stops |
| Cost `period` | **Amortization tag** — e.g. `MONTH` cost is spread evenly across days in that month via `daily_amortized_amount` |
| Sayed auth | **Django auth** — `User` with `is_staff=True`; login for driver portal |
| Car capacity | `DriverProfile.max_capacity` (default 14) — no separate `Car` model for now |
| App structure | Single Django app `core` — avoid splitting into many apps until necessary |

---

## Current implementation status

### Done (phase 1)

- [x] `core` app with all models
- [x] Migrations (`core/migrations/0001_initial.py`)
- [x] Django admin for all models (review surface)
- [x] `seed_data` management command (idempotent)
- [x] README with quick start

### Not done yet (phase 2+)

- [ ] Passenger mobile UI (`/passenger/` or similar)
- [ ] Sayed driver UI — live operations (`/driver/`)
- [ ] Sayed dashboard — income vs costs, period filters, maybe cash vs savings plan
- [ ] Views, URLs, templates
- [ ] Thmaniyah font + icon set
- [ ] InstaPay QR generation on checkout
- [ ] Browser geolocation API integration
- [ ] Real-time sync between passenger tablet and Sayed tablet (can be simple: shared DB + page refresh or HTMX polling for hackathon)

**Only URL today:** `/admin/` — see `buildathon/urls.py`.

---

## Repository layout

```
Buildathon/
├── AGENT.md                 ← you are here
├── README.md                ← human quick start
├── manage.py
├── requirements.txt
├── db.sqlite3               ← SQLite (gitignored or local)
├── buildathon/              ← Django project settings
│   ├── settings.py          ← INSTALLED_APPS includes 'core', ar/Cairo TZ
│   └── urls.py              ← only admin registered so far
└── core/                    ← all domain logic lives here
    ├── models.py            ← Route, RouteStop, DriverProfile, Ride, Passenger, Cost
    ├── admin.py
    ├── views.py             ← empty/stub — add views here
    ├── management/commands/
    │   └── seed_data.py
    └── migrations/
```

---

## Quick start (for agents)

```bash
cd /path/to/Buildathon
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

**Demo login:** `sayed` / `sayed123` → http://127.0.0.1:8000/admin/

Re-run `seed_data` safely — uses `get_or_create`.

---

## Data model

### ERD (conceptual)

```mermaid
erDiagram
    User ||--o| DriverProfile : has
    User ||--o{ Ride : drives
    User ||--o{ Cost : incurs
    Route ||--o{ RouteStop : has
    Route ||--o{ DriverProfile : assigned_to
    Route ||--o{ Ride : follows
    Ride ||--o{ Passenger : carries
    RouteStop ||--o{ Passenger : pickup
    RouteStop ||--o{ Passenger : drop

    Route {
        string name
        enum price_type FIXED_VARIABLE
        decimal fixed_price nullable
        bool is_active
    }
    RouteStop {
        int order unique_per_route
        string name
        decimal cost
        float lat
        float lng
    }
    DriverProfile {
        int max_capacity
        string instapay_handle
    }
    Ride {
        enum status ACTIVE_COMPLETED
        datetime started_at
        datetime ended_at nullable
    }
    Passenger {
        float pickup_lat pickup_lng
        decimal fare
        enum payment_method CASH_INSTAPAY
        enum payment_status PENDING_PAID
        enum ride_status IN_CAR_DROPPED_OFF_CANCELLED
    }
    Cost {
        decimal amount
        enum period ONE_OFF_DAY_WEEK_MONTH_YEAR
        date date_incurred
        string note
    }
```

### Models reference (`core/models.py`)

#### `Route`
- `price_type`: `FIXED` | `VARIABLE`
- `fixed_price`: required when FIXED, must be null when VARIABLE
- **`nearest_stop(lat, lng)`** — returns closest `RouteStop` by haversine km
- **`compute_fare(pickup_stop, drop_stop)`** — fare logic (see below)

#### `RouteStop`
- `order` — sequence along route; **unique per route**
- `cost` — fare increment for arriving at this stop (first stop often `0.00`)
- `lat`, `lng` — for nearest-stop detection

#### `DriverProfile`
- OneToOne → `auth.User`
- `route`, `max_capacity`, `instapay_handle` (string for QR payload later)

#### `Ride`
- Groups passenger registrations between Sayed's **Start** and **End** buttons
- `status`: `ACTIVE` | `COMPLETED`
- **`active_passenger_count`** — passengers with `ride_status=IN_CAR` (for capacity checks)

#### `Passenger`
- Belongs to one `Ride`
- `pickup_stop` / `drop_stop` — FKs to `RouteStop`
- `pickup_lat`, `pickup_lng` — raw GPS from passenger device
- `fare` — **snapshotted at creation** via `route.compute_fare()`
- `payment_method`: `CASH` | `INSTAPAY`
- `payment_status`: `PENDING` | `PAID` — auto-set in `save()`:
  - InstaPay → `PAID` immediately
  - Cash → `PENDING` until Sayed verifies
- `ride_status`: `IN_CAR` | `DROPPED_OFF` | `CANCELLED`

#### `Cost`
- `period`: amortization tag — `ONE_OFF` | `DAY` | `WEEK` | `MONTH` | `YEAR`
- `date_incurred` — anchor date for window calculation
- **`period_window()`** → `(start_date, end_date)`
- **`daily_amortized_amount`** → `amount / days_in_window`

---

## Business logic

### Fare calculation

**VARIABLE route** (seeded route uses this):

```
fare = sum(stop.cost for stop in route.stops
           where pickup.order < stop.order <= drop.order)
```

**Examples** (seeded stops):

| Pickup | Drop | Stops summed | Fare |
|--------|------|--------------|------|
| ميدان الجيزة (1) | فيصل (3) | 2+3 | 7 EGP |
| ميدان الجيزة (1) | الدقي (4) | 2+3+4 | 12 EGP |
| شارع الهرم (2) | المهندسين (5) | 3+4+5 | 13 EGP |

**FIXED route:** `fare = route.fixed_price` for any valid pickup/drop pair.

**Validation:** `drop_stop.order` must be **strictly greater** than `pickup_stop.order`.

### Passenger flow (to implement)

```
1. New passenger page
2. Get device GPS (browser Geolocation API)
3. Find nearest RouteStop on active route → pickup_stop
4. User picks drop_stop from list (only stops after pickup)
5. Show fare preview (route.compute_fare)
6. Checkout:
   - InstaPay → show QR from driver.instapay_handle → mark PAID
   - Cash → button "سأدفع نقداً" → mark PENDING, Sayed verifies later
7. Create Passenger on active Ride (must exist and be ACTIVE)
8. Redirect immediately back to step 1
```

**Capacity:** before creating passenger, check `ride.active_passenger_count < driver.max_capacity`.

**Active ride:** passenger UI needs an active `Ride` with `status=ACTIVE`. Sayed starts/ends rides from his UI.

### Sayed operations flow (to implement)

**During the day:**
- Start ride / End ride
- View passengers in car (IN_CAR)
- Approve cash payments (`payment_status` PENDING → PAID)
- Manually create passenger (skip GPS or override pickup)
- Mark passenger dropped off / cancel / free the car
- Add expense (`Cost` form: amount, period, note)

**Dashboard (second section of Sayed portal):**
- Income for period (sum of `Passenger.fare` where paid)
- Costs for period (use `daily_amortized_amount` × overlapping days)
- Net = income − costs
- Period filters: today, yesterday, last week, month, year, custom range
- **Maybe later:** cash vs savings plan

### Cost amortization (dashboard math)

For a query range `[query_start, query_end]`:

```python
for cost in driver.costs.all():
    win_start, win_end = cost.period_window()
    overlap_start = max(win_start, query_start)
    overlap_end = min(win_end, query_end)
    if overlap_start <= overlap_end:
        overlap_days = (overlap_end - overlap_start).days + 1
        total += cost.daily_amortized_amount * overlap_days
```

---

## Seeded data (`python manage.py seed_data`)

| Entity | Details |
|--------|---------|
| Route | `الطريق الرئيسي – الجيزة` — VARIABLE |
| Stops | 6 stops from ميدان الجيزة → أبو النمرس (see `seed_data.py`) |
| User | `sayed` / `sayed123`, `is_staff=True`, name سيد السائق |
| DriverProfile | route above, capacity 14, instapay `sayed.microbus@instapay` |
| Costs | ديزل 350 EGP (DAY), دفعة للمالك 3000 EGP (MONTH) |
| Sample ride | 1 COMPLETED ride, 3 passengers (fare sanity check) |

---

## Planned URL structure (suggestion — not implemented)

| Path | Audience | Purpose |
|------|----------|---------|
| `/passenger/` | Passenger phone | New passenger → drop → checkout loop |
| `/driver/` | Sayed tablet | Login required; live ops |
| `/driver/dashboard/` | Sayed | Income vs costs |
| `/admin/` | Dev/review | Django admin (exists) |

Use Django session auth for `/driver/*`. Passenger flow can be open (no login) — device is physically in the car.

---

## Implementation guidelines for future agents

1. **Minimize scope** — hackathon speed; don't add models unless necessary.
2. **Reuse model methods** — always call `route.compute_fare()` and `route.nearest_stop()`; don't duplicate fare logic in views/JS.
3. **Snapshot fare** on `Passenger` creation — prices may change later.
4. **One active ride** — enforce at most one `Ride` with `status=ACTIVE` per driver (add constraint in view or model clean).
5. **Templates** — put in `core/templates/core/`; add `DIRS` or use app templates.
6. **Static** — Thmaniyah font in `core/static/core/fonts/`; icons via SVG or a lightweight icon font.
7. **No separate API** unless needed — Django form posts + HTMX is fine for two tablets on same network.
8. **Don't edit** `.cursor/plans/` plan files.
9. **Don't commit** unless user asks.
10. **Ask before rebuilding** core decisions in the table above.

---

## Key files to read first

1. `core/models.py` — all domain logic
2. `core/management/commands/seed_data.py` — example data + fare examples
3. `core/admin.py` — field names for forms
4. `buildathon/settings.py` — locale, installed apps
5. `buildathon/urls.py` — wire new routes here

---

## Dependencies (`requirements.txt`)

```
Django==6.0.7
gunicorn==26.0.0
asgiref, sqlparse  # Django deps
```

For QR codes on InstaPay checkout, you'll likely add `qrcode` or generate client-side — not installed yet.

---

## Sanity-check commands

```bash
# Verify fare math
python manage.py shell -c "
from core.models import Route
r = Route.objects.first()
stops = list(r.stops.order_by('order'))
print(r.compute_fare(stops[0], stops[2]))  # expect 7
print(r.compute_fare(stops[0], stops[3]))  # expect 12
"

# Count seeded records
python manage.py shell -c "
from core.models import *
print('Routes:', Route.objects.count())
print('Passengers:', Passenger.objects.count())
print('Costs:', Cost.objects.count())
"
```

---

## Glossary

| Arabic | English | Model/field |
|--------|---------|-------------|
| مسار | Route | `Route` |
| محطة | Stop | `RouteStop` |
| رحلة | Trip session | `Ride` |
| راكب | Passenger | `Passenger` |
| مصروف | Expense | `Cost` |
| نقدي | Cash | `PaymentMethod.CASH` |
| إنستاباي | InstaPay | `PaymentMethod.INSTAPAY` |
| ثابت / متغير | Fixed / Variable pricing | `PriceType` |

---

*Last updated: phase 1 complete (models + admin + seed). Frontend not started.*
