"""Couche 5 + amélioration Facebook — ranking pur (score + raison + diversité), sans I/O."""
from dataclasses import dataclass

from app.social.application.ranking import (REASON_AFFINITY, REASON_FRESH, REASON_FRIEND,
                                            REASON_OWN, REASON_POPULAR, diversify, score_post)


@dataclass
class _P:  # faux post minimal pour tester le re-rank diversité
    author_id: str


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


def test_affinite_augmente_le_score_et_peut_devenir_la_raison():
    s_low, _ = score_post(is_friend=False, is_following=True, is_own=False,
                          age_hours=100, reactions=0, comments=0, affinity=0.0)
    s_high, reason = score_post(is_friend=False, is_following=True, is_own=False,
                                age_hours=100, reactions=0, comments=0, affinity=1.0)
    assert s_high > s_low and reason == REASON_AFFINITY


def test_bonus_media_leger():
    s_txt, _ = score_post(is_friend=True, is_following=False, is_own=False,
                          age_hours=10, reactions=0, comments=0, has_media=False)
    s_media, _ = score_post(is_friend=True, is_following=False, is_own=False,
                            age_hours=10, reactions=0, comments=0, has_media=True)
    assert s_media > s_txt


def test_diversite_evite_deux_posts_du_meme_auteur_a_la_suite():
    # A a 3 posts très forts, B un seul plus faible : sans diversité A,A,A,B ;
    # avec diversité, le post de B doit remonter (pas 3 A d'affilée en tête).
    scored = [(10.0, "r", _P("A")), (9.5, "r", _P("A")), (9.0, "r", _P("A")), (5.0, "r", _P("B"))]
    order = [item[-1].author_id for item in diversify(scored)]
    assert order[0] == "A" and order[1] == "B"  # B intercalé avant le 2e A
