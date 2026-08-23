from resources.lib.controllers.browse_controller import BrowseController
from resources.lib.controllers import browse_controller


class FakeAddon:
    def __init__(self, library_path):
        self.library_path = str(library_path)

    def getSetting(self, key):
        return self.library_path if key == 'library_path' else ''

    def getAddonInfo(self, key):
        return 'plugin.video.nlziet' if key == 'id' else ''


class FakeApi:
    def __init__(self):
        self.calls = []

    def get_series_detail(self, series_id):
        assert series_id == 'series-1'
        return {
            'title': 'A / Series',
            'description': 'Show <plot>',
            'seasons': [{'id': 'season-1', 'episodes_url': 'https://example.test/items'}],
        }

    def get_series_episodes(self, series_id, season_id=None, limit=400):
        self.calls.append((series_id, season_id, limit))
        return []

    def get_items_from_url(self, url):
        assert url == 'https://example.test/items'
        return [{
            'id': 'episode-1',
            'title': 'Episode <one>',
            'description': 'Plot & text',
            'aired_date': '2025-01-02',
        }]


def test_library_export_uses_season_episodes_url_and_writes_kodi_files(tmp_path, monkeypatch):
    api = FakeApi()
    notifications = []
    addon = FakeAddon(tmp_path)
    controller = BrowseController(
        {}, 1, lambda: api, lambda *args, **kwargs: None,
        addon, object, lambda key, *args: key.format(*args) if args else key,
    )
    monkeypatch.setattr(
        browse_controller.xbmcgui,
        'Dialog',
        lambda: type('Dialog', (), {
            'notification': lambda self, *args: notifications.append(args),
        })(),
    )

    controller.export_series_library('series-1')

    show_dir = tmp_path / 'A Series'
    assert api.calls == [('series-1', 'season-1', 1000)]
    assert (show_dir / 'tvshow.nfo').read_text(encoding='utf-8') == (
        '<tvshow>\n<title>A / Series</title>\n<plot>Show &lt;plot&gt;</plot>\n</tvshow>\n'
    )
    assert (show_dir / 'Season 2025' / 'A Series S2025E01.strm').read_text(encoding='utf-8') == (
        'plugin://plugin.video.nlziet?mode=play&id=episode-1\n'
    )
    assert notifications[-1][1] == 'library_exported'
