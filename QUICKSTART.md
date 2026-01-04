# FastAPI Backend - Quick Start Guide

## 🚀 Quick Start (Automated Setup)

### Option 1: Use the Setup Script (Easiest)

Simply run the automated setup script:

```bash
cd backend
.\setup.bat
```

This will:
- Create a virtual environment
- Install all dependencies
- Copy .env.example to .env
- Set up the database (optional)

### Option 2: Manual Setup

If you prefer to set up manually:

```bash
cd backend

# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
copy .env.example .env
# Then edit .env with your actual values

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload
```

## ⚙️ Configuration

### Important: Update .env

Before running the backend, you MUST update these values in `.env`:

1. **DATABASE_URL**: Your PostgreSQL connection string
   - For Supabase: `postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres`
   - For local PostgreSQL: `postgresql://postgres:password@localhost:5432/heyllo_db`

2. **SECRET_KEY**: Generate a secure random key
   ```bash
   # Using Python:
   python -c "import secrets; print(secrets.token_hex(32))"
   
   # Or using OpenSSL:
   openssl rand -hex 32
   ```

3. **CORS_ORIGINS**: Your frontend URL (default: `http://localhost:5173`)

## 🎯 Running the Backend

```bash
# Make sure you're in the backend directory
cd backend

# Activate virtual environment (if not already active)
.\venv\Scripts\activate

# Start the server
uvicorn app.main:app --reload --port 8000

# Or use Python directly
python -m app.main
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs 
- **ReDoc**: http://localhost:8000/redoc

## 📡 Testing the API

### 1. Open Swagger UI
Navigate to http://localhost:8000/docs

### 2. Register a User
```json
POST /api/auth/register
{
  "email": "test@example.com",
  "password": "test123",
  "full_name": "Test User"
}
```

### 3. Login
```json
POST /api/auth/login
{
  "email": "test@example.com",
  "password": "test123"
}
```

Copy the `access_token` from the response.

### 4. Authorize in Swagger
- Click the "Authorize" button at the top
- Paste your access token
- Now you can test all protected endpoints!

## 🗄️ Database

The backend uses PostgreSQL with SQLAlchemy ORM. All database operations are managed through Alembic migrations.

### Common Database Commands:

```bash
# Create a new migration (auto-generate from model changes)
alembic revision --autogenerate -m "Description of changes"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## 📝 Available Endpoints

### Authentication
- `POST /api/auth/register` - Register
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh token

### Leads
- `GET /api/leads` - List leads
- `POST /api/leads` - Create lead
- `PUT /api/leads/{id}` - Update lead
- `POST /api/leads/import/csv` - Import CSV
- `GET /api/leads/export/csv` - Export CSV

### Campaigns
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `GET /api/campaigns/{id}/stats` - Get statistics

### Calls
- `GET /api/calls` - List calls
- `POST /api/calls` - Initiate call
- `GET /api/calls/active` - Get active calls
- `GET /api/calls/stats` - Get call statistics

### Analytics
- `GET /api/analytics/dashboard` - Dashboard KPIs
- `GET /api/analytics/calls-overtime` - Time series data
- `GET /api/analytics/outcomes` - Outcome distribution

## 🔧 Troubleshooting

### "ModuleNotFoundError"
Make sure you're in the virtual environment:
```bash
.\venv\Scripts\activate
```

### "Database connection failed"
Check your `DATABASE_URL` in `.env`:
- Verify the username, password, host, and database name
- Ensure PostgreSQL is running
- For Supabase, check the connection pooler port (5432)

### "Alembic can't import app.config"
Make sure you're in the `backend/` directory when running Alembic commands.

### Port 8000 already in use
Change the port:
```bash
uvicorn app.main:app --reload --port 8001
```

## 🎉 Next Steps

1. ✅ **Backend is running** at http://localhost:8000
2. 📖 **Test APIs** using Swagger at http://localhost:8000/docs
3. 🔗 **Connect Frontend** - Update your React app to call the new API endpoints
4. 🚀 **Deploy** - When ready, deploy to a production server

---

**Need help?** Check the full README.md for detailed documentation.
