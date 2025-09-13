
#!/usr/bin/env python3
"""
Script to import dictionary data from CSV file
"""
import csv
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from src.config import get_database_url


def import_dictionary_data(csv_file_path: str):
    """Import dictionary data from CSV file"""
    
    try:
        # Get database URL
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print(f"📥 Importing dictionary data from {csv_file_path}...")
            
            # Check if data already exists
            result = conn.execute(text("SELECT COUNT(*) FROM dictionary")).scalar()
            if result > 0:
                print(f"⚠️  Dictionary already has {result:,} entries.")
                response = input("Do you want to clear existing data and reimport? (y/N): ")
                if response.lower() == 'y':
                    conn.execute(text("DELETE FROM dictionary"))
                    conn.commit()
                    print("🗑️  Cleared existing data")
                else:
                    print("❌ Import cancelled")
                    return
            
            # Import CSV data
            imported_count = 0
            batch_size = 1000
            batch = []
            
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file, delimiter='\t')
                
                for row_num, row in enumerate(csv_reader, 1):
                    if len(row) >= 3:
                        # Skip header if exists
                        if row_num == 1 and row[0].lower() == 'id':
                            continue
                            
                        batch.append({
                            'expression': row[1].strip(),
                            'definitions': row[2].strip()
                        })
                        
                        if len(batch) >= batch_size:
                            # Insert batch
                            conn.execute(text("""
                                INSERT INTO dictionary (expression, definitions)
                                VALUES (:expression, :definitions)
                            """), batch)
                            conn.commit()
                            imported_count += len(batch)
                            print(f"📥 Imported {imported_count:,} entries...")
                            batch = []
                
                # Insert remaining batch
                if batch:
                    conn.execute(text("""
                        INSERT INTO dictionary (expression, definitions)
                        VALUES (:expression, :definitions)
                    """), batch)
                    conn.commit()
                    imported_count += len(batch)
                    print(f"📥 Imported {imported_count:,} entries...")
            
            # Get final count
            result = conn.execute(text("SELECT COUNT(*) FROM dictionary")).scalar()
            print(f"✅ Import completed! Total entries: {result:,}")
            
    except Exception as e:
        print(f"❌ Error importing dictionary data: {e}")
        sys.exit(1)


def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_dictionary.py <csv_file_path>")
        print("Example: python scripts/import_dictionary.py data/dictionary.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    import_dictionary_data(csv_file)


if __name__ == "__main__":
    main()
