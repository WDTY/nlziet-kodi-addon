from resources.lib.controllers.profile_controller import ProfileController


class FakeProfileApi:
    def __init__(self, result=True, profiles=None):
        self.result = result
        self.profiles = profiles if profiles is not None else [{'id': 'p1', 'displayName': 'Profile One'}]
        self.selected = []
        self.pkce_calls = 0

    def select_profile(self, profile_id):
        self.selected.append(profile_id)
        return self.result

    def get_profiles(self):
        return self.profiles

    def perform_pkce_authorize_and_exchange(self):
        self.pkce_calls += 1
        return {}


def _controller(fake_addon, api, calls=None):
    calls = calls if calls is not None else []
    return ProfileController(
        {'manage_profiles': lambda: calls.append('manage')},
        fake_addon,
        lambda: api,
        lambda **kwargs: api,
        lambda query: 'plugin://profiles',
        71,
        lambda *args, **kwargs: calls.append((args, kwargs)),
        lambda color, text: f"[{color}]{text}",
        lambda key, *args: key,
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


def test_manage_profiles_adds_profile_items(fake_addon, kodi_recorder):
    calls = []
    fake_addon.setSetting('profile_id', 'p1')

    _controller(fake_addon, FakeProfileApi(), calls).manage()

    assert calls == [(('Profile One', {'mode': 'select_profile', 'profile_id': 'p1'}), {
        'is_folder': True,
        'thumb': None,
        'info': {'plotoutline': 'Active'},
    })]
    assert kodi_recorder.ended == [71]


def test_manage_profiles_notifies_when_empty(fake_addon, kodi_recorder):
    api = FakeProfileApi(profiles=[])

    _controller(fake_addon, api).manage()

    assert api.pkce_calls == 1
    assert kodi_recorder.notifications == [('NLZiet', 'no_profiles', 'info')]
