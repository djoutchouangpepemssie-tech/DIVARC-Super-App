"""Couche 5 — ranking pur (score + raison explicable), sans I/O."""
from app.social.application.ranking import (REASON_FRESH, REASON_FRIEND, REASON_OWN,
                                            REASON_POPULAR, score_post)


def test_ami_prime_sur_suivi():
    s_friend, r_friend = score_post(is_friend=True, is_following=True, is_own=False,
                                    age_hours=10, reactions=0, comments=0)
    s_follow, _ = score_post(is_friend=False, is_following=True, is_own=False,
                             age_hours=10, reactions=0, comments=0)
    assert s_friend > s_follow and r_friend == REASON_FRIEND


def test_popularite_via_engagement():
    _, reason = score_post(is_friend=False, is_following=False, is_own=False,
                           age_hours=48, reactions=50, comments=30)
    assert reason == REASON_POPULAR


def test_fraicheur_pour_post_recent_sans_engagement():
    _, reason = score_post(is_friend=False, is_following=False, is_own=False,
                           age_hours=0, reactions=0, comments=0)
    assert reason == REASON_FRESH


def test_commentaires_pesent_plus_que_reactions():
    s_comments, _ = score_post(is_friend=False, is_following=False, is_own=False,
                               age_hours=48, reactions=0, comments=10)
    s_reactions, _ = score_post(is_friend=False, is_following=False, is_own=False,
                                age_hours=48, reactions=10, comments=0)
    assert s_comments > s_reactions  # la conversation vaut plus que le like


def test_ma_publication_a_une_raison_dediee():
    _, reason = score_post(is_friend=False, is_following=False, is_own=True,
                           age_hours=100, reactions=0, comments=0)
    assert reason == REASON_OWN
