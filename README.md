# Buildathon

A Django web application.

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

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

Visit http://127.0.0.1:8000/ in your browser.

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
└── db.sqlite3          # SQLite database (created after migrate)
```
