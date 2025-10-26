#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to run all import scripts in sequence
- import_dictionary.py: Import dictionary data
- import_sounds.py: Import sound data
- create_admin.py: Create admin user
"""
import sys
import os
import subprocess
import codecs

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_script(script_name, description):
    """Run a script and handle errors"""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    try:
        # Set environment variable to force UTF-8 encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, script_path],
            check=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}", file=sys.stderr)
        return False


def main():
    """Main function to run all imports"""
    print("🚀 Starting all import scripts...")
    
    # List of scripts to run
    # Note: dictionary import requires CSV file, so it's commented out
    # You can run it manually: python scripts/import_dictionary.py data/dictionary.csv
    scripts = [
        ("create_admin.py", "Create Admin User"),
        ("import_sounds.py", "Import Sound Data"),
        # ("import_dictionary.py", "Import Dictionary Data"),  # Requires CSV file argument
    ]
    
    results = {}
    
    for script_name, description in scripts:
        success = run_script(script_name, description)
        results[script_name] = success
        
        if success:
            print(f"✅ {description} completed successfully")
        else:
            print(f"❌ {description} failed or skipped")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Summary")
    print(f"{'='*60}")
    
    for script_name, success in results.items():
        status = "✅ Success" if success else "❌ Failed/Skipped"
        print(f"{status}: {script_name}")
    
    print(f"\n{'='*60}")
    success_count = sum(1 for s in results.values() if s)
    print(f"Total: {success_count}/{len(scripts)} scripts completed successfully")
    
    return success_count == len(scripts)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
