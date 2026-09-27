import sqlite3
from datetime import datetime
from pathlib import Path
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Ma'lumotlar bazasini va jadvallarni yaratish"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Kinolar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                clean_title TEXT NOT NULL,
                channel_message_id INTEGER NOT NULL,
                file_size INTEGER DEFAULT 0,
                duration INTEGER DEFAULT 0,
                uploader_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_clean_title ON movies(clean_title)")

        # Foydalanuvchi qadamma-qadam jarayoni (Session) jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id INTEGER PRIMARY KEY,
                state TEXT DEFAULT 'IDLE',
                video_msg_id INTEGER,
                subtitle_msg_id INTEGER,
                video_name TEXT,
                subtitle_name TEXT,
                title TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def normalize_title(title: str) -> str:
    """Qidirish va solishtirish uchun nomni tozalash"""
    return " ".join(title.lower().strip().split())

def add_movie(title: str, channel_message_id: int, file_size: int = 0, duration: int = 0, uploader_id: int = None) -> int:
    clean_title = normalize_title(title)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO movies (title, clean_title, channel_message_id, file_size, duration, uploader_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title.strip(), clean_title, channel_message_id, file_size, duration, uploader_id))
        conn.commit()
        return cursor.lastrowid

def search_movies(query: str, limit: int = 10):
    clean_query = f"%{normalize_title(query)}%"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM movies
            WHERE clean_title LIKE ?
            ORDER BY id DESC
            LIMIT ?
        """, (clean_query, limit))
        return [dict(row) for row in cursor.fetchall()]

def get_movie_by_id(movie_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_movie_by_title(title: str):
    clean_title = normalize_title(title)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE clean_title = ? LIMIT 1", (clean_title,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_recent_movies(limit: int = 5):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_user_session(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_sessions WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        # Agar yo'q bo'lsa yangi bo'sh sessiya
        cursor.execute("INSERT INTO user_sessions (user_id, state) VALUES (?, 'IDLE')", (user_id,))
        conn.commit()
        return {"user_id": user_id, "state": "IDLE", "video_msg_id": None, "subtitle_msg_id": None, "video_name": None, "subtitle_name": None, "title": None}

def update_user_session(user_id: int, **kwargs):
    if not kwargs:
        return
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(datetime.utcnow())
    values.append(user_id)
    
    query = f"UPDATE user_sessions SET {', '.join(fields)}, updated_at = ? WHERE user_id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(values))
        if cursor.rowcount == 0:
            # Insert if not exists
            columns = ["user_id"] + list(kwargs.keys())
            placeholders = ["?"] * len(columns)
            cursor.execute(
                f"INSERT INTO user_sessions ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                tuple([user_id] + list(kwargs.values()))
            )
        conn.commit()

def clear_user_session(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_sessions 
            SET state = 'IDLE', video_msg_id = NULL, subtitle_msg_id = NULL, video_name = NULL, subtitle_name = NULL, title = NULL 
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()

def get_total_movies_count() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        return cursor.fetchone()[0]
