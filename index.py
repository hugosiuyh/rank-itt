from app import create_app
from app.db import init_db

app = create_app()
with app.app_context():
    db = init_db()
app.run()
