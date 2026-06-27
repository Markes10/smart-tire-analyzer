# PostgreSQL Migration Guide

## Prerequisites
- PostgreSQL 14+ running
- Database created: `CREATE DATABASE smart_tire;`

## Step 1: Update .env
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/smart_tire
POSTGRES_ENABLED=true
```

## Step 2: Install extras
```bash
pip install asyncpg psycopg2-binary
```

## Step 3: Run migrations
```bash
python scripts/migrate_db.py --apply
```

## Note
The application auto-detects PostgreSQL from the DATABASE_URL.
SQLite `connect_args` will not be applied when using PostgreSQL.
