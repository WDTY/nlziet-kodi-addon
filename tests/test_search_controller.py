from resources.lib.controllers.search_controller import SearchController


class FakeSearchApi:
    def __init__(self, results=None):
        self.results = results
        self.search_calls = []
        self.series_calls = []
        self.movie_calls = 0
        self.channel_calls = 0

    def search(self, query):
        self.search_calls.append(query)
        return self.results or []

    def get_series_list(self, limit=None):
        self.series_calls.append(limit)
        return [{'id': 's1', 'title': 'Needle Series', 'type': 'series'}]

    def get_movies(self):
        self.movie_calls += 1
        return [{'id': 'm1', 'title': 'Needle Movie', 'type': 'movie'}]

    def get_channels(self):
        self.channel_calls += 1
        return [{'id': 'c1', 'title': 'Needle Channel', 'type': 'channel'}]

    def get_content_detail(self, content_id):
        return {'raw': {'type': 'movie'}, 'description': 'Detail'}


def _controller(fake_addon, api, added):
    return SearchController(
        {},
        fake_addon,
        70,
        lambda: api,
        lambda **kwargs: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        lambda item: 'thumb:' + item['id'],
        lambda color, text: f"[{color}]{text}",
        'FFFFFFFF',
    )


def test_search_group_filters_matching_group_without_network(fake_addon, kodi_recorder):
    added = []
    api = FakeSearchApi([
        {'id': 's1', 'title': 'Series Result', 'type': 'series'},
        {'id': 'm1', 'title': 'Movie Result', 'type': 'movie'},
    ])

    _controller(fake_addon, api, added).group('query', 'Movies')

    assert api.search_calls == ['query']
    assert added == [(('Movie Result', {'mode': 'play', 'id': 'm1'}), {
        'is_folder': False,
        'thumb': 'thumb:m1',
        'info': {'title': 'Movie Result', 'plot': 'Detail', 'plotoutline': 'Detail'},
        'content': {'id': 'm1', 'title': 'Movie Result', 'type': 'movie'},
    })]
    assert kodi_recorder.ended == [70]


def test_search_group_uses_fallback_results_without_network(fake_addon):
    added = []
    api = FakeSearchApi([])

    _controller(fake_addon, api, added).group('needle', 'Series')

    assert api.series_calls == [999]
    assert api.movie_calls == 1
    assert api.channel_calls == 1
    assert added[0][0][0] == 'Needle Series'
    assert added[0][0][1] == {'mode': 'series_detail', 'series_id': 's1'}
    assert added[0][1]['is_folder'] is True


def test_search_group_missing_query_notifies(fake_addon, kodi_recorder):
    _controller(fake_addon, FakeSearchApi(), []).group('', 'Movies')

    assert kodi_recorder.notifications == [('NLZiet', 'Missing search query', 'info')]
