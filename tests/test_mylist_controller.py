from resources.lib.controllers.mylist_controller import MyListController


class FakeApi:
    def __init__(self, items=None):
        self.items = items or []
        self.added = []
        self.removed = []
        self.detail_calls = []

    def get_my_list(self):
        return self.items

    def is_in_my_list(self, item_id):
        return False

    def add_to_my_list(self, item):
        self.added.append(item)
        return True

    def remove_from_my_list(self, item_id):
        self.removed.append(item_id)
        return True

    def get_content_detail(self, item_id):
        self.detail_calls.append(item_id)
        return {'type': 'movie'}


def _controller(fake_addon, api, added):
    return MyListController(
        {},
        fake_addon,
        44,
        lambda: api,
        lambda **kwargs: api,
        lambda *args, **kwargs: added.append((args, kwargs)),
        lambda item: 'thumb:' + item['id'],
        lambda key, *args: key,
    )


def test_overview_groups_items_without_network(fake_addon, kodi_recorder):
    added = []
    api = FakeApi([
        {'id': 's1', 'title': 'Series', 'type': 'series'},
        {'id': 'm1', 'title': 'Movie', 'type': 'movie'},
        {'id': 'x1', 'title': 'Other', 'type': 'clip'},
    ])

    _controller(fake_addon, api, added).list()

    labels = [call[0][0] for call in added]
    assert labels == ['Series: 1 found', 'Movies: 1 found', 'Other: 1 found']
    assert kodi_recorder.ended == [44]


def test_group_route_filters_movies(fake_addon):
    added = []
    api = FakeApi([
        {'id': 's1', 'title': 'Series', 'type': 'series'},
        {'id': 'm1', 'title': 'Movie', 'type': 'movie'},
    ])

    _controller(fake_addon, api, added).group('Movies')

    assert len(added) == 1
    assert added[0][0][0] == 'Movie'
    assert added[0][0][1] == {'mode': 'play', 'id': 'm1'}
    assert added[0][1]['is_folder'] is False


def test_toggle_passes_item_id_and_content_type(fake_addon, kodi_recorder):
    added = []
    api = FakeApi()

    _controller(fake_addon, api, added).toggle('m1', 'Movie', 'movie', 'poster.jpg')

    assert api.added == [{
        'id': 'm1',
        'title': 'Movie',
        'type': 'movie',
        'posterUrl': 'poster.jpg',
    }]
    assert kodi_recorder.executed == ['Container.Refresh']
