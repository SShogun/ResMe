import os
import sqlite3
import json

DATABASE_URL = os.environ.get("DATABASE_URL")

# Check if we should use PostgreSQL
IS_POSTGRES = DATABASE_URL is not None and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://"))

def get_connection():
    if IS_POSTGRES:
        import psycopg2
        # Render sometimes provides postgres:// instead of postgresql:// which python's psycopg2 expects
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        return conn
    else:
        DB_PATH = os.path.join(os.path.dirname(__file__), "applications.db")
        conn = sqlite3.connect(DB_PATH)
        return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
        # PostgreSQL syntax
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id SERIAL PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Wishlist',
            date_applied TEXT NOT NULL,
            jd_text TEXT,
            latex_content TEXT,
            notes TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_profile (
            id INT PRIMARY KEY DEFAULT 1,
            resume_data TEXT NOT NULL,
            CONSTRAINT sole_profile CHECK (id = 1)
        )
        """)
    else:
        # SQLite syntax
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Wishlist',
            date_applied TEXT NOT NULL,
            jd_text TEXT,
            latex_content TEXT,
            notes TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            resume_data TEXT NOT NULL
        )
        """)
        
    conn.commit()
    conn.close()

def execute_query(query, params=(), commit=False, fetchone=False, fetchall=False):
    conn = get_connection()
    # For SQLite, we can use conn.row_factory to return dict-like rows.
    # For Postgres, we can map manually.
    if not IS_POSTGRES:
        conn.row_factory = sqlite3.Row
        
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    result = None
    if fetchone:
        row = cursor.fetchone()
        if row:
            result = dict(row) if not IS_POSTGRES else dict(zip([desc[0] for desc in cursor.description], row))
    elif fetchall:
        rows = cursor.fetchall()
        if IS_POSTGRES:
            cols = [desc[0] for desc in cursor.description]
            result = [dict(zip(cols, row)) for row in rows]
        else:
            result = [dict(row) for row in rows]
            
    if commit:
        conn.commit()
        
    # Get last insert id if commit & no return results
    last_id = None
    if commit and not IS_POSTGRES:
        last_id = cursor.lastrowid
    elif commit and IS_POSTGRES and "INSERT INTO applications" in query:
        # We will append RETURNING id to insert query for postgres
        pass
        
    conn.close()
    return result if (fetchone or fetchall) else last_id

# Helper CRUD operations
def get_all_applications():
    return execute_query("SELECT * FROM applications ORDER BY id DESC", fetchall=True)

def get_application(app_id: int):
    return execute_query("SELECT * FROM applications WHERE id = %s" if IS_POSTGRES else "SELECT * FROM applications WHERE id = ?", (app_id,), fetchone=True)

def create_application(company: str, title: str, status: str, date_applied: str, jd_text: str = "", latex_content: str = "", notes: str = ""):
    if IS_POSTGRES:
        # PostgreSQL returning insert
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO applications (company, title, status, date_applied, jd_text, latex_content, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (company, title, status, date_applied, jd_text, latex_content, notes))
        new_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return new_id
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO applications (company, title, status, date_applied, jd_text, latex_content, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (company, title, status, date_applied, jd_text, latex_content, notes))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

def update_application(app_id: int, company: str, title: str, status: str, date_applied: str, jd_text: str, latex_content: str, notes: str):
    placeholder = "%s" if IS_POSTGRES else "?"
    query = f"""
    UPDATE applications
    SET company = {placeholder}, title = {placeholder}, status = {placeholder}, date_applied = {placeholder}, jd_text = {placeholder}, latex_content = {placeholder}, notes = {placeholder}
    WHERE id = {placeholder}
    """
    execute_query(query, (company, title, status, date_applied, jd_text, latex_content, notes, app_id), commit=True)
    return True

def delete_application(app_id: int):
    placeholder = "%s" if IS_POSTGRES else "?"
    execute_query(f"DELETE FROM applications WHERE id = {placeholder}", (app_id,), commit=True)
    return True

# Resume Profile Helpers
def get_resume_profile():
    row = execute_query("SELECT resume_data FROM resume_profile WHERE id = 1", fetchone=True)
    return json.loads(row["resume_data"]) if row else None

def save_resume_profile(resume_data: dict):
    data_str = json.dumps(resume_data)
    conn = get_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("""
        INSERT INTO resume_profile (id, resume_data) VALUES (1, %s)
        ON CONFLICT (id) DO UPDATE SET resume_data = EXCLUDED.resume_data
        """, (data_str,))
    else:
        cursor.execute("""
        INSERT OR REPLACE INTO resume_profile (id, resume_data) VALUES (1, ?)
        """, (data_str,))
    conn.commit()
    conn.close()

# Initialize tables
init_db()
