#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to import background video types and background videos data into database
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


def import_background_video_types(type_data: list):
    """Import background video types into database"""
    
    try:
        # Get database URL
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print(f"📥 Importing {len(type_data)} background video types...")
            
            # Check if data already exists
            result = conn.execute(text("SELECT COUNT(*) FROM background_video_types WHERE deleted_at IS NULL")).scalar()
            if result > 0:
                print(f"ℹ️  Background video types table already has {result:,} entries. Skipping import.")
                return
            
            # Import types data
            for vid_type in type_data:
                # Parse datetime strings
                created_at = datetime.fromisoformat(vid_type['created_at'].replace('Z', '+00:00'))
                updated_at = datetime.fromisoformat(vid_type['updated_at'].replace('Z', '+00:00'))
                
                # Insert type data
                conn.execute(
                    text("""
                        INSERT INTO background_video_types 
                        (id, name, description, created_at, updated_at, deleted_at)
                        VALUES (:id, :name, :description, :created_at, :updated_at, NULL)
                    """),
                    {
                        'id': vid_type['id'],
                        'name': vid_type['name'],
                        'description': vid_type['description'],
                        'created_at': created_at,
                        'updated_at': updated_at
                    }
                )
            
            conn.commit()
            print(f"✅ Successfully imported {len(type_data)} background video types!")
            
    except Exception as e:
        print(f"❌ Error importing background video types: {e}")
        raise


def import_background_videos(video_data: list):
    """Import background videos into database"""
    
    try:
        # Get database URL
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print(f"📥 Importing {len(video_data)} background videos...")
            
            # Check if data already exists
            result = conn.execute(text("SELECT COUNT(*) FROM background_videos WHERE deleted_at IS NULL")).scalar()
            if result > 0:
                print(f"ℹ️  Background videos table already has {result:,} entries. Skipping import.")
                return
            
            # Import videos data
            for video in video_data:
                # Parse datetime strings
                created_at = datetime.fromisoformat(video['created_at'].replace('Z', '+00:00'))
                updated_at = datetime.fromisoformat(video['updated_at'].replace('Z', '+00:00'))
                
                # Insert video data
                conn.execute(
                    text("""
                        INSERT INTO background_videos 
                        (id, youtube_url, image_url, type_id, created_at, updated_at, deleted_at)
                        VALUES (:id, :youtube_url, :image_url, :type_id, :created_at, :updated_at, NULL)
                    """),
                    {
                        'id': video['id'],
                        'youtube_url': video['youtube_url'],
                        'image_url': video['image_url'],
                        'type_id': video['type_id'],
                        'created_at': created_at,
                        'updated_at': updated_at
                    }
                )
            
            conn.commit()
            print(f"✅ Successfully imported {len(video_data)} background videos!")
            
    except Exception as e:
        print(f"❌ Error importing background videos: {e}")
        raise


def main():
    """Main function to import all data"""
    
    # Background video types data
    types_data = [
        {"name": "🌸 Anime", "description": "🌸 Anime", "id": 1, "created_at": "2025-10-27T20:12:23+0000", "updated_at": "2025-10-27T20:12:23+0000"},
        {"name": "📚 Library", "description": "📚 Library", "id": 2, "created_at": "2025-10-27T20:12:35+0000", "updated_at": "2025-10-27T20:12:35+0000"},
        {"name": "🌿 Nature", "description": "🌿 Nature", "id": 3, "created_at": "2025-10-27T20:12:56+0000", "updated_at": "2025-10-27T20:12:56+0000"},
        {"name": "🐱 Animals", "description": "🐱 Animals", "id": 4, "created_at": "2025-10-27T20:13:08+0000", "updated_at": "2025-10-27T20:13:08+0000"},
        {"name": "☕ Cafe", "description": "☕ Cafe", "id": 5, "created_at": "2025-10-27T20:13:18+0000", "updated_at": "2025-10-27T20:13:18+0000"},
        {"name": "💻 Desk", "description": "💻 Desk", "id": 6, "created_at": "2025-10-27T20:13:32+0000", "updated_at": "2025-10-27T20:13:32+0000"},
        {"name": "🏙️ City", "description": "🏙️ City", "id": 7, "created_at": "2025-10-27T20:14:54+0000", "updated_at": "2025-10-27T20:14:54+0000"},
        {"name": "✨ Other", "description": "✨ Other", "id": 8, "created_at": "2025-10-27T20:15:38+0000", "updated_at": "2025-10-27T20:15:38+0000"}
    ]
    
    # Read videos data from JSON file if it exists, otherwise use sample data
    videos_data = []
    json_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'background_videos_data.json')
    
    if os.path.exists(json_file):
        print(f"📂 Reading data from {json_file}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            videos_data = json_data.get('items', [])
    else:
        print("⚠️  background_videos_data.json not found. Creating sample data file...")
        # This is where you can paste your full JSON data
        print("Please create background_videos_data.json in scripts/ folder")
        return
    
    print("🚀 Starting background videos import process...\n")
    
    # Import types first
    import_background_video_types(types_data)
    print()
    
    # Import videos
    import_background_videos(videos_data)
    print()
    
    print("🎉 All background videos data imported successfully!")


if __name__ == "__main__":
    main()
