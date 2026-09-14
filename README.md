## Tech Stack

- Python
- Django
- Django REST Framework
- django-filter
- drf-spectacular
- SQLite (development)

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Somayeh-Bahari/invoiceflow-api.git
cd invoiceflow-api
```

### 2. Create a virtual environment

```bash
python -m venv env
```

### 3. Activate the virtual environment

Linux:

```bash
source env/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Run the development server

```bash
python manage.py runserver
```

The API will be available at:

```text
http://127.0.0.1:8000/api/
```

## API Documentation

Swagger UI:

```text
http://127.0.0.1:8000/api/docs/
```

OpenAPI Schema:

```text
http://127.0.0.1:8000/api/schema/
```

## Tests

Run the automated tests with:

```bash
python manage.py test core
```