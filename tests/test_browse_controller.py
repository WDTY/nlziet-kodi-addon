from resources.lib.controllers.browse_controller import BrowseController


class FakeBrowseApi:
    def __init__(self):
        self.genre_calls = []

    def get_movies_by_genre(self, genre):
        self.genre_calls.append(genre)
        return [{
            'id': 'm1',
            'title': 'Movie',
            'description': 'Description',
            'expires_in': 'soon',
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

    assert api.genre_calls == [None]
    assert added[0][0][0] == 'Movie'
    assert added[0][0][1] == {'mode': 'play', 'id': 'm1'}
    assert added[0][1]['is_folder'] is False
    assert added[0][1]['thumb'] == 'thumb:m1'
    assert kodi_recorder.ended == [55]
