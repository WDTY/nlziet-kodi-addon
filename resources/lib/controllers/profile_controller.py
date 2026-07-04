import os

import xbmc
import xbmcgui
import xbmcplugin


class ProfileController:
    """Profile route adapter."""

    def __init__(self, handlers, addon=None, get_api_instance=None,
                 api_class=None, build_url=None, handle=None,
                 add_directory_item=None, make_color_tag=None,
                 get_string=None):
        self._handlers = handlers
        self._addon = addon
        self._get_api_instance = get_api_instance
        self._api_class = api_class
        self._build_url = build_url
        self._handle = handle
        self._add_directory_item = add_directory_item
        self._make_color_tag = make_color_tag
        self._get_string = get_string

    def manage(self):
        if (self._addon and self._get_api_instance and self._handle is not None
                and self._add_directory_item and self._make_color_tag
                and self._get_string):
            """List available profiles and let the user switch the active profile.

            This renders a directory of profiles where the currently active profile
            is displayed in green. Selecting a profile will activate it and re-open
            the list so the active profile remains highlighted until another is
            chosen.
            """
            api = self._get_api_instance()
            profiles = api.get_profiles()
            # Try to obtain tokens if profiles empty
            if not profiles:
                try:
                    api.perform_pkce_authorize_and_exchange()
                    profiles = api.get_profiles() or []
                except Exception:
                    profiles = profiles or []

            if not profiles:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('no_profiles'), xbmcgui.NOTIFICATION_INFO)
                return

            current_pid = self._addon.getSetting('profile_id') or ''
            # Build a directory listing: active profile is colored/marked
            for p in profiles:
                name = p.get('displayName') or p.get('name') or p.get('profileName') or p.get('id') or str(p)
                pid = p.get('id') or p.get('profileId') or p.get('profile_id') or name
                try:
                    # Compare as strings to be tolerant of types
                    is_active = str(pid) == str(current_pid)
                except Exception:
                    is_active = False

                # Build a local path to bundled icons
                try:
                    addon_path = self._addon.getAddonInfo('path') or ''
                except Exception:
                    addon_path = ''

                # Prefer a PNG asset, then SVG, then the addon's icon.png
                candidates = [
                    os.path.join(addon_path, 'resources', 'media', 'emoji_google_active.png'),
                    os.path.join(addon_path, 'resources', 'media', 'emoji_google_active.svg'),
                    os.path.join(addon_path, 'icon.png'),
                ]
                active_icon = None
                for c in candidates:
                    try:
                        if c and os.path.exists(c):
                            active_icon = c
                            break
                    except Exception:
                        continue

                # For active profile use the bundled Google-style icon as the thumb
                if is_active:
                    # Keep the color tag when an icon is available; no emoji prefix
                    title = self._make_color_tag('FF27AE60', name) if active_icon else name
                    thumb = active_icon
                    info_obj = {'plotoutline': 'Active'}
                else:
                    # Use bundled inactive icon when available so inactive profiles show an icon
                    candidates_inactive = [
                        os.path.join(addon_path, 'resources', 'media', 'emoji_google_inactive.png'),
                        os.path.join(addon_path, 'resources', 'media', 'emoji_google_inactive.svg'),
                        os.path.join(addon_path, 'icon.png'),
                    ]
                    inactive_icon = None
                    for c in candidates_inactive:
                        try:
                            if c and os.path.exists(c):
                                inactive_icon = c
                                break
                        except Exception:
                            continue
                    title = name
                    thumb = inactive_icon
                    info_obj = None

                # Selecting an item triggers the 'select_profile' route with the profile id
                self._add_directory_item(title, {'mode': 'select_profile', 'profile_id': str(pid)}, is_folder=True, thumb=thumb, info=info_obj)

            xbmcplugin.endOfDirectory(self._handle)
            return None
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
