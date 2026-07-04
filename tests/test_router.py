from types import SimpleNamespace

from resources.lib.router import Router


def _handlers(calls):
    names = [
        'main_menu', 'do_login', 'do_search', 'manage_profiles',
        'browse_my_list', 'browse_my_list_group', 'toggle_mylist',
        'select_profile', 'apply_profile', 'browse_series', 'do_logout',
        'confirm_logout', 'refresh_account_info', 'search_group',
        'show_series_detail', 'show_series_season', 'browse_placement_row',
        'browse_tv_shows', 'browse_tv_genre', 'browse_series_categories',
        'browse_series_genre', 'browse_movie_categories',
        'browse_movie_genre', 'browse_category', 'play_item',
        'select_iptv_channels',
    ]

    def make(name):
        def handler(*args, **kwargs):
            calls.append((name, args, kwargs))
        return handler

    return {name: make(name) for name in names}


def test_missing_mode_dispatches_main_menu():
    calls = []
    context = SimpleNamespace(handle=5, paramstring='')

    Router(context, _handlers(calls)).dispatch()

    assert calls == [('main_menu', (), {})]


def test_known_mode_dispatches_with_parsed_parameters(kodi_recorder):
    calls = []
    context = SimpleNamespace(handle=5, paramstring='mode=series_season&series_id=s1&season_id=2')

    Router(context, _handlers(calls)).dispatch()

    assert calls == [('show_series_season', ('s1', '2'), {})]
    assert kodi_recorder.set_content == [(5, 'videos')]


def test_my_list_routes_preserve_parameters():
    calls = []
    router = Router(SimpleNamespace(handle=5, paramstring=''), _handlers(calls))

    router.dispatch('mode=my_list_group&group=Movies')
    router.dispatch('mode=toggle_mylist&id=1&type=movie&title=T&thumb=img')

    assert calls == [
        ('browse_my_list_group', ('Movies',), {}),
        ('toggle_mylist', ('1', 'T', 'movie', 'img'), {}),
    ]


def test_unknown_mode_matches_existing_noop_except_content(kodi_recorder):
    calls = []
    context = SimpleNamespace(handle=5, paramstring='mode=unknown')

    Router(context, _handlers(calls)).dispatch()

    assert calls == []
    assert kodi_recorder.set_content == [(5, 'videos')]
