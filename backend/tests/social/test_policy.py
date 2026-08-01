"""Couche 1 — règles de visibilité & PolicyService (domaine pur, sans I/O)."""
from app.social.domain.policy import PolicyService
from app.social.domain.visibility import PostAudience, ViewerRelation, Visibility, can_view

P = PolicyService()
AUTHOR = "u-author"
VIEWER = "u-viewer"


def _post(vis, **kw):
    return PostAudience(visibility=vis, author_id=AUTHOR, **kw)


def test_public_visible_par_tous():
    assert can_view(VIEWER, _post(Visibility.PUBLIC), ViewerRelation()) is True


def test_only_me_reserve_a_l_auteur():
    assert can_view(AUTHOR, _post(Visibility.ONLY_ME), ViewerRelation()) is True
    assert can_view(VIEWER, _post(Visibility.ONLY_ME), ViewerRelation()) is False


def test_friends_requiert_amitie():
    assert can_view(VIEWER, _post(Visibility.FRIENDS), ViewerRelation(is_friend=False)) is False
    assert can_view(VIEWER, _post(Visibility.FRIENDS), ViewerRelation(is_friend=True)) is True


def test_friends_except_exclut_une_liste():
    post = _post(Visibility.FRIENDS_EXCEPT, excluded_ids=frozenset({VIEWER}))
    assert can_view(VIEWER, post, ViewerRelation(is_friend=True)) is False
    assert can_view("u-other", post, ViewerRelation(is_friend=True)) is True


def test_circles_intersection():
    post = _post(Visibility.CIRCLES, circle_ids=frozenset({"c1", "c2"}))
    assert can_view(VIEWER, post, ViewerRelation(viewer_circle_ids=frozenset({"c2"}))) is True
    assert can_view(VIEWER, post, ViewerRelation(viewer_circle_ids=frozenset({"c9"}))) is False


def test_group_requiert_appartenance():
    post = _post(Visibility.GROUP, group_id="g1")
    assert can_view(VIEWER, post, ViewerRelation(is_group_member=True)) is True
    assert can_view(VIEWER, post, ViewerRelation(is_group_member=False)) is False


def test_blocage_prime_sur_public():
    assert can_view(VIEWER, _post(Visibility.PUBLIC), ViewerRelation(is_blocked=True)) is False


def test_auteur_voit_toujours_meme_bloque_ou_only_me():
    assert can_view(AUTHOR, _post(Visibility.ONLY_ME), ViewerRelation(is_blocked=True)) is True


def test_post_supprime_invisible_pour_tous():
    assert can_view(AUTHOR, _post(Visibility.PUBLIC, deleted=True), ViewerRelation()) is False
    assert can_view(VIEWER, _post(Visibility.PUBLIC, deleted=True), ViewerRelation()) is False


def test_commenter_bloque_si_commentaires_fermes():
    post = _post(Visibility.PUBLIC)
    assert P.can_comment(VIEWER, post, ViewerRelation(), comments_closed=True) is False
    assert P.can_comment(AUTHOR, post, ViewerRelation(), comments_closed=True) is True  # l'auteur peut


def test_partage_uniquement_du_public():
    assert P.can_share(VIEWER, _post(Visibility.PUBLIC), ViewerRelation()) is True
    assert P.can_share(VIEWER, _post(Visibility.FRIENDS), ViewerRelation(is_friend=True)) is False


def test_edition_reservee_a_l_auteur():
    post = _post(Visibility.PUBLIC)
    assert P.can_edit(AUTHOR, post, ViewerRelation()) is True
    assert P.can_edit(VIEWER, post, ViewerRelation()) is False


def test_suppression_par_moderateur_de_groupe():
    post = _post(Visibility.GROUP, group_id="g1")
    assert P.can_delete("u-mod", post, ViewerRelation(is_group_member=True, group_role="moderator")) is True
    assert P.can_delete("u-mod", post, ViewerRelation(is_group_member=True, group_role="member")) is False
