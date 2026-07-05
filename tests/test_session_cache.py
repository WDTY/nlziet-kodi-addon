import pytest

from resources.lib import session_cache


class FakeApi:
    instances = []

    def __init__(self, username='', password=''):
        self.username = username
        self.password = password
        self.channel_calls = 0
        self.epg_calls = []
        self.channels = [{'id': 'c1'}, {'id': 'c2'}]

        self.instances.append(self)

    def get_channels(self):
        self.channel_calls += 1
        return self.channels

    def get_current_programs(self, channel_ids):
        self.epg_calls.append(channel_ids)
        return {'c1': [{'title': 'Now'}]}


@pytest.fixture(autouse=True)
def reset_session_cache():
    session_cache.clear_api_cache()
    FakeApi.instances = []
    yield
    session_cache.clear_api_cache()


def test_get_api_instance_reuses_fresh_cache(fake_addon, monkeypatch):
    times = iter([1000, 1010])
    fake_addon.setSetting('username', 'user')
    fake_addon.setSetting('password', 'pass')
    monkeypatch.setattr(session_cache.time, 'time', lambda: next(times))

    first = session_cache.get_api_instance(fake_addon, FakeApi)
    second = session_cache.get_api_instance(fake_addon, FakeApi)

    assert first is second
    assert len(FakeApi.instances) == 1
    assert first.username == 'user'
    assert first.password == 'pass'


def test_get_api_instance_refreshes_after_timeout(fake_addon, monkeypatch):
    times = iter([1000, 1401])
    monkeypatch.setattr(session_cache.time, 'time', lambda: next(times))

    first = session_cache.get_api_instance(fake_addon, FakeApi)
    second = session_cache.get_api_instance(fake_addon, FakeApi)

    assert first is not second
    assert len(FakeApi.instances) == 2


def test_set_and_clear_api_instance(fake_addon, monkeypatch):
    manual = object()
    monkeypatch.setattr(session_cache.time, 'time', lambda: 1000)

    session_cache.set_api_instance(manual)

    assert session_cache.get_api_instance(fake_addon, FakeApi) is manual

    session_cache.clear_api_cache()

    assert session_cache.get_api_instance(fake_addon, FakeApi) is not manual


def test_get_channels_menu_data_uses_short_lived_cache(monkeypatch):
    api = FakeApi()
    times = iter([1000, 1010])
    monkeypatch.setattr(session_cache.time, 'time', lambda: next(times))

    first = session_cache.get_channels_menu_data(api)
    second = session_cache.get_channels_menu_data(api)

    assert first == second
    assert api.channel_calls == 1
    assert api.epg_calls == [['c1', 'c2']]


def test_clear_api_cache_clears_channel_cache(monkeypatch):
    api = FakeApi()
    times = iter([1000, 1010, 1011])
    monkeypatch.setattr(session_cache.time, 'time', lambda: next(times))

    session_cache.get_channels_menu_data(api)
    session_cache.clear_api_cache()
    session_cache.get_channels_menu_data(api)

    assert api.channel_calls == 2
