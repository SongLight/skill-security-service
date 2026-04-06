#!/usr/bin/env python3
"""
Medium risk skill - Has some permission overreach issues.
"""

import os
import sqlite3
import tempfile
from datetime import datetime


def read_config():
    """Declared: file_system.read ✓"""
    with open("/etc/hosts", "r") as f:
        return f.read()


def fetch_data():
    """Declared: network.http_request ✓"""
    import requests
    response = requests.get("https://api.example.com/data")
    return response.json()


def write_log(message):
    """Not declared: file_system.write ❌"""
    # Write to log file - MEDIUM risk
    log_dir = os.path.expanduser("~/.myapp")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "app.log")
    with open(log_file, "a") as f:
        timestamp = datetime.now().isoformat()
        f.write(f"[{timestamp}] {message}\n")


def create_temp_file(content):
    """Not declared: file_system.write ❌"""
    # Create temporary file
    fd, path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path
    except Exception:
        return None


def get_user_home():
    """Not declared: system.environment ❌"""
    # Access environment variables
    home = os.environ.get("HOME", "/")
    path = os.environ.get("PATH", "")
    return {"home": home, "path": path}


def init_database():
    """Not declared: database.access ❌"""
    # Initialize SQLite database
    db_path = os.path.expanduser("~/.myapp/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        )
    """)
    
    conn.commit()
    conn.close()
    return db_path


if __name__ == "__main__":
    print("=== MEDIUM RISK SKILL ===")
    
    # Declared operations
    config = read_config()
    data = fetch_data()
    
    # Not declared - OVERREACH
    write_log("Application started")
    temp_path = create_temp_file("test content")
    env_info = get_user_home()
    db_path = init_database()
    
    print(f"Config loaded: {len(config)} bytes")
    print(f"Data fetched: {data}")
    print(f"Temp file: {temp_path}")
    print(f"Home dir: {env_info['home']}")
    print(f"Database: {db_path}")
