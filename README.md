# Heyllo.ai Call Center Backend

FastAPI backend for the Heyllo.ai Call Center Management System.

## Features

- **Authentication**: JWT-based authentication with refresh tokens
- **Leads Management**: CRUD operations, CSV import/export, search and filtering
- **Campaigns**: Campaign orchestration, status tracking, and statistics
- **Calls**: Real-time call management, queue tracking, and analytics
- **Analytics**: Dashboard KPIs, time series data, and performance metrics
- **Multi-tenancy**: Full tenant isolation for all data

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens (python-jose)
- **Password Hashing**: bcrypt (passlib)
- **Migrations**: Alembic

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and update with your settings:

```bash
copy .env.example .env
```

**IMPORTANT**: Update the following in `.env`:
- `DATABASE_URL`: Your PostgreSQL connection string
- `SECRET_KEY`: Generate a secure random key (use `openssl rand -hex 32`)

### 4. Initialize Database

```bash
# Create database tables
alembic upgrade head
```

### 5. Run the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Or use Python directly
python -m app.main
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout

### Leads
- `GET /api/leads` - List leads (with filters & pagination)
- `GET /api/leads/{id}` - Get lead details
- `POST /api/leads` - Create lead
- `PUT /api/leads/{id}` - Update lead
- `PATCH /api/leads/{id}/status` - Update lead status
- `DELETE /api/leads/{id}` - Delete lead
- `POST /api/leads/import/csv` - Import leads from CSV
- `GET /api/leads/export/csv` - Export leads to CSV
- `GET /api/leads/{id}/calls` - Get lead call history

### Campaigns
- `GET /api/campaigns` - List campaigns
- `GET /api/campaigns/{id}` - Get campaign details
- `POST /api/campaigns` - Create campaign
- `PUT /api/campaigns/{id}` - Update campaign
- `PATCH /api/campaigns/{id}/status` - Update campaign status
- `DELETE /api/campaigns/{id}` - Delete campaign
- `GET /api/campaigns/{id}/stats` - Get campaign statistics

### Calls
- `GET /api/calls` - List calls (with filters)
- `GET /api/calls/{id}` - Get call details
- `POST /api/calls` - Initiate new call
- `PATCH /api/calls/{id}/status` - Update call status
- `GET /api/calls/active` - Get active calls
- `GET /api/calls/queue` - Get queued calls
- `GET /api/calls/stats` - Get call statistics

### Analytics
- `GET /api/analytics/dashboard` - Dashboard KPIs
- `GET /api/analytics/calls-overtime` - Time series call data
- `GET /api/analytics/outcomes` - Call outcome distribution
- `GET /api/analytics/campaigns-performance` - Campaign metrics

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

## Testing the API

### Using Swagger UI
1. Navigate to http://localhost:8000/docs
2. Click "Authorize" and enter your JWT token
3. Test endpoints interactively

### Using curl

```bash
# Register a user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Use the access_token from login response for authenticated requests
TOKEN="your_access_token_here"

# Get leads
curl -X GET http://localhost:8000/api/leads \
  -H "Authorization: Bearer $TOKEN"
```

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/      # API endpoint handlers
│   ├── models/          # SQLAlchemy database models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── utils/           # Utility functions (security, etc.)
│   ├── config.py        # Configuration management
│   ├── database.py      # Database connection
│   ├── dependencies.py  # Shared dependencies
│   └── main.py          # FastAPI app entry point
├── alembic/             # Database migrations
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
└── README.md           # This file
```

## Development

- The API uses **JWT tokens** for authentication
- All endpoints require `tenant_id` isolation
- Use the Swagger UI at `/docs` for interactive testing
- Database changes require Alembic migrations

## Deployment

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Use a production-grade database
3. Set a strong `SECRET_KEY`
4. Configure proper CORS origins
5. Use a production ASGI server (e.g., Gunicorn with Uvicorn workers)

```bash
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
