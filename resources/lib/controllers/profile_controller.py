import xbmc
import xbmcgui


class ProfileController:
    """Profile route adapter."""

    def __init__(self, handlers, addon=None, get_api_instance=None,
                 api_class=None, build_url=None):
        self._handlers = handlers
        self._addon = addon
        self._get_api_instance = get_api_instance
        self._api_class = api_class
        self._build_url = build_url

    def manage(self):
        return self._handlers['manage_profiles']()

    def select(self, profile_id):
        if (self._addon and self._get_api_instance and self._api_class
                and self._build_url):
            if not profile_id:
                xbmcgui.Dialog().notification('NLZiet', 'Missing profile id', xbmcgui.NOTIFICATION_ERROR)
                return

            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for faster profile switching
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            try:
                result = api.select_profile(profile_id)
            except Exception as e:
                xbmc.log(f"NLZiet select_profile error: {e}", xbmc.LOGERROR)
                result = None

            if result:
                # persist selection
                try:
                    self._addon.setSetting('profile_id', str(profile_id))
                    # attempt to look up a friendly name
                    profiles = api.get_profiles() or []
                    profile_name = ''
                    for p in profiles:
                        if str(p.get('id')) == str(profile_id) or str(p.get('profileId')) == str(profile_id):
                            profile_name = p.get('displayName') or p.get('name') or p.get('profileName') or ''
                            break
                    self._addon.setSetting('profile_name', profile_name or str(profile_id))
                except Exception:
                    pass
                xbmcgui.Dialog().notification('NLZiet', f'Profile switched to {self._addon.getSetting("profile_name") or profile_id}', xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification('NLZiet', 'Profile switch failed', xbmcgui.NOTIFICATION_ERROR)

            # Replace the current container with the profiles listing so we don't
            # push an extra history entry. This prevents Back from cycling
            # through profile selections and instead returns to the main menu.
            try:
                profiles_url = self._build_url({'mode': 'profiles'})
                xbmc.executebuiltin('Container.Update(%s,replace)' % profiles_url)
            except Exception:
                # Fallback: if the builtin fails, render profiles directly.
                self._handlers['manage_profiles']()
            return None
        return self._handlers['select_profile'](profile_id)

    def apply(self):
        return self._handlers['apply_profile']()
