from resources.lib.controllers.search_controller import SearchController
from resources.lib.i18n import get_string
import xbmc


class FakeKeyboard:
    confirmed = True
    text = ''

    def __init__(self, default, heading):
        self.default = default
        self.heading = heading

    def doModal(self):
        return None

    def isConfirmed(self):
        return self.confirmed

    def getText(self):
        return self.text


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
        get_string,
    )


def _set_keyboard(monkeypatch, confirmed=True, text='query'):
    FakeKeyboard.confirmed = confirmed
    FakeKeyboard.text = text
    monkeypatch.setattr(xbmc, 'Keyboard', FakeKeyboard, raising=False)


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

    assert kodi_recorder.notifications == [('NLZiet', 'Zoekopdracht ontbreekt', 'info')]


def test_search_cancel_does_not_call_api(fake_addon, monkeypatch):
    added = []
    api = FakeSearchApi([{'id': 'm1', 'title': 'Movie', 'type': 'movie'}])
    _set_keyboard(monkeypatch, confirmed=False, text='movie')

    _controller(fake_addon, api, added).search()

    assert api.search_calls == []
    assert added == []


def test_search_groups_multiple_result_types(fake_addon, kodi_recorder, monkeypatch):
    added = []
    api = FakeSearchApi([
        {'id': 's1', 'title': 'Series Result', 'type': 'series'},
        {'id': 'm1', 'title': 'Movie Result', 'type': 'movie'},
    ])
    _set_keyboard(monkeypatch, text='mix')

    _controller(fake_addon, api, added).search()

    assert [call[0][0] for call in added] == ['Series: 1 gevonden', 'Films: 1 gevonden']
    assert added[0][0][1] == {'mode': 'search_group', 'q': 'mix', 'group': 'Series'}
    assert added[1][0][1] == {'mode': 'search_group', 'q': 'mix', 'group': 'Movies'}
    assert all(call[1]['is_folder'] is True for call in added)
    assert kodi_recorder.ended == [70]


def test_search_single_group_adds_direct_results(fake_addon, kodi_recorder, monkeypatch):
    added = []
    api = FakeSearchApi([
        {'id': 'm1', 'title': 'Movie Result', 'type': 'movie', 'description': 'Description'},
    ])
    _set_keyboard(monkeypatch, text='movie')

    _controller(fake_addon, api, added).search()

    assert added[0][0][0] == 'Films: Movie Result'
    assert added[0][0][1] == {'mode': 'play', 'id': 'm1'}
    assert added[0][1]['is_folder'] is False
    assert kodi_recorder.ended == [70]


def test_search_uses_fallback_results(fake_addon, monkeypatch):
    added = []
    api = FakeSearchApi([])
    _set_keyboard(monkeypatch, text='needle')

    _controller(fake_addon, api, added).search()

    assert api.series_calls == [999]
    assert api.movie_calls == 1
    assert api.channel_calls == 1
    assert [call[0][0] for call in added] == [
        'Series: 1 gevonden',
        'Films: 1 gevonden',
        'Kanalen: 1 gevonden',
    ]


def test_search_no_results_notifies(fake_addon, kodi_recorder, monkeypatch):
    added = []
    api = FakeSearchApi([])
    api.get_series_list = lambda limit=None: []
    api.get_movies = lambda: []
    api.get_channels = lambda: []
    _set_keyboard(monkeypatch, text='nothing')

    _controller(fake_addon, api, added).search()

    assert added == []
    assert kodi_recorder.notifications == [('NLZiet', 'Geen resultaten gevonden voor "nothing"', 'info')]
    assert kodi_recorder.ended == [70]
