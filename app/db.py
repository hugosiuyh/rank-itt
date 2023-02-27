from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import click
from flask import current_app, g


def get_db():
    if 'db' not in g:
        # Create a SQLAlchemy engine using the database URL
        engine = create_engine('postgresql://sxeotxuxlmjxyo:1c4b9218b5de7f2f8db838198eae0f7c2f6974265a1b50c91fdf010a67242b2e@ec2-44-194-4-127.compute-1.amazonaws.com:5432/d840ckthb5pvst')

        # Create a SQLAlchemy session factory
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create a scoped session for thread safety
        db_session = scoped_session(session_factory)

        # Set the row factory to access columns by name
        db_session.row_factory = lambda session, row: dict((col.name, row[idx]) for idx, col in enumerate(row.cursor.description))

        g.db = db_session

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()
    engine = create_engine('postgresql://sxeotxuxlmjxyo:1c4b9218b5de7f2f8db838198eae0f7c2f6974265a1b50c91fdf010a67242b2e@ec2-44-194-4-127.compute-1.amazonaws.com:5432/d840ckthb5pvst')

    with open('app/schema.sql', 'r') as f:
        schema = f.read()

# Execute the SQL statements in the schema.sql file
    with engine.connect() as conn:
        conn.execute(schema)


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    # tells Flask to call that function when cleaning up after returning the response
    app.teardown_appcontext(close_db)
    # adds a new command that can be called with the flask command
    app.cli.add_command(init_db_command)
