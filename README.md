# Aeiouly-be

## Project Setup Guide

### 1. Create a virtual environment (recommended)

```bash
python -m venv .venv
# Activate the virtual environment:
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your .env file

```bash
cp .env.example .env
# Or manually create a .env file and fill in the environment variables as in .env.example
```

### 4. Initialize and migrate the database

```bash
alembic upgrade head
```

### 5. Import dictionary data (optional)

```bash
# Import English-Vietnamese dictionary data
python scripts/import_dictionary.py data/dictionary.csv
```

### 6. Run the application

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Access API documentation

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

---

**Note:**

- All environment variables are documented in `.env.example`.
- Make sure to update your database connection string and secret key in your `.env` file for production use.
