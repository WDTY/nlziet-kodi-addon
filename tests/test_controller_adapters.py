import subprocess
import sys

import pytest

from resources.lib.compat import controller_adapters


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


class FakeSearchController(RecordingController):
    def search(self):
        return self._record('search')

    def group(self, q, group):
        return self._record('group', q, group)


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


def _dependencies():
    return {
        'addon': 'addon',
        'handle': 7,
        'get_api_instance': 'get-api',
        'api_class': 'api-class',
        'build_url': 'build-url',
        'add_directory_item': 'add-item',
        'pick_landscape_thumb': 'pick-thumb',
        'make_color_tag': 'color-tag',
        'expiry_color_raw': 'FFFFFFFF',
        'get_channels_menu_data': 'channels-menu',
        'get_string': 'get-string',
    }


@pytest.mark.parametrize(
    ('adapter_name', 'controller_method', 'args'),
    [
        ('browse_series_categories', 'series_categories', ()),
        ('browse_series_genre', 'series_genre', ('drama',)),
        ('browse_series', 'series', ()),
        ('show_series_detail', 'series_detail', ('series-1',)),
        ('show_series_season', 'series_season', ('series-1', 'season-2')),
        ('browse_tv_shows', 'tv_shows', ()),
        ('browse_tv_genre', 'tv_genre', ('news',)),
        ('browse_movie_categories', 'movie_categories', ()),
        ('browse_movie_genre', 'movie_genre', ('action',)),
        ('browse_placement_row', 'placement_row', ('items-url', 'placement-1', '3')),
        ('browse_category', 'category', ('movies',)),
    ],
)
def test_browse_adapters_delegate_to_expected_method(monkeypatch, adapter_name, controller_method, args):
    monkeypatch.setattr(controller_adapters, 'BrowseController', FakeBrowseController)
    FakeBrowseController.reset()

    result = getattr(controller_adapters, adapter_name)(_dependencies(), *args)

    assert result == controller_method
    assert FakeBrowseController.calls[-1] == (controller_method, args, {})


def test_browse_adapters_create_controller_per_call(monkeypatch):
    monkeypatch.setattr(controller_adapters, 'BrowseController', FakeBrowseController)
    FakeBrowseController.reset()

    controller_adapters.browse_series(_dependencies())
    controller_adapters.browse_series(_dependencies())

    assert [call[0] for call in FakeBrowseController.calls].count('init') == 2


def test_adapter_exceptions_are_not_transformed(monkeypatch):
    class RaisingBrowseController(FakeBrowseController):
        def series(self):
            raise RuntimeError('series failed')

    monkeypatch.setattr(controller_adapters, 'BrowseController', RaisingBrowseController)

    with pytest.raises(RuntimeError, match='series failed'):
        controller_adapters.browse_series(_dependencies())


def test_search_profile_and_mylist_adapters_delegate(monkeypatch):
    monkeypatch.setattr(controller_adapters, 'SearchController', FakeSearchController)
    monkeypatch.setattr(controller_adapters, 'ProfileController', FakeProfileController)
    monkeypatch.setattr(controller_adapters, 'MyListController', FakeMyListController)
    FakeSearchController.reset()
    FakeProfileController.reset()
    FakeMyListController.reset()

    assert controller_adapters.do_search(_dependencies()) == 'search'
    assert controller_adapters.search_group(_dependencies(), 'q', 'Movies') == 'group'
    assert controller_adapters.manage_profiles(_dependencies()) == 'manage'
    assert controller_adapters.select_profile(_dependencies(), 'profile-1', 'manage') == 'select'
    assert controller_adapters.browse_my_list(_dependencies()) == 'list'
    assert controller_adapters.browse_my_list_group(_dependencies(), 'Movies') == 'group'
    assert controller_adapters.toggle_mylist(_dependencies(), 'id', 'Title', 'movie', 'thumb') == 'toggle'

    assert FakeSearchController.calls[-1] == ('group', ('q', 'Movies'), {})
    assert FakeProfileController.calls[-1] == ('select', ('profile-1',), {})
    assert FakeMyListController.calls[-1] == ('toggle', ('id', 'Title', 'movie', 'thumb'), {})


def test_adapter_module_import_does_not_require_kodi_modules():
    code = (
        "import sys\n"
        "import resources.lib.compat.controller_adapters\n"
        "print(any(name.startswith('xbmc') for name in sys.modules))\n"
    )

    completed = subprocess.run(
        [sys.executable, '-c', code],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == 'False'
