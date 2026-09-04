# MyDuka Backend

MyDuka Backend is the Django REST API for a multi-tenant retail and inventory platform. A `merchant` owns one or more stores, invites `admin` users, and those admins create `clerk` users who record stock movements, spoilage, sales, and supply requests. All inventory and reporting data is scoped to the requesting user’s store.

## Overview

This backend is built to support:

- merchant-owned store management
- admin and clerk role-based access
- JWT authentication and authorization
- inventory tracking for products and stock movements
- stock received, sold, and spoiled events
- unpaid payment tracking and payment status updates
- reporting dashboards for inventory and store performance
- OpenAPI/Swagger documentation

## Tech stack

- Python 3.11+
- Django 6.1
- Django REST Framework
- PostgreSQL
- drf-spectacular for OpenAPI and Swagger UI
- djangorestframework-simplejwt for token authentication
- CORS support for frontend integrations
- Docker Compose for local development and database provisioning

## Project structure

```text
Myduka-backend/
├── apps/
│   ├── accounts/
│   │   ├── models.py
│   │   ├── permissions.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── inventory/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   └── __init__.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── reports/
│   ├── services/
│   ├── urls.py
│   ├── views.py
│   └── serializers.py
├── .env.example
├── .env
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── manage.py
├── Pipfile
├── README.md
├── render.yaml
├── requirements.txt
└── .coveragerc
```

## Prerequisites

Before starting the project, ensure you have:

- Python 3.11 or later
- PostgreSQL running locally, or Docker installed for the bundled database
- pip or pipenv
- a terminal with access to the repository

## Environment configuration

The project reads configuration from environment variables using Django’s `.env` file. A starter file is provided at `.env.example`.

### Example `.env` file

```env
DEBUG=True
SECRET_KEY=replace-with-a-secure-secret

# Option A: use explicit DB variables
DB_NAME=myduka
DB_USER=myduka_user
DB_PASSWORD=myduka_password
DB_HOST=localhost
DB_PORT=5432

# Option B: use a single DATABASE_URL instead
# DATABASE_URL=postgresql://myduka_user:myduka_password@localhost:5432/myduka

# Optional: allow frontend origins during local development
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key for signing sessions and tokens |
| `DEBUG` | No | Enables Django debug mode in development |
| `DB_NAME` | No, unless using `DATABASE_URL` | PostgreSQL database name |
| `DB_USER` | No, unless using `DATABASE_URL` | PostgreSQL user |
| `DB_PASSWORD` | No, unless using `DATABASE_URL` | PostgreSQL password |
| `DB_HOST` | No, unless using `DATABASE_URL` | PostgreSQL host |
| `DB_PORT` | No, unless using `DATABASE_URL` | PostgreSQL port |
| `DATABASE_URL` | No | Full PostgreSQL connection string; takes precedence when set |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated frontend origins allowed by Django CORS |
| `ALLOWED_HOSTS` | No | Extra hostnames accepted by Django |

## Running the app locally

### Option 1: Docker (recommended)

This is the easiest path for local development because it starts both PostgreSQL and the Django app together.

```bash
cp .env.example .env
docker compose up --build
```

The project will run with:

- PostgreSQL: `localhost:5432`
- Django API: `http://localhost:8000`

The Docker setup uses the `web` service defined in `docker-compose.yml`, which runs the Django development server and automatically calls `python manage.py migrate` via the `entrypoint.sh` script.

### Option 2: Local virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

If you are not using Docker, make sure PostgreSQL is running and that your environment variables match the database you want to connect to.

## Authentication and roles

The API uses JWT authentication via Django REST Framework Simple JWT.

### User roles

- `merchant`: owns the store and can manage the business and team
- `admin`: manages store operations and invites or manages clerks
- `clerk`: records stock movement, sales, spoilage, and supply requests

### Authentication flow

1. Create a merchant user directly in the database or through a one-time seed step.
2. Log in with `POST /api/auth/login` to get an access token.
3. Use the token as:

```http
Authorization: Bearer <access_token>
```

4. Use the role-based endpoints to manage users and store operations.

### Public endpoints

These do not require a JWT token:

- `GET /api/auth/health/`
- `POST /api/auth/login`
- `POST /api/auth/register-admin`
- `GET /api/auth/invitations/<token>`

### Protected endpoints

All other API routes require authentication.

## API routes

### Auth and users

```text
GET    /api/auth/health/
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
GET    /api/auth/invitations
POST   /api/auth/invitations
GET    /api/auth/invitations/<token>
POST   /api/auth/register-admin
GET    /api/auth/admins
POST   /api/auth/admins/<user_id>/<action>
GET    /api/auth/clerks
POST   /api/auth/clerks/<user_id>/<action>
```

Notes:

- Admins are usually invited by merchants.
- A pending invitation is exchanged for an admin account through `register-admin`.
- A merchant or admin can manage related users within the same store context.

### Inventory

```text
GET    /api/inventory
GET    /api/inventory/<product_id>
GET    /api/inventory/stats
POST   /api/stock/receive
GET    /api/stock/received
POST   /api/stock/sell
GET    /api/spoilage
POST   /api/spoilage
GET    /api/supply-requests
POST   /api/supply-requests
PUT    /api/supply-requests/<request_id>
GET    /api/payments/unpaid
PATCH  /api/payments/<transaction_id>/status
```

These endpoints are centered on product records, receiving stock, sales, spoilage logging, supply requests, and payment tracking.

### Reports

```text
GET    /api/v1/reports/inventory/
GET    /api/v1/reports/products/
GET    /api/v1/reports/stores/
GET    /api/v1/reports/clerks/
```

These report endpoints compute aggregate inventory and performance data from the underlying transaction and spoilage records.

## API documentation

The project includes OpenAPI support and a Swagger UI dashboard.

- Swagger UI: `http://localhost:8000/api/docs/`
- Schema: `http://localhost:8000/api/schema/`
- API index: `http://localhost:8000/api/`

## Creating the first merchant and store

There is no public merchant sign-up endpoint. The initial merchant and store are usually created directly in the database and then the merchant invites admins through the API.

```bash
python manage.py shell -c "
from apps.accounts.models import User, Store
merchant = User.objects.create_user(
    email='owner@example.com',
    password='changeme123',
    name='Owner',
    role=User.Role.MERCHANT,
)
store = Store.objects.create(name='My Shop', merchant=merchant)
merchant.store = store
merchant.save(update_fields=['store'])
print(f'Merchant: {merchant.email}')
print(f'Store: {store.name}')
"
```

After this, the flow is:

1. `POST /api/auth/login` with the merchant credentials
2. `POST /api/auth/invitations` to invite an admin
3. The admin completes registration via `POST /api/auth/register-admin`
4. The admin can then create clerks using the clerk management endpoint

## Deployment on Render

The repository contains a `render.yaml` blueprint for deploy-on-click setup on Render.

### What Render config does

- creates a Postgres database
- creates a Docker-based web service
- sets `SECRET_KEY` automatically
- sets `DEBUG=False`
- injects `DATABASE_URL` from the database resource
- exposes `CORS_ALLOWED_ORIGINS` as a runtime variable you can set manually

### Render setup steps

1. Push the repository to GitHub.
2. In Render, choose “New” → “Blueprint” and select the repository.
3. Render reads `render.yaml` and creates the database and web service.
4. After the initial deployment, set `CORS_ALLOWED_ORIGINS` to your frontend domain, such as:

```text
https://myduka.vercel.app
```

5. Deploy the app and confirm the health endpoint:

```text
https://<your-service>.onrender.com/api/auth/health/
```

> The app executes `migrate` and `collectstatic` in `entrypoint.sh` before starting Gunicorn.

## Running tests

Use Django’s test runner:

```bash
python manage.py test
```

For coverage, use:

```bash
coverage run manage.py test
coverage report -m
```

## Data model summary

The system centers around a store-owned inventory model:

- `Store` owns a business context and its users
- `User` represents a merchant, admin, or clerk
- `Invitation` is used to onboard people into a store
- `Product` represents each item in the catalog
- `StockTransaction` records stock received, stock sold, spoilage, and adjustments
- `SpoilageRecord` tracks quantity lost or damaged
- `SupplyRequest` records procurement requests

## Notes and current assumptions

- Merchant self-registration is intentionally not exposed publicly; a merchant account is created directly in the system.
- Inventory and reporting data is intentionally scoped to the current store so no cross-store leakage occurs.
- Payment tracking is a store-level operational flag rather than a full external payment processor integration.
- Reports are generated live from stock movement and spoilage data rather than a separate analytics table.

## Troubleshooting

### PostgreSQL connection errors

Check that:

- PostgreSQL is running
- your `.env` values match the database credentials
- the server is listening on the expected host/port

### Django app does not start

Run:

```bash
python manage.py check
python manage.py migrate
```

### CORS issues from the frontend

Add your frontend domain to `CORS_ALLOWED_ORIGINS` in `.env`:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Docker issues

If ports are already in use:

- stop the process using the port, or
- change the published host port in `docker-compose.yml`

## License

This project currently does not include a dedicated license file. If you intend to distribute or reuse it in a production setting, add a formal license before publication.

## Contributors
- Kelvin Tullo
- Gabriel Ngige
- Elias Kosh
- Joshua Mbili
- George Njenga