#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to import sound data into database
"""
import json
import sys
import os
import codecs
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models first to register them with SQLAlchemy
import src.models  # This will register all models

from sqlalchemy import create_engine, text
from src.config import get_database_url


def import_sound_data(sound_data: list):
    """Import sound data into database"""
    
    try:
        # Get database URL
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print(f"📥 Importing {len(sound_data)} sound entries...")
            
            # Check if data already exists
            result = conn.execute(text("SELECT COUNT(*) FROM sounds WHERE deleted_at IS NULL")).scalar()
            if result > 0:
                print(f"ℹ️  Sounds table already has {result:,} entries. Skipping import.")
                return
            
            # Import sound data
            for sound in sound_data:
                # Parse datetime strings
                created_at = datetime.fromisoformat(sound['created_at'].replace('Z', '+00:00'))
                updated_at = datetime.fromisoformat(sound['updated_at'].replace('Z', '+00:00'))
                
                # Insert sound data
                conn.execute(text("""
                    INSERT INTO sounds (name, sound_file_url, file_size, duration, created_at, updated_at)
                    VALUES (:name, :sound_file_url, :file_size, :duration, :created_at, :updated_at)
                """), {
                    'name': sound['name'],
                    'sound_file_url': sound['sound_file_url'],
                    'file_size': sound['file_size'],
                    'duration': sound['duration'],
                    'created_at': created_at,
                    'updated_at': updated_at
                })
                print(f"📥 Imported: {sound['name']}")
            
            conn.commit()
            
            # Get final count
            result = conn.execute(text("SELECT COUNT(*) FROM sounds WHERE deleted_at IS NULL")).scalar()
            print(f"✅ Import completed! Total sound entries: {result:,}")
            
    except Exception as e:
        print(f"❌ Error importing sound data: {e}")
        sys.exit(1)


def main():
    """Main function"""
    # Sound data from the provided JSON
    sound_data = [
        {
            "name": "🌠 LoFi beats",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/31ea4e68f9094605aa310652a0d91fea.mp3",
            "file_size": 44935082,
            "duration": 3210,
            "id": 1,
            "created_at": "2025-10-26T13:43:24+0000",
            "updated_at": "2025-10-26T15:14:03+0000"
        },
        {
            "name": "🌿 Nature sounds",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/a8b5ca2294c34aa19b09b21cadd28121.mp3",
            "file_size": 5600790,
            "duration": 350,
            "id": 2,
            "created_at": "2025-10-26T13:44:48+0000",
            "updated_at": "2025-10-26T18:10:54+0000"
        },
        {
            "name": "💧 Rain sounds",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/840940e785b243f9aaaf0e34733214df.mp3",
            "file_size": 4945025,
            "duration": 309,
            "id": 3,
            "created_at": "2025-10-26T15:10:26+0000",
            "updated_at": "2025-10-26T18:11:06+0000"
        },
        {
            "name": "🔥 Fireplace sounds",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/066bd6afcf1148e8b89009044ac97d78.mp3",
            "file_size": 4560907,
            "duration": 285,
            "id": 4,
            "created_at": "2025-10-26T15:11:03+0000",
            "updated_at": "2025-10-26T18:11:16+0000"
        },
        {
            "name": "📚 Library ambience",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/e826cc94c1d44d42bb60eca0aaa2dad6.mp3",
            "file_size": 4976777,
            "duration": 311,
            "id": 5,
            "created_at": "2025-10-26T15:11:35+0000",
            "updated_at": "2025-10-26T18:11:38+0000"
        },
        {
            "name": "🎹 Piano music",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/ab8aea9aa0754860b809a6371af3142b.mp3",
            "file_size": 72995364,
            "duration": 9124,
            "id": 6,
            "created_at": "2025-10-26T15:11:50+0000",
            "updated_at": "2025-10-26T18:11:51+0000"
        },
        {
            "name": "🎷 Jazz music",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/35a27c66c2ec4e949be7e603a2c92b63.mp3",
            "file_size": 55024937,
            "duration": 6878,
            "id": 7,
            "created_at": "2025-10-26T15:12:07+0000",
            "updated_at": "2025-10-26T18:12:15+0000"
        },
        {
            "name": "🐉 Studio Ghibli music",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/c9788793194b495983aa1d1197f45c2a.mp3",
            "file_size": 27741570,
            "duration": 3468,
            "id": 8,
            "created_at": "2025-10-26T15:12:31+0000",
            "updated_at": "2025-10-26T18:12:59+0000"
        },
        {
            "name": "🧠 Binaural beats",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/7d5a2f31f3484c32983a70a31c2c4054.mp3",
            "file_size": 9424698,
            "duration": 589,
            "id": 9,
            "created_at": "2025-10-26T15:12:47+0000",
            "updated_at": "2025-10-26T18:13:33+0000"
        },
        {
            "name": "☕ Coffee shop ambience",
            "sound_file_url": "https://aeiouly.s3.ap-southeast-1.amazonaws.com/sounds/270596aa570d46ce9278c6c044796e76.mp3",
            "file_size": 34040822,
            "duration": 4255,
            "id": 10,
            "created_at": "2025-10-26T15:13:01+0000",
            "updated_at": "2025-10-26T18:14:17+0000"
        }
    ]
    
    import_sound_data(sound_data)


if __name__ == "__main__":
    main()
