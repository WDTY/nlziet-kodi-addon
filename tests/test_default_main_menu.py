import importlib
import sys


def _import_default(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    monkeypatch.setattr(sys.modules['xbmc'], 'Player', type('FakePlayer', (), {}), raising=False)
    sys.modules.pop('default', None)
    return importlib.import_module('default')


class FakeThread:
    created = []

    def __init__(self, target=None, args=(), daemon=None):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.started = False
        self.__class__.created.append(self)

    def start(self):
        self.started = True


def _patch_main_menu_edges(monkeypatch, default, logged_in):
    items = []
    properties = []

    def add_directory_item(title, query, is_folder=True, thumb=None, info=None, content=None):
        items.append({
            'title': title,
            'query': query,
            'is_folder': is_folder,
            'thumb': thumb,
            'info': info,
            'content': content,
        })

    def exists(path):
        normalized = path.replace('\\', '/')
        return '/resources/media/menu_' in normalized or normalized.endswith('/resources/media/background.jpg')

    FakeThread.created = []
    monkeypatch.setattr(default, '_check_and_handle_token_expiry', lambda: True)
    monkeypatch.setattr(default, '_is_logged_in', lambda: logged_in)
    monkeypatch.setattr(default, 'get_api_instance', lambda: (_ for _ in ()).throw(AssertionError('API should not be called')))
    monkeypatch.setattr(default, 'add_directory_item', add_directory_item)
    monkeypatch.setattr(default.threading, 'Thread', FakeThread)
    monkeypatch.setattr(default.os.path, 'exists', exists)
    monkeypatch.setattr(default.xbmcplugin, 'setProperty', lambda handle, key, value: properties.append((handle, key, value)), raising=False)

    return items, properties, FakeThread.created


def _queries(items):
    return [item['query'] for item in items]


def test_build_main_menu_entries_logged_out_returns_login_entry(monkeypatch):
    default = _import_default(monkeypatch)

    entries = default.build_main_menu_entries(
        False,
        'C:/addon',
        lambda name: f'icon:{name}',
        get_label=lambda key: f'label:{key}',
    )

    assert entries == [
        {
            'title': 'label:login',
            'query': {'mode': 'login'},
            'thumb': 'icon:login',
        },
    ]


def test_build_main_menu_entries_logged_in_returns_protected_entries(monkeypatch):
    default = _import_default(monkeypatch)
    monkeypatch.setattr(default.os.path, 'exists', lambda path: path.replace('\\', '/').endswith('/resources/media/menu_logout.png'))

    entries = default.build_main_menu_entries(
        True,
        'C:/addon',
        lambda name: f'icon:{name}',
        get_label=lambda key: f'label:{key}',
    )

    assert [entry['query'] for entry in entries] == [
        {'mode': 'logout_confirm'},
        {'mode': 'profiles'},
        {'mode': 'search'},
        {'mode': 'my_list'},
        {'mode': 'browse_series_categories'},
        {'mode': 'browse_tv_shows'},
        {'mode': 'browse', 'type': 'documentary'},
        {'mode': 'browse_movie_categories'},
        {'mode': 'browse', 'type': 'channels'},
    ]
    assert [entry['title'] for entry in entries] == [
        'label:sign_out',
        'label:manage_profiles',
        'label:search',
        'label:my_list',
        'label:series',
        'label:tv_shows',
        'label:documentary',
        'label:movies',
        'label:channels',
    ]
    assert entries[0]['thumb'].replace('\\', '/') == 'C:/addon/resources/media/menu_logout.png'
    assert entries[1]['thumb'] == 'icon:profiles'
    assert entries[-1]['thumb'] == 'icon:tv'


def test_main_menu_logged_out_shows_login_only_and_completes(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    items, properties, threads = _patch_main_menu_edges(monkeypatch, default, logged_in=False)

    default.main_menu()

    queries = _queries(items)
    assert queries == [{'mode': 'login'}]
    assert {'mode': 'logout_confirm'} not in queries
    assert not any(query.get('mode') in {
        'profiles',
        'search',
        'my_list',
        'browse_series_categories',
        'browse_tv_shows',
        'browse_movie_categories',
    } for query in queries)
    assert not any(query.get('type') in {'documentary', 'channels'} for query in queries)
    assert items[0]['thumb'].replace('\\', '/').endswith('/resources/media/menu_login.png')
    assert len(properties) == 1
    handle, key, value = properties[0]
    assert (handle, key) == (default.HANDLE, 'fanart')
    assert value.replace('\\', '/') == 'C:/addon/resources/media/background.jpg'
    assert kodi_recorder.ended == [default.HANDLE]
    assert len(threads) == 1
    assert threads[0].target is default.refresh_account_info
    assert threads[0].args == (False,)
    assert threads[0].daemon is True
    assert threads[0].started is True


def test_main_menu_logged_in_shows_protected_entries_in_order(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    items, properties, threads = _patch_main_menu_edges(monkeypatch, default, logged_in=True)

    default.main_menu()

    queries = _queries(items)
    assert queries == [
        {'mode': 'logout_confirm'},
        {'mode': 'profiles'},
        {'mode': 'search'},
        {'mode': 'my_list'},
        {'mode': 'browse_series_categories'},
        {'mode': 'browse_tv_shows'},
        {'mode': 'browse', 'type': 'documentary'},
        {'mode': 'browse_movie_categories'},
        {'mode': 'browse', 'type': 'channels'},
    ]
    assert {'mode': 'login'} not in queries
    assert items[0]['thumb'].replace('\\', '/').endswith('/resources/media/menu_logout.png')
    assert items[1]['thumb'].replace('\\', '/').endswith('/resources/media/menu_profiles.png')
    assert items[2]['thumb'].replace('\\', '/').endswith('/resources/media/menu_search.png')
    assert items[3]['thumb'].replace('\\', '/').endswith('/resources/media/menu_mylist.png')
    assert items[-1]['thumb'].replace('\\', '/').endswith('/resources/media/menu_tv.png')
    assert len(properties) == 1
    handle, key, value = properties[0]
    assert (handle, key) == (default.HANDLE, 'fanart')
    assert value.replace('\\', '/') == 'C:/addon/resources/media/background.jpg'
    assert kodi_recorder.ended == [default.HANDLE]
    assert len(threads) == 1


def test_main_menu_falls_back_when_xbmc_translate_path_is_missing(monkeypatch, kodi_recorder):
    default = _import_default(monkeypatch)
    monkeypatch.delattr(default.xbmc, 'translatePath', raising=False)
    items, properties, threads = _patch_main_menu_edges(monkeypatch, default, logged_in=False)

    default.main_menu()

    assert _queries(items) == [{'mode': 'login'}]
    assert items[0]['thumb'].replace('\\', '/').endswith('/resources/media/menu_login.png')
    assert len(properties) == 1
    handle, key, value = properties[0]
    assert (handle, key) == (default.HANDLE, 'fanart')
    assert value.replace('\\', '/') == 'C:/addon/resources/media/background.jpg'
    assert kodi_recorder.ended == [default.HANDLE]
    assert len(threads) == 1
