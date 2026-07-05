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


def test_default_search_wrappers_are_callable(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.nlziet', '42', ''])
    monkeypatch.setattr(sys.modules['xbmc'], 'Player', type('FakePlayer', (), {}), raising=False)
    sys.modules.pop('default', None)
    default = importlib.import_module('default')
    monkeypatch.setattr(default, 'SearchController', FakeSearchController)
    FakeSearchController.calls = []

    assert default.do_search() == 'searched'
    assert default.search_group('query', 'Movies') == 'grouped'

    assert FakeSearchController.calls[0][0] == 'init'
    assert FakeSearchController.calls[1] == ('search', (), {})
    assert FakeSearchController.calls[2][0] == 'init'
    assert FakeSearchController.calls[3] == ('group', ('query', 'Movies'), {})
