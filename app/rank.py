import sqlite3
from flask import (Blueprint, flash, g, redirect, render_template, request, url_for)
from typing import List
from werkzeug.exceptions import abort

from app.auth import login_required
from app.db import get_db
from app.rating.rating import update_rating

rank = Blueprint('rank', __name__)


@rank.route('/', methods=['GET'])
@login_required
def index():
    """ View function for the index page which shows the ranking table """

    # Get player ranking from d_skill table in descending order
    db: sqlite3.Connection = get_db()
    ranking: List[sqlite3.Row] = db.execute(
        """
        SELECT du.id as user_id, du.username as name, ds.skill as skill, ds.uncertainty as uncertainty 
        FROM d_skill ds 
        JOIN d_user du 
            ON ds.user_id = du.id 
        ORDER BY skill DESC;
        """
    ).fetchall()

    return render_template('rank/index.html', ranking=ranking)


@rank.route('/add-score', methods=['GET', 'POST'])
@login_required
def add_score():
    """ View function for the Add Score page """

    if request.method == 'POST':

        # Access form response
        opp_username = request.form['opponent']
        self_score = request.form['your-score']
        opp_score = request.form['opponent-score']

        # Handle form response error
        db = get_db()
        error = None
        usernames: List[str] = [row["username"] for row in db.execute('SELECT username FROM d_user').fetchall()]
        if not opp_username or not self_score or not opp_score:
            error = 'All entries must be filled.'
        elif opp_username not in usernames:
            error = 'Opponent\'s username does not exist.'
        elif opp_username == g.user['username']:
            error = 'Opponent cannot be yourself.'
        elif not self_score.isdigit() or not opp_score.isdigit():
            error = "Your/Opponent score must be an integer."
        elif self_score == opp_score:
            error = "Game result cannot be a draw."

        if error is None:

            # Convert scores from string in form response to integer
            self_score, opp_score = int(self_score), int(opp_score)

            # Get opponent user_id
            opp_ = db.execute(""" SELECT * FROM d_user WHERE username = ?; """, (opp_username,)).fetchone()

            # Update d_match table and get match_id
            match = db.execute(
                """
                INSERT INTO d_match(self_user_id, opponent_user_id, is_reviewed)
                VALUES (?, ?, ?)
                RETURNING id;
                """,
                (g.user['id'], opp_['id'], 0),
            ).fetchone()
            db.commit()

            # Update d_score
            db.execute(
                """
                INSERT INTO d_score(match_id, user_id, score, is_winner, is_reviewed)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)
                """,
                (match['id'], g.user['id'], self_score, 1 if self_score > opp_score else 0, 1,  # self score is always reviewed
                 match['id'], opp_['id'], opp_score, 1 if opp_score > self_score else 0, 0)  # opp score is always pending review
            )
            db.commit()

            return redirect(url_for('rank.profile', user_id=g.user['id']))

        # If not show the error message
        flash(error)

    db = get_db()
    users = db.execute('SELECT username FROM d_user WHERE id != ?', (g.user['id'],)).fetchall()
    return render_template('rank/add_score.html', users=users)


@rank.route('/approve-score/<int:match_id>/<int:self_score_id>/<int:opp_score_id>', methods=['GET'])
@login_required
def approve_score(match_id, self_score_id, opp_score_id):

    # Update d_score
    db = get_db()
    db.execute("""UPDATE d_score SET is_reviewed = 1 WHERE id = ?""",(self_score_id, ))

    # Update d_match
    db.execute("""UPDATE d_match SET is_reviewed = 1 WHERE id = ?""", (match_id,))

    # Update d_skill
    # Query player 1's user id, current skill, current uncertainty
    self_ = db.execute(
        """
        SELECT du.id as user_id, dsk.skill as skill, dsk.uncertainty as uncertainty, dsc.score as score
        FROM d_user as du
        JOIN d_skill dsk on du.id = dsk.user_id
        JOIN d_score dsc on du.id = dsc.user_id 
        WHERE du.id = ? AND dsc.id = ?
        """,
        (g.user["id"], self_score_id)
    ).fetchone()

    # Query player 2's user id, current skill, current uncertainty
    opp_ = db.execute(
        """
        SELECT du.id as user_id, dsk.skill as skill, dsk.uncertainty as uncertainty, dsc.score as score
        FROM d_user as du
        JOIN d_skill dsk on du.id = dsk.user_id
        JOIN d_score dsc on du.id = dsc.user_id 
        WHERE dsc.id = ?
        """,
        (opp_score_id,)
    ).fetchone()

    # Get player 1's and player 2's Rating (i.e. mu = skill, sigma = uncertainty)
    self_id, self_mu, self_sigma, self_score = self_["user_id"], self_["skill"], self_["uncertainty"], self_["score"]
    opp_id, opp_mu, opp_sigma, opp_score = opp_["user_id"], opp_["skill"], opp_["uncertainty"], opp_["score"]

    # Update their rating
    new_self_mu, new_self_sigma, new_opp_mu, new_opp_sigma = update_rating(
        self_mu, self_sigma, self_score,
        opp_mu, opp_sigma, opp_score
    )

    # Update d_skill table with player 1
    db.execute("""UPDATE d_skill SET skill = ?, uncertainty = ? WHERE user_id = ?""",
               (new_self_mu, new_self_sigma, self_id))
    db.commit()

    # Update d_skill table with player 1
    db.execute("""UPDATE d_skill SET skill = ?, uncertainty = ? WHERE user_id = ?""",
               (new_opp_mu, new_opp_sigma, opp_id))
    db.commit()

    return redirect(url_for('rank.index'))


@rank.route('/profile/<int:user_id>', methods=['GET'])
@login_required
def profile(user_id):
    """ View function for the profile page; conditionally renders if user is current user or other """

    db = get_db()

    # Query the username and count how many games played
    username_game_count = db.execute(
        """
        SELECT du.username as username, COUNT(*) as game_count
        FROM d_score ds
        JOIN d_user du ON du.id = ds.user_id
        WHERE user_id = ?;
        """,
        (user_id,)
    ).fetchone()
    username, games_played = username_game_count['username'], username_game_count['game_count']

    # Query how many games the user won or lost -- 2 sqlite3.Row result
    history: List[sqlite3.Row] = db.execute(
        """
        SELECT is_winner, COUNT(is_winner) AS count
        FROM d_score
        WHERE user_id = ?
        GROUP BY is_winner;
        """,
        (user_id,)
    ).fetchall()

    lost, won = 0, 0
    # If user has both won and lost
    if len(history) == 2:
        lost, won = history[0]["count"], history[1]["count"]
    # If user has either won or lost
    elif len(history) == 1:
        if history[0]["is_winner"] == 0:
            lost = history[0]["count"]
        elif history[0]["is_winner"] == 1:
            won = history[0]["count"]

    # Query which matches require your approval
    pending_self_approval = db.execute(
        """
        SELECT
            t1.match_id as match_id,
            t1.user_id as self_id,
            t1.id as self_score_id,
            t1.score as self_score,
            t2.user_id as opp_id,
            t2.id as opp_score_id,
            t2.score as opp_score,
            du.username as opp_username,
            t1.created as date
        FROM d_score t1
        JOIN d_score t2 ON t1.match_id = t2.match_id
        JOIN d_user du ON t2.user_id = du.id
        WHERE t1.is_reviewed = 0
            AND t2.is_reviewed = 1
            AND t1.user_id = ? 
            AND t2.user_id != t1.user_id;
        """,
        (user_id, )
    ).fetchall()

    # Query which matches are still waiting on other's approval
    pending_others_approval = db.execute(
        """
        SELECT
            t1.match_id as match_id,
            t1.user_id as self_id,
            t1.score as self_score,
            t2.user_id as opp_id,
            t2.score as opp_score,
            du.username as opp_username,
            t1.created as date
        FROM d_score t1
        JOIN d_score t2 ON t1.match_id = t2.match_id
        JOIN d_user du ON t2.user_id = du.id
        WHERE t1.is_reviewed = 1
            AND t2.is_reviewed = 0 
            AND t1.user_id = ? 
            AND t2.user_id != t1.user_id;
        """,
        (user_id, )
    ).fetchall()

    return render_template('rank/profile.html',
                           user_id=user_id,
                           username=username,
                           games_played=games_played,
                           lost=lost,
                           won=won,
                           pending_self_approval=pending_self_approval,
                           pending_others_approval=pending_others_approval)

@rank.route('/about', methods=['GET'])
@login_required
def about():
    return render_template('rank/about.html', name=g.user["first_name"])

