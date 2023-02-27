import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
import trueskill

from app.db import get_db
from app.rating.rating import init_user_rating

auth = Blueprint('auth', __name__, url_prefix='/auth')


@auth.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        first_name = request.form['first_name']

        db = get_db()
        error = None
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif not first_name:
            error = 'First name is required.'

        if error is None:
            try:

                # Insert into d_user
                db.execute(
                    "INSERT INTO d_user (username, password, first_name) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), first_name),
                )
                db.commit()

                # Insert into d_ranking with default user
                init_skill, init_uncertainty = init_user_rating()

                # Get the recently-committed new user entry
                user = db.execute(
                    'SELECT * FROM d_user WHERE username = ?', (username,)
                ).fetchone()

                # Insert into the d_skill with initialized TrueSkill rating
                db.execute(
                    "INSERT INTO d_skill (user_id, skill, uncertainty) VALUES (?, ?, ?)",
                    (user['id'], init_skill, init_uncertainty),
                )
                db.commit()

            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:

                # Directly logs in
                session.clear()
                session['user_id'] = user['id']
                return redirect(url_for('index'))

        flash(error)

    return render_template('auth/register.html')


@auth.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM d_user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            # session is a dict that stores data across requests. When validation succeeds,
            # the user’s id is stored in a new session. The data is stored in a cookie that is
            # sent to the browser, and the browser then sends it back with subsequent requests.
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')


@auth.before_app_request  # registers a function that runs before the view function, no matter what URL is requested.
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM d_user WHERE id = ?', (user_id,)
        ).fetchone()


@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# Decorator definition for views
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        # Redirects if not logged in
        if g.user is None:
            return redirect(url_for('auth.login'))

        # Simply returns the view if logged in
        return view(**kwargs)

    return wrapped_view
