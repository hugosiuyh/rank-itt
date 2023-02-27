import trueskill


def init_user_rating():
    rating = trueskill.Rating()
    return rating.mu, rating.sigma


def update_rating(self_mu, self_sigma, self_score, opp_mu, opp_sigma, opp_score):

    # Reconstruct Rating object
    self_r = trueskill.Rating(self_mu, self_sigma)
    opp_r = trueskill.Rating(opp_mu, opp_sigma)

    # Update the Rating depending on who wins
    if self_score > opp_score:
        new_self_r, new_opp_r = trueskill.rate_1vs1(self_r, opp_r)
    elif opp_score > self_score:
        new_opp_r, new_self_r = trueskill.rate_1vs1(opp_r, self_r)

    # Return the deconstructed Rating object
    return new_self_r.mu, new_self_r.sigma, new_opp_r.mu, new_opp_r.sigma
