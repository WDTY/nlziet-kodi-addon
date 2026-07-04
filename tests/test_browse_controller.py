from resources.lib.controllers.browse_controller import BrowseController


class FakeBrowseApi:
    def __init__(self):
        self.genre_calls = []
        self.item_url_calls = []
        self.placement_calls = []

    def get_series_by_genre(self, genre):
        self.genre_calls.append(('series', genre))
        return [{
            'id': 's1',
            'title': 'Series',
            'type': 'Series',
            'description': 'Description',
        }]

    def get_movies_by_genre(self, genre):
        self.genre_calls.append(('movies', genre))
        return [{
            'id': 'm1',
            'title': 'Movie',
            'description': 'Description',
            'expires_in': 'soon',
        }]

    def get_videos_by_genre(self, genre=None, limit=None):
        self.genre_calls.append(('tv', genre, limit))
        return [
            {
                'id': 'e1',
                'title': 'Episode Title',
                'subtitle': 'Episode Subtitle',
                'type': 'episode',
            },
            {
                'id': 's2',
                'title': 'Series Title',
                'type': 'series',
            },
        ]

    def get_items_from_url(self, url):
        self.item_url_calls.append(url)
        return [{
            'id': 'u1',
            'title': 'URL Item',
            'description': 'Description',
        }]

    def get_placement_rows(self, placement_id):
        self.placement_calls.append(placement_id)
        return [{
            'items': [{
                'item': {
                    'seriesId': 'p1',
                    'title': 'Placement Item',
                    'summary': 'Summary',
                },
            }],
        }]


def test_movie_genre_adds_playable_items_without_network(kodi_recorder):
    added = []
    api = FakeBrowseApi()

    BrowseController(
        {},
        55,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        pick_landscape_thumb=lambda item: 'thumb:' + item['id'],
        make_color_tag=lambda color, text: f"[{color}]{text}",
        expiry_color_raw='FFFFFFFF',
    ).movie_genre('all')

    assert api.genre_calls == [('movies', None)]
    assert added[0][0][0] == 'Movie'
    assert added[0][0][1] == {'mode': 'play', 'id': 'm1'}
    assert added[0][1]['is_folder'] is False
    assert added[0][1]['thumb'] == 'thumb:m1'
    assert kodi_recorder.ended == [55]


def test_series_genre_adds_series_folders_without_network(kodi_recorder):
    added = []
    api = FakeBrowseApi()

    BrowseController(
        {},
        56,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        pick_landscape_thumb=lambda item: 'thumb:' + item['id'],
        make_color_tag=lambda color, text: f"[{color}]{text}",
        expiry_color_raw='FFFFFFFF',
    ).series_genre('drama')

    assert api.genre_calls == [('series', 'drama')]
    assert added[0][0][0] == 'Series'
    assert added[0][0][1] == {'mode': 'series_detail', 'series_id': 's1'}
    assert added[0][1]['is_folder'] is True
    assert added[0][1]['thumb'] == 'thumb:s1'
    assert kodi_recorder.ended == [56]


def test_tv_genre_routes_series_as_folders_without_network(kodi_recorder):
    added = []
    api = FakeBrowseApi()

    BrowseController(
        {},
        57,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        pick_landscape_thumb=lambda item: 'thumb:' + item['id'],
        make_color_tag=lambda color, text: f"[{color}]{text}",
        expiry_color_raw='FFFFFFFF',
    ).tv_genre('all')

    assert api.genre_calls == [('tv', None, 999)]
    assert added[0][0][0] == 'Episode Subtitle'
    assert added[0][0][1] == {'mode': 'play', 'id': 'e1'}
    assert added[0][1]['is_folder'] is False
    assert added[1][0][0] == 'Series Title'
    assert added[1][0][1] == {'mode': 'series_detail', 'series_id': 's2'}
    assert added[1][1]['is_folder'] is True
    assert kodi_recorder.ended == [57]


def test_placement_row_uses_direct_items_url_without_network(fake_addon, kodi_recorder):
    added = []
    api = FakeBrowseApi()

    BrowseController(
        {},
        58,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        fake_addon,
        lambda **kwargs: api,
        lambda key, *args: key,
        lambda item: 'thumb:' + item['id'],
        lambda color, text: f"[{color}]{text}",
        'FFFFFFFF',
    ).placement_row('https://example.test/items', None, None)

    assert api.item_url_calls == ['https://example.test/items']
    assert added[0][0][0] == 'URL Item'
    assert added[0][0][1] == {'mode': 'series_detail', 'series_id': 'u1'}
    assert added[0][1]['is_folder'] is True
    assert kodi_recorder.ended == [58]


def test_placement_row_uses_inline_items_without_network(fake_addon, kodi_recorder):
    added = []
    api = FakeBrowseApi()

    BrowseController(
        {},
        59,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        fake_addon,
        lambda **kwargs: api,
        lambda key, *args: key,
        lambda item: 'thumb:' + item.get('id', item.get('seriesId')),
        lambda color, text: f"[{color}]{text}",
        'FFFFFFFF',
    ).placement_row(None, 'explore-series', '0')

    assert api.placement_calls == ['explore-series']
    assert added[0][0][0] == 'Placement Item'
    assert added[0][0][1] == {'mode': 'series_detail', 'series_id': 'p1'}
    assert added[0][1]['is_folder'] is True
    assert kodi_recorder.ended == [59]
