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

### 5. Import initial data (optional)

You can import various types of data into your database:

#### Option 1: Import all data at once
```bash
# Run all import scripts (admin user, sounds)
python scripts/run_all_imports.py

# Import dictionary separately (requires CSV file)
python scripts/import_dictionary.py data/dictionary.csv

# Import background videos separately (requires JSON file)
python scripts/import_background_videos.py
```

#### Option 2: Import data separately

**Import admin user:**
```bash
# Creates admin user (username: admin, password: admin123)
python scripts/create_admin.py
```

**Import sound data:**
```bash
# Import 10 pre-configured sound files
python scripts/import_sounds.py
```

**Import dictionary data:**
```bash
# Import English-Vietnamese dictionary from CSV
python scripts/import_dictionary.py data/dictionary.csv
```

**Import background videos:**
```bash
# Import background video types and videos
python scripts/import_background_videos.py
```

### 6. Run the application

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Access API documentation

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

---

## Data Import Details

### Admin User
- **Script**: `scripts/create_admin.py`
- **Creates**: Default admin account
- **Credentials**:
  - Username: `admin`
  - Password: `admin123`
  - Email: `admin@aeiouly.com`
  - Role: `admin`
- **Behavior**: Only creates if admin user doesn't exist

### Sound Files
- **Script**: `scripts/import_sounds.py`
- **Imports**: 10 pre-configured background music files
- **Files**:
  - 🌠 LoFi beats (3210 seconds)
  - 🌿 Nature sounds (350 seconds)
  - 💧 Rain sounds (309 seconds)
  - 🔥 Fireplace sounds (285 seconds)
  - 📚 Library ambience (311 seconds)
  - 🎹 Piano music (9124 seconds)
  - 🎷 Jazz music (6878 seconds)
  - 🐉 Studio Ghibli music (3468 seconds)
  - 🧠 Binaural beats (589 seconds)
  - ☕ Coffee shop ambience (4255 seconds)
- **Behavior**: Only imports if no sounds exist in database

### Dictionary Data
- **Script**: `scripts/import_dictionary.py`
- **Requires**: CSV file with dictionary entries
- **Format**: TSV (Tab-Separated Values)
- **Behavior**: Only imports if no dictionary entries exist

### Background Videos
- **Script**: `scripts/import_background_videos.py`
- **Requires**: JSON file at `data/background_videos_data.json`
- **Imports**: 
  - 8 background video types (🌸 Anime, 📚 Library, 🌿 Nature, 🐱 Animals, ☕ Cafe, 💻 Desk, 🏙️ City, ✨ Other)
  - Background videos with YouTube URLs and image URLs
- **Behavior**: Only imports if no background videos exist in database

### All-in-One Import
- **Script**: `scripts/run_all_imports.py`
- **Runs all scripts in sequence**:
  1. Create admin user
  2. Import sound files
- **Note**: Dictionary and background videos imports require data files and must be run separately

---

## Notes

- All environment variables are documented in `.env.example`
- Make sure to update your database connection string and secret key in your `.env` file for production use
- Scripts are idempotent (safe to run multiple times)
- Scripts use soft-delete pattern (preserve deleted records)
