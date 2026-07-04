from resources.lib.controllers.browse_controller import BrowseController


class FakeBrowseApi:
    def __init__(self):
        self.genre_calls = []
        self.item_url_calls = []
        self.placement_calls = []
        self.placement_rows = None
        self.series_list_calls = 0
        self.episode_calls = []
        self.episodes = None

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
        if self.placement_rows is not None:
            return self.placement_rows
        return [{
            'items': [{
                'item': {
                    'seriesId': 'p1',
                    'title': 'Placement Item',
                    'summary': 'Summary',
                },
            }],
        }]

    def get_series_list(self):
        self.series_list_calls += 1
        return [{
            'id': 's3',
            'title': 'Fallback Series',
            'description': 'Description',
        }]

    def get_series_episodes(self, series_id, season_id=None, limit=None):
        self.episode_calls.append((series_id, season_id, limit))
        if self.episodes is not None:
            return self.episodes
        return [{
            'id': 'ep1',
            'title': 'Episode Title',
            'subtitle': 'S1:A2 Episode Subtitle',
            'description': 'Episode description',
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


def test_series_prefers_placement_rows_without_network(fake_addon, kodi_recorder):
    added = []
    api = FakeBrowseApi()
    api.placement_rows = [
        {'title': 'Series', 'id': 'skip-this'},
        {'title': 'Genre row', 'id': 'explore-series-genres'},
        {'title': 'Drama', 'itemsUrl': 'https://example.test/drama'},
        {'title': 'Inline'},
    ]

    BrowseController(
        {},
        60,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        fake_addon,
        lambda **kwargs: api,
        lambda key, *args: key,
        lambda item: 'thumb:' + item['id'],
        lambda color, text: f"[{color}]{text}",
        'FFFFFFFF',
    ).series()

    assert api.placement_calls == ['explore-series']
    assert [call[0][0] for call in added] == ['Drama', 'Inline']
    assert added[0][0][1] == {'mode': 'placement_row', 'items_url': 'https://example.test/drama'}
    assert added[1][0][1] == {'mode': 'placement_row', 'placement_id': 'explore-series', 'comp_index': '3'}
    assert kodi_recorder.ended == [60]


def test_series_falls_back_to_series_list_without_network(fake_addon, kodi_recorder):
    added = []
    api = FakeBrowseApi()
    api.placement_rows = []

    BrowseController(
        {},
        61,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        fake_addon,
        lambda **kwargs: api,
        lambda key, *args: key,
        lambda item: 'thumb:' + item['id'],
        lambda color, text: f"[{color}]{text}",
        'FFFFFFFF',
    ).series()

    assert api.series_list_calls == 1
    assert added[0][0][0] == 'Fallback Series'
    assert added[0][0][1] == {'mode': 'series_detail', 'series_id': 's3'}
    assert added[0][1]['is_folder'] is True
    assert kodi_recorder.ended == [61]


def test_series_season_adds_episode_items_without_network(fake_addon, kodi_recorder):
    added = []
    api = FakeBrowseApi()

    BrowseController(
        {},
        62,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        fake_addon,
        lambda **kwargs: api,
        lambda key, *args: key,
        lambda item: 'thumb:' + item['id'],
    ).series_season('series-1', 'season-1')

    assert api.episode_calls == [('series-1', 'season-1', 400)]
    assert added[0][0][0] == 'S1:A2 Episode Subtitle'
    assert added[0][0][1] == {'mode': 'play', 'id': 'ep1'}
    assert added[0][1]['is_folder'] is False
    assert kodi_recorder.ended == [62]


def test_series_season_falls_back_to_items_url_without_network(fake_addon):
    added = []
    api = FakeBrowseApi()
    api.episodes = []

    BrowseController(
        {},
        63,
        lambda: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        fake_addon,
        lambda **kwargs: api,
        lambda key, *args: key,
        lambda item: 'thumb:' + item['id'],
    ).series_season('series-1', 'https://example.test/episodes')

    assert api.item_url_calls == ['https://example.test/episodes']
    assert added[0][0][0] == 'URL Item'


def test_series_season_missing_series_id_notifies(fake_addon, kodi_recorder):
    BrowseController(
        {},
        64,
        lambda: FakeBrowseApi(),
        lambda *args, **kwargs: None,
        fake_addon,
        lambda **kwargs: FakeBrowseApi(),
        lambda key, *args: key,
        lambda item: 'thumb',
    ).series_season('', 'season-1')

    assert kodi_recorder.notifications == [('NLZiet', 'missing_series_id', 'error')]
