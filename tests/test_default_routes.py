import pytest

from resources.lib.compat.default_routes import build_compatibility_handlers


EXPECTED_KEYS = {
    'main_menu', 'do_login', 'do_search', 'manage_profiles',
    'browse_my_list', 'browse_my_list_group', 'toggle_mylist',
    'select_profile', 'apply_profile', 'browse_series', 'do_logout',
    'confirm_logout', 'refresh_account_info', 'search_group',
    'show_series_detail', 'show_series_season', 'browse_placement_row',
    'browse_tv_shows', 'browse_tv_genre', 'browse_series_categories',
    'browse_series_genre', 'browse_movie_categories',
    'browse_movie_genre', 'browse_category', 'play_item',
    'select_iptv_channels',
}


def _handler(name):
    def fail_if_called(*args, **kwargs):
        raise AssertionError(f'{name} should not be called')

    return fail_if_called


def _build_named_handlers():
    return {key: _handler(key) for key in EXPECTED_KEYS}


def test_build_compatibility_handlers_returns_expected_key_set():
    callables = _build_named_handlers()

    handlers = build_compatibility_handlers(**callables)

    assert set(handlers) == EXPECTED_KEYS


@pytest.mark.parametrize('key', sorted(EXPECTED_KEYS))
def test_build_compatibility_handlers_preserves_callable_identity(key):
    callables = _build_named_handlers()

    handlers = build_compatibility_handlers(**callables)

    assert handlers[key] is callables[key]


def test_build_compatibility_handlers_does_not_invoke_handlers():
    callables = _build_named_handlers()

    build_compatibility_handlers(**callables)
