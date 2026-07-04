from resources.lib.controllers.profile_controller import ProfileController


class FakeProfileApi:
    def __init__(self, result=True):
        self.result = result
        self.selected = []

    def select_profile(self, profile_id):
        self.selected.append(profile_id)
        return self.result

    def get_profiles(self):
        return [{'id': 'p1', 'displayName': 'Profile One'}]


def _controller(fake_addon, api, calls=None):
    calls = calls if calls is not None else []
    return ProfileController(
        {'manage_profiles': lambda: calls.append('manage')},
        fake_addon,
        lambda: api,
        lambda **kwargs: api,
        lambda query: 'plugin://profiles',
    )


def test_select_profile_persists_name_and_updates_container(fake_addon, kodi_recorder):
    api = FakeProfileApi()

    _controller(fake_addon, api).select('p1')

    assert api.selected == ['p1']
    assert fake_addon.getSetting('profile_id') == 'p1'
    assert fake_addon.getSetting('profile_name') == 'Profile One'
    assert kodi_recorder.notifications == [('NLZiet', 'Profile switched to Profile One', 'info')]
    assert kodi_recorder.executed == ['Container.Update(plugin://profiles,replace)']


def test_select_profile_missing_id_notifies(fake_addon, kodi_recorder):
    _controller(fake_addon, FakeProfileApi()).select('')

    assert kodi_recorder.notifications == [('NLZiet', 'Missing profile id', 'error')]


def test_select_profile_failure_notifies(fake_addon, kodi_recorder):
    _controller(fake_addon, FakeProfileApi(result=False)).select('p1')

    assert kodi_recorder.notifications == [('NLZiet', 'Profile switch failed', 'error')]
    assert kodi_recorder.executed == ['Container.Update(plugin://profiles,replace)']
