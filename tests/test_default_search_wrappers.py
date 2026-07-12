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


class RecordingController:
    calls = []

    def __init__(self, *args, **kwargs):
        self.__class__.calls.append(('init', args, kwargs))

    @classmethod
    def reset(cls):
        cls.calls = []

    def _record(self, name, *args, **kwargs):
        self.__class__.calls.append((name, args, kwargs))
        return name


class FakeBrowseController(RecordingController):
    def series_categories(self):
        return self._record('series_categories')

    def series_genre(self, genre):
        return self._record('series_genre', genre)

    def series(self):
        return self._record('series')

    def series_detail(self, series_id):
        return self._record('series_detail', series_id)

    def series_season(self, series_id, season_id):
        return self._record('series_season', series_id, season_id)

    def tv_shows(self):
        return self._record('tv_shows')

    def tv_genre(self, genre):
        return self._record('tv_genre', genre)

    def movie_categories(self):
        return self._record('movie_categories')

    def movie_genre(self, genre):
        return self._record('movie_genre', genre)

    def placement_row(self, items_url, placement_id, comp_index):
        return self._record('placement_row', items_url, placement_id, comp_index)

    def category(self, content_type):
        return self._record('category', content_type)


class FakeProfileController(RecordingController):
    def manage(self):
        return self._record('manage')

    def select(self, profile_id):
        return self._record('select', profile_id)


class FakeMyListController(RecordingController):
    def list(self):
        return self._record('list')

    def group(self, group):
        return self._record('group', group)

    def toggle(self, item_id, title, type, thumb):
        return self._record('toggle', item_id, title, type, thumb)


class FakeIPTVController(RecordingController):
    def select_channels(self):
        return self._record('select_channels')


class RaisingBrowseController(FakeBrowseController):
    def series(self):
        raise RuntimeError('series failed')


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


def test_default_search_wrappers_pass_expected_dependencies(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'SearchController', FakeSearchController)
    FakeSearchController.calls = []

    default.do_search()
    default.search_group('query', 'Series')

    for call in (FakeSearchController.calls[0], FakeSearchController.calls[2]):
        _, args, kwargs = call
        assert kwargs == {}
        assert args == (
            {},
            default.ADDON,
            default.HANDLE,
            default.get_api_instance,
            default.NLZietAPI,
            default.add_directory_item,
            default._pick_landscape_thumb,
            default._make_color_tag,
            default.EXPIRY_COLOR_RAW,
            default.get_string,
        )


def test_default_browse_wrappers_delegate_without_fetching_api(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'BrowseController', FakeBrowseController)
    monkeypatch.setattr(default, 'get_api_instance', lambda: (_ for _ in ()).throw(AssertionError('API should not be called')))
    FakeBrowseController.reset()

    assert default.browse_series_categories() == 'series_categories'
    assert default.browse_series_genre('drama') == 'series_genre'
    assert default.browse_series() == 'series'
    assert default.show_series_detail('series-1') == 'series_detail'
    assert default.show_series_season('series-1', 'season-2') == 'series_season'
    assert default.browse_tv_shows() == 'tv_shows'
    assert default.browse_tv_genre('news') == 'tv_genre'
    assert default.browse_movie_categories() == 'movie_categories'
    assert default.browse_movie_genre('action') == 'movie_genre'
    assert default.browse_placement_row('items-url', 'placement-1', '3') == 'placement_row'
    assert default.browse_category('channels') == 'category'

    method_calls = [call for call in FakeBrowseController.calls if call[0] != 'init']
    assert method_calls == [
        ('series_categories', (), {}),
        ('series_genre', ('drama',), {}),
        ('series', (), {}),
        ('series_detail', ('series-1',), {}),
        ('series_season', ('series-1', 'season-2'), {}),
        ('tv_shows', (), {}),
        ('tv_genre', ('news',), {}),
        ('movie_categories', (), {}),
        ('movie_genre', ('action',), {}),
        ('placement_row', ('items-url', 'placement-1', '3'), {}),
        ('category', ('channels',), {}),
    ]


def test_default_browse_wrappers_pass_shared_dependencies(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'BrowseController', FakeBrowseController)
    FakeBrowseController.reset()

    default.browse_series()

    _, args, kwargs = FakeBrowseController.calls[0]
    assert kwargs == {}
    assert args == (
        {},
        default.HANDLE,
        default.get_api_instance,
        default.add_directory_item,
        default.ADDON,
        default.NLZietAPI,
        default.get_string,
        default._pick_landscape_thumb,
        default._make_color_tag,
        default.EXPIRY_COLOR_RAW,
        default.get_channels_menu_data,
    )


def test_default_browse_wrappers_create_controller_per_invocation(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'BrowseController', FakeBrowseController)
    FakeBrowseController.reset()

    default.browse_series()
    default.browse_series()

    init_calls = [call for call in FakeBrowseController.calls if call[0] == 'init']
    assert len(init_calls) == 2


def test_default_browse_wrapper_exceptions_are_not_transformed(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'BrowseController', RaisingBrowseController)

    try:
        default.browse_series()
    except RuntimeError as exc:
        assert str(exc) == 'series failed'
    else:
        raise AssertionError('expected RuntimeError')


def test_default_profile_wrappers_delegate_and_pass_dependencies(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'ProfileController', FakeProfileController, raising=False)
    monkeypatch.setattr(default, 'get_api_instance', lambda: (_ for _ in ()).throw(AssertionError('API should not be called')))
    FakeProfileController.reset()

    assert default.manage_profiles() == 'manage'
    assert default.select_profile('profile-1') == 'select'

    assert FakeProfileController.calls[1] == ('manage', (), {})
    assert FakeProfileController.calls[3] == ('select', ('profile-1',), {})

    _, manage_args, manage_kwargs = FakeProfileController.calls[0]
    assert manage_kwargs == {}
    assert manage_args == (
        {},
        default.ADDON,
        default.get_api_instance,
        default.NLZietAPI,
        default.build_url,
        default.HANDLE,
        default.add_directory_item,
        default._make_color_tag,
        default.get_string,
    )

    _, select_args, select_kwargs = FakeProfileController.calls[2]
    assert select_kwargs == {}
    assert select_args == (
        {'manage_profiles': default.manage_profiles},
        default.ADDON,
        default.get_api_instance,
        default.NLZietAPI,
        default.build_url,
        default.HANDLE,
        default.add_directory_item,
        default._make_color_tag,
        default.get_string,
    )


def test_default_mylist_wrappers_delegate_and_pass_dependencies(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'MyListController', FakeMyListController)
    monkeypatch.setattr(default, 'get_api_instance', lambda: (_ for _ in ()).throw(AssertionError('API should not be called')))
    FakeMyListController.reset()

    assert default.browse_my_list() == 'list'
    assert default.browse_my_list_group('Movies') == 'group'
    assert default.toggle_mylist('item-1', 'Title', 'movie', 'thumb.jpg') == 'toggle'

    method_calls = [call for call in FakeMyListController.calls if call[0] != 'init']
    assert method_calls == [
        ('list', (), {}),
        ('group', ('Movies',), {}),
        ('toggle', ('item-1', 'Title', 'movie', 'thumb.jpg'), {}),
    ]

    for call in FakeMyListController.calls:
        if call[0] != 'init':
            continue
        _, args, kwargs = call
        assert kwargs == {}
        assert args == (
            {},
            default.ADDON,
            default.HANDLE,
            default.get_api_instance,
            default.NLZietAPI,
            default.add_directory_item,
            default._pick_landscape_thumb,
            default.get_string,
        )


def test_default_iptv_wrapper_delegates_without_fetching_api(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default, 'IPTVController', FakeIPTVController)
    monkeypatch.setattr(default, 'get_api_instance', lambda: (_ for _ in ()).throw(AssertionError('API should not be called')))
    FakeIPTVController.reset()

    assert default.select_iptv_channels() == 'select_channels'

    assert FakeIPTVController.calls == [
        ('init', (default.get_api_instance,), {}),
        ('select_channels', (), {}),
    ]


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
