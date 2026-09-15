from backend.app.database import engine
from sqlalchemy import text, inspect

insp = inspect(engine)
cols = [c['name'] for c in insp.get_columns('support_requests')]

with engine.connect() as conn:
    if 'session_format' not in cols:
        conn.execute(text("ALTER TABLE support_requests ADD COLUMN session_format VARCHAR(50) DEFAULT 'telephonic'"))
        print("Added session_format column")
    else:
        print("session_format already exists")

    if 'session_metadata' not in cols:
        conn.execute(text("ALTER TABLE support_requests ADD COLUMN session_metadata TEXT"))
        print("Added session_metadata column")
    else:
        print("session_metadata already exists")
    conn.commit()

print("Columns migration successfully executed.")
