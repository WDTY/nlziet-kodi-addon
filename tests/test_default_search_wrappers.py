import importlib
import sys


class FakeSearchController:
    calls = []

    def __init__(self, *args, **kwargs):
        self.calls.append(('init', args, kwargs))

    def search(self):
        self.calls.append(('search', (), {}))
        return 'searched'

    def group(self, q, group):
        self.calls.append(('group', (q, group), {}))
        return 'grouped'


def _import_default(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    monkeypatch.setattr(sys.modules['xbmc'], 'Player', type('FakePlayer', (), {}), raising=False)
    sys.modules.pop('default', None)
    return importlib.import_module('default')


def test_default_search_wrappers_are_callable(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'SearchController', FakeSearchController)
    FakeSearchController.calls = []

    assert default.do_search() == 'searched'
    assert default.search_group('query', 'Movies') == 'grouped'

    assert FakeSearchController.calls[0][0] == 'init'
    assert FakeSearchController.calls[1] == ('search', (), {})
    assert FakeSearchController.calls[2][0] == 'init'
    assert FakeSearchController.calls[3] == ('group', ('query', 'Movies'), {})


def test_default_route_wiring_exposes_expected_handlers(monkeypatch):
    default = _import_default(monkeypatch)

    expected = {
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

    assert set(default.get_compatibility_handlers()) == expected
    assert set(default.get_route_handlers()) == expected


def test_default_route_dependencies_are_named(monkeypatch):
    default = _import_default(monkeypatch)

    assert set(default.get_route_dependencies()) == {
        'addon',
        'handle',
        'get_api_instance',
        'api_class',
        'build_url',
        'add_directory_item',
        'pick_landscape_thumb',
        'make_color_tag',
        'expiry_color_raw',
        'get_channels_menu_data',
        'get_string',
    }
