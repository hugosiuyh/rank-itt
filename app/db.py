import sqlite3
import click
from flask import current_app, g


def get_db():
    if 'db' not in g:
        # Create a SQLAlchemy engine using the database URL
        engine = create_engine('sqlite:///{}'.format(current_app.config['DATABASE']), convert_unicode=True)

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

    with current_app.open_resource('./schema.sql') as f:  # opens file relative to "app" package
        db.executescript(f.read().decode('utf8'))


def init_db_vercel():
    db = get_db()

    with open('app/schema.sql') as f:  # opens file relative to "app" package
        db.executescript(f.read())


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
