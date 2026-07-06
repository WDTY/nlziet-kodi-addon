import sys
import re
import urllib.parse
import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import threading
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from resources.lib.nlziet_api import NLZietAPI
from resources.lib import session_cache
from resources.lib.app_context import AddonContext
from resources.lib.compat import default_helpers, default_routes
from resources.lib.controller_factory import build_route_dependencies, build_route_handlers
from resources.lib.controllers import AuthController, BrowseController, MyListController, PlaybackController, IPTVController, SearchController
from resources.lib.i18n import get_string
from resources.lib.kodi import ui as kodi_ui
from resources.lib.router import Router

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

def get_api_instance():
    return session_cache.get_api_instance(ADDON, NLZietAPI)

def clear_api_cache():
    return session_cache.clear_api_cache()


def set_api_instance(api_instance):
    return session_cache.set_api_instance(api_instance)


def get_channels_menu_data(api_instance):
    return session_cache.get_channels_menu_data(api_instance)

# Raw expiry color to test — change this to 'orange' or a hex like 'FFA500' or
# try the exact raw tag you suggested ('ffoooo66') to experiment.
EXPIRY_COLOR_RAW = default_helpers.EXPIRY_COLOR_RAW


def _make_color_tag(color_raw, text):
    """Return a COLOR tag using the raw value provided by the user.

    We intentionally use the raw value so you can test named colors or hex
    variants; if the skin ignores color tags, we also prefix label2 with an
    emoji marker as a fallback (see code below).
    """
    return default_helpers.make_color_tag(color_raw, text)


def build_url(query):
    return default_helpers.build_url(BASE_URL, query)


def add_directory_item(title, query, is_folder=True, thumb=None, info=None, content=None):
    return kodi_ui.add_directory_item(
        ADDON,
        HANDLE,
        build_url,
        get_api_instance,
        title,
        query,
        is_folder=is_folder,
        thumb=thumb,
        info=info,
        content=content,
    )


def _optimize_image_url(url):
    """Optimize image URLs to request higher-resolution versions for fanart.
    
    The NLZiet image service returns low-res images (1280x720) by default.
    We request a larger resolution to avoid pixelation when displayed as fanart.
    
    Args:
        url: Image URL
        
    Returns:
        Optimized URL requesting higher-resolution image
    """
    return default_helpers.optimize_image_url(url)


def _pick_landscape_thumb(src):
    """Return the best landscape-oriented thumbnail or path for an item.

    Accepts either a string URL/path or a dict-like content item. Prefers
    explicit landscape keys, then common wide/hero/poster keys, and finally
    falls back to any url-like string found on the object.
    """
    return default_helpers.pick_landscape_thumb(src)


def _pick_portrait_thumb(src):
    """Return the best portrait-oriented thumbnail or path for an item.
    
    Portrait images are typically 2:3 aspect ratio (posters/covers).
    Prefers explicit portrait keys, then falls back to landscape or generic thumbnails.
    """
    return default_helpers.pick_portrait_thumb(src)


def _set_smart_artwork(li, src, thumb=None):
    """Set artwork on a ListItem with proper aspect ratio handling.
    
    Assigns different images to different art keys based on their aspect ratios:
    - fanart (16:9 landscape) - prefers landscape images
    - poster (2:3 portrait) - prefers portrait images  
    - thumb/icon (1:1 square) - uses best single image with aspect ratio preserved
    
    Args:
        li: xbmcgui.ListItem to set artwork on
        src: Content dict (to extract multiple image URLs)
        thumb: Fallback single image URL if src doesn't provide multiple images
    """
    return default_helpers.set_smart_artwork(li, src, thumb=thumb)


def _is_logged_in():
    """Return True when the addon has an active authenticated session.

    We consider the user logged in when a valid access token exists or a
    cookie-session was established by the form login. This is intentionally
    lightweight and avoids forcing network calls during menu rendering.
    """
    try:
        api = get_api_instance()
        try:
            token = api.get_access_token()
        except Exception:
            token = None
        if token:
            return True
        if getattr(api, 'token', None) == 'cookie-session':
            # Heuristic: presence of nlziet cookies indicates an active session
            try:
                for c in api.cookie_jar:
                    dom = getattr(c, 'domain', '') or ''
                    if 'nlziet' in dom.lower():
                        return True
            except Exception:
                return True
    except Exception:
        pass
    return False


def _check_and_handle_token_expiry():
    """Check if token is expired and needs refresh. Show notification if re-login is required."""
    try:
        api = get_api_instance()
        
        # Try to get a valid token (which handles refresh automatically)
        token = api.get_access_token()
        if token:
            # Token is valid or was successfully refreshed
            return True
        
        # Token is expired and refresh failed - user needs to re-login
        save_creds = ADDON.getSetting('save_credentials') in ('true', '1', 'yes', True)
        if not save_creds:
            # No saved credentials, notify user to login
            try:
                xbmcgui.Dialog().notification('NLZiet', get_string('login_again'), xbmcgui.NOTIFICATION_INFO)
            except Exception:
                pass
        return False
    except Exception:
        pass
    return False


def main_menu():
    # Check for expired tokens and attempt refresh
    _check_and_handle_token_expiry()
    
    try:
        addon_path = xbmc.translatePath(ADDON.getAddonInfo('path')) or ''
    except Exception:
        try:
            addon_path = ADDON.getAddonInfo('path') or ''
        except Exception:
            addon_path = ''

    # prefer png then svg then fallback to addon's icon.png
    def _pick_icon(name):
        return kodi_ui.pick_menu_icon(addon_path, name)

    # Explicit PNG-first picker (prefer exact menu_{name}.png when available)
    def _pick_png(name):
        return kodi_ui.pick_menu_png(addon_path, name)

    # Start background refresh of account info (silent) on addon launch
    try:
        threading.Thread(target=refresh_account_info, args=(False,), daemon=True).start()
    except Exception:
        xbmc.log('NLZiet: failed to start account refresh thread', xbmc.LOGDEBUG)

    # Determine authentication state and show protected items only when logged in
    logged_in = _is_logged_in()

    # If not logged in, notify the user to press Login on the main menu
    if not logged_in:
        try:
            msg = get_string('login_notification')
            xbmcgui.Dialog().notification('NLZiet', msg, xbmcgui.NOTIFICATION_INFO)
        except Exception:
            xbmc.log('NLZiet: failed to show login notification', xbmc.LOGDEBUG)

    # Show Login or Sign Out button based on auth status
    if logged_in:
        explicit_logout_icon = os.path.join(addon_path, 'resources', 'media', 'menu_logout.png')
        logout_icon = explicit_logout_icon if explicit_logout_icon and os.path.exists(explicit_logout_icon) else _pick_png('logout')
        add_directory_item(get_string('sign_out'), {'mode': 'logout_confirm'}, thumb=logout_icon)
    else:
        add_directory_item(get_string('login'), {'mode': 'login'}, thumb=_pick_png('login'))
    
    if logged_in:
        add_directory_item(get_string('manage_profiles'), {'mode': 'profiles'}, thumb=_pick_png('profiles'))
        add_directory_item(get_string('search'), {'mode': 'search'}, thumb=_pick_png('search'))
        add_directory_item(get_string('my_list'), {'mode': 'my_list'}, thumb=_pick_png('mylist'))
        add_directory_item(get_string('series'), {'mode': 'browse_series_categories'}, thumb=_pick_png('series'))
        add_directory_item(get_string('tv_shows'), {'mode': 'browse_tv_shows'}, thumb=_pick_png('tvshows'))
        add_directory_item(get_string('documentary'), {'mode': 'browse', 'type': 'documentary'}, thumb=_pick_png('documentary'))
        add_directory_item(get_string('movies'), {'mode': 'browse_movie_categories'}, thumb=_pick_png('movies'))
        # Some icon sets use 'tv' instead of 'channels' (we check menu_tv.png)
        add_directory_item(get_string('channels'), {'mode': 'browse', 'type': 'channels'}, thumb=_pick_png('tv'))
    
    # Set background image for the container
    try:
        background_path = os.path.join(addon_path, 'resources', 'media', 'background.jpg')
        if os.path.exists(background_path):
            xbmcplugin.setProperty(HANDLE, 'fanart', background_path)
    except Exception:
        xbmc.log('NLZiet: failed to set background image', xbmc.LOGDEBUG)
    
    xbmcplugin.endOfDirectory(HANDLE)


def browse_series_categories():
    """Display series category/genre list."""
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item
    ).series_categories()


def browse_series_genre(genre=None):
    """Display series in a selected genre."""
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item,
        ADDON,
        NLZietAPI,
        get_string,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_channels_menu_data
    ).series_genre(genre)


def browse_series():
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item,
        ADDON,
        NLZietAPI,
        get_string,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_channels_menu_data
    ).series()


def show_series_detail(series_id):
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item,
        ADDON,
        NLZietAPI,
        get_string
    ).series_detail(series_id)


def show_series_season(series_id, season_id):
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item,
        ADDON,
        NLZietAPI,
        get_string,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_channels_menu_data
    ).series_season(series_id, season_id)


def browse_tv_shows():
    """Show TV show categories/genres for browsing."""
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item
    ).tv_shows()


def browse_tv_genre(genre=None):
    """Show TV shows for a specific genre."""
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item,
        ADDON,
        NLZietAPI,
        get_string,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_channels_menu_data
    ).tv_genre(genre)


def browse_movie_categories():
    """Display movie category/genre list."""
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item
    ).movie_categories()


def browse_movie_genre(genre=None):
    """Display movies in a selected genre."""
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item,
        ADDON,
        NLZietAPI,
        get_string,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_channels_menu_data
    ).movie_genre(genre)


def browse_placement_row(items_url=None, placement_id=None, comp_index=None):
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item,
        ADDON,
        NLZietAPI,
        get_string,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_channels_menu_data
    ).placement_row(items_url, placement_id, comp_index)


def _extract_max_devices(summary):
    """Try to parse max devices from API summary payload."""
    return default_helpers.extract_max_devices(summary)


def _extract_subscription_name(summary):
    """Try to parse subscription name from API summary payload."""
    return default_helpers.extract_subscription_name(summary)


def _extract_subscription_type(summary):
    """Try to parse subscription type from API summary payload."""
    return default_helpers.extract_subscription_type(summary)


def _extract_subscription_expiry(summary):
    """Try to parse subscription expiry (nextDate) from API summary payload."""
    return default_helpers.extract_subscription_expiry(summary)


def _format_date_string(dtstr):
    """Normalize various date formats to YYYY-MM-DD string."""
    return default_helpers.format_date_string(dtstr)


def refresh_account_info(notify=True):
    return AuthController(
        {},
        get_string,
        ADDON,
        get_api_instance,
        NLZietAPI
    ).refresh_account_info(notify=notify)


def do_logout(keep_mylist=False):
    """Clear persistent addon data (cookies, tokens, profile) and refresh the UI.

    Args:
        keep_mylist: If True, keep the My List file; if False, delete it
    
    This removes cookie/token/profile files saved under the addon's
    profile directory, clears the stored profile settings, and replaces the
    current container with the main menu so the addon appears like a fresh
    install.
    """
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance when available
    try:
        api = get_api_instance()
    except Exception:
        api = NLZietAPI(username=username, password=password)
    
    # remove persistent files (cookies, profile, tokens)
    # optionally remove mylist based on keep_mylist parameter
    paths = [getattr(api, 'cookie_file', None), getattr(api, 'stream_cookie_file', None), getattr(api, 'profile_file', None), getattr(api, 'token_file', None)]
    if not keep_mylist:
        paths.append(getattr(api, 'mylist_file', None))
    
    for p in paths:
        try:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    try:
                        with open(p, 'w', encoding='utf-8') as f:
                            f.write('')
                    except Exception:
                        pass
        except Exception:
            pass

    # clear in-memory cookie jar and tokens
    try:
        api.cookie_jar.clear()
    except Exception:
        pass
    try:
        api.tokens = {}
        api.token = None
    except Exception:
        pass

    # Clear API instance cache
    clear_api_cache()
    
    # Clear relevant addon settings so the addon appears fresh
    try:
        for key in ('profile_id', 'profile_name', 'subscription_name', 'subscription_type', 'subscription_expires', 'max_devices', 'username', 'password', 'save_credentials', 'access_token', 'refresh_token', 'token_expires_at'):
            try:
                ADDON.setSetting(key, '')
            except Exception:
                pass
    except Exception:
        pass

    xbmcgui.Dialog().notification('NLZiet', get_string('logged_out'), xbmcgui.NOTIFICATION_INFO)

    # Refresh UI to main menu so the addon appears like a fresh install
    try:
        main_url = build_url({})
        xbmc.executebuiltin('Container.Update(%s,replace)' % main_url)
    except Exception:
        try:
            xbmc.executebuiltin('RunPlugin(%s)' % BASE_URL)
        except Exception:
            pass


def confirm_logout():
    """Show confirmation dialogs before performing logout.
    
    First asks to confirm logout, then asks whether to keep My List.
    """
    return AuthController(get_route_handlers(), get_string).confirm_logout()


def show_login_dialog(preset_email='', preset_password=''):
    """Show login dialog to get email and password from user.
    
    Args:
        preset_email: optional pre-filled email address
        preset_password: optional pre-filled password
    
    Returns:
        Tuple of (email, password) or (None, None) if cancelled
    """
    return AuthController({}, get_string).show_login_dialog(
        preset_email,
        preset_password
    )


def do_login():
    """Handle login via dialog or saved credentials with retry support."""
    save_creds = ADDON.getSetting('save_credentials') in ('true', '1', 'yes', True)
    
    # Check if we have saved credentials
    saved_username = ADDON.getSetting('username')
    saved_password = ADDON.getSetting('password')
    
    email = None
    password = None
    
    # If credentials are saved and save_credentials is enabled, use them
    if save_creds and saved_username and saved_password:
        email = saved_username
        password = saved_password
        use_saved = True
    else:
        # Show login dialog
        email, password = show_login_dialog()
        use_saved = False
        if not email or not password:
            return
    
    # Attempt login with provided credentials (with retry loop)
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        try:
            xbmc.log(f"NLZiet: attempting login (attempt {attempt}/{max_attempts}) for {email}", xbmc.LOGINFO)
            api = NLZietAPI(username=email, password=password)
            ok = api.login()
            
            if ok:
                xbmc.log(f"NLZiet: login successful for {email}", xbmc.LOGINFO)
                # attempt PKCE authorize + token exchange (uses the saved cookie session)
                tokens = api.perform_pkce_authorize_and_exchange()
                if tokens:
                    try:
                        api._append_debug(
                            "LOGIN FLOW: PKCE returned tokens access={} refresh={}".format(
                                bool((tokens or {}).get('access_token')),
                                bool((tokens or {}).get('refresh_token')),
                            )
                        )
                        api._debug_auth_state('default_do_login_tokens_received')
                    except Exception:
                        pass

                    try:
                        if isinstance(tokens, dict):
                            api.tokens.update(tokens)
                        if api.tokens.get('access_token'):
                            api.token = api.tokens.get('access_token')
                            api.save_tokens()
                    except Exception:
                        pass

                    # Store tokens in API (they're persistent via save_tokens)
                    xbmcgui.Dialog().notification('NLZiet', get_string('session_token_obtained'), xbmcgui.NOTIFICATION_INFO)
                    
                    # If user didn't use saved credentials, ask how to save the session
                    if not use_saved and not save_creds:
                        try:
                            options = [
                                get_string('save_option_tokens_only'),
                                get_string('save_option_with_credentials')
                            ]
                            choice = xbmcgui.Dialog().select(get_string('save_options_title'), options)
                            
                            if choice == 0:
                                # User chose tokens only (recommended)
                                xbmcgui.Dialog().ok('NLZiet', get_string('tokens_only_info'))
                            elif choice == 1:
                                # User chose to save email and password
                                xbmcgui.Dialog().ok('NLZiet', get_string('credentials_saved_warning'))
                                # Save credentials
                                ADDON.setSetting('username', email)
                                ADDON.setSetting('password', password)
                                ADDON.setSetting('save_credentials', 'true')
                        except Exception:
                            pass
                else:
                    try:
                        api._append_debug('LOGIN FLOW: form login succeeded but PKCE/token exchange returned no tokens')
                        api._debug_auth_state('default_do_login_no_tokens')
                    except Exception:
                        pass
                    xbmcgui.Dialog().notification('NLZiet', get_string('login_successful_no_tokens'), xbmcgui.NOTIFICATION_INFO)

                # Keep runtime state consistent: startup may have cached an unauthenticated
                # API instance. Replace it with this authenticated one immediately.
                try:
                    set_api_instance(api)
                    try:
                        api._append_debug('LOGIN FLOW: cached API instance replaced with authenticated instance')
                    except Exception:
                        pass
                except Exception:
                    pass

                try:
                    # Avoid showing a confusing parse-error popup directly after login
                    # when account summary fields are temporarily unavailable.
                    refresh_account_info(notify=False)
                except Exception:
                    pass

                # Refresh main menu so authenticated entries are shown right away.
                try:
                    main_url = build_url({})
                    xbmc.executebuiltin('Container.Update(%s,replace)' % main_url)
                except Exception:
                    pass
                return
            else:
                # Login failed - offer to retry
                xbmc.log(f"NLZiet: login failed for {email} (attempt {attempt}/{max_attempts})", xbmc.LOGINFO)
                
                # If we have more attempts, ask user if they want to retry
                if attempt < max_attempts:
                    retry_msg = f"{get_string('login_invalid_credentials')}\n\n{get_string('login_try_again')}"
                    
                    if xbmcgui.Dialog().yesno('NLZiet', retry_msg):
                        # Show login dialog again with email/password pre-filled
                        new_email, new_password = show_login_dialog(email, password)
                        if new_email and new_password:
                            email = new_email
                            password = new_password
                            # Loop will continue to next attempt
                        else:
                            # User cancelled
                            return
                    else:
                        # User doesn't want to retry
                        return
                else:
                    # Max attempts reached
                    xbmcgui.Dialog().notification('NLZiet', 'Login failed - max attempts reached', xbmcgui.NOTIFICATION_ERROR)
                    return
        
        except Exception as e:
            xbmc.log(f"NLZiet: login exception (attempt {attempt}/{max_attempts}): {e}", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification('NLZiet', f'Login error: {str(e)[:50]}', xbmcgui.NOTIFICATION_ERROR)
            return


def manage_profiles():
    return ProfileController(
        {},
        ADDON,
        get_api_instance,
        NLZietAPI,
        build_url,
        HANDLE,
        add_directory_item,
        _make_color_tag,
        get_string
    ).manage()


def browse_my_list():
    return MyListController(
        {},
        ADDON,
        HANDLE,
        get_api_instance,
        NLZietAPI,
        add_directory_item,
        _pick_landscape_thumb,
        get_string
    ).list()


def browse_my_list_group(group):
    """Show items from the user's My List filtered to a single group."""
    return MyListController(
        {},
        ADDON,
        HANDLE,
        get_api_instance,
        NLZietAPI,
        add_directory_item,
        _pick_landscape_thumb,
        get_string
    ).group(group)


def toggle_mylist(item_id=None, title=None, type=None, thumb=None):
    return MyListController(
        {},
        ADDON,
        HANDLE,
        get_api_instance,
        NLZietAPI,
        add_directory_item,
        _pick_landscape_thumb,
        get_string
    ).toggle(item_id, title, type, thumb)


def select_profile(profile_id):
    return ProfileController(
        {'manage_profiles': manage_profiles},
        ADDON,
        get_api_instance,
        NLZietAPI,
        build_url,
        HANDLE,
        add_directory_item,
        _make_color_tag,
        get_string
    ).select(profile_id)


def apply_profile():
    """Apply the `profile_id` stored in settings: perform profile-grant and
    update the stored `profile_name` setting for display in Settings UI.
    """
    pid = ADDON.getSetting('profile_id') or ''
    if not pid:
        xbmcgui.Dialog().notification('NLZiet', 'No Profile ID set in Settings', xbmcgui.NOTIFICATION_INFO)
        return

    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance for faster profile application
    try:
        api = get_api_instance()
    except Exception:
        api = NLZietAPI(username=username, password=password)

    try:
        # Attempt a direct profile switch using the stored master token or
        # cookie session.
        result = api.select_profile(pid)
        if not result:
            # Try to obtain tokens using PKCE and retry selection
            tokens = api.perform_pkce_authorize_and_exchange()
            if tokens:
                result = api.select_profile(pid)
    except Exception as e:
        xbmc.log(f"NLZiet apply_profile error: {e}", xbmc.LOGERROR)
        result = None

    if result:
        # Find a human-friendly name for the profile when possible
        profile_name = ''
        try:
            profiles = api.get_profiles() or []
            for p in profiles:
                if str(p.get('id')) == str(pid) or str(p.get('profileId')) == str(pid):
                    profile_name = p.get('displayName') or p.get('name') or p.get('profileName') or ''
                    break
        except Exception:
            profile_name = ''

        try:
            ADDON.setSetting('profile_name', profile_name or str(pid))
        except Exception:
            pass

        try:
            refresh_account_info()
        except Exception:
            pass

        xbmcgui.Dialog().notification('NLZiet', f'Profile applied: {profile_name or pid}', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('NLZiet', 'Failed to apply profile. Try Manage profiles.', xbmcgui.NOTIFICATION_ERROR)


def do_search():
    return SearchController(
        {},
        ADDON,
        HANDLE,
        get_api_instance,
        NLZietAPI,
        add_directory_item,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_string
    ).search()


def browse_category(content_type):
    return BrowseController(
        {},
        HANDLE,
        get_api_instance,
        add_directory_item,
        ADDON,
        NLZietAPI,
        get_string,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_channels_menu_data
    ).category(content_type)


def search_group(q, group):
    return SearchController(
        {},
        ADDON,
        HANDLE,
        get_api_instance,
        NLZietAPI,
        add_directory_item,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_string
    ).group(q, group)


def filter_manifest_subtitles(manifest_url):
    """
    Placeholder for future manifest filtering.
    Currently unused - we use player subtitle API instead.
    """
    return PlaybackController({}).filter_manifest_subtitles(manifest_url)


class NLZietPlaybackMonitor(xbmc.Player):
    """Player callback helper for live TV subtitle control.

    Keep this callback path non-blocking so stop/back returns to the menu instantly.
    """

    def __init__(self, disable_subs=False):
        super().__init__()
        self.disable_subs = disable_subs
        self.subtitle_disabled = False
        xbmc.log(f"NLZiet: PlaybackMonitor created with disable_subs={disable_subs}", xbmc.LOGINFO)

    def _disable_subtitles_if_needed(self):
        if not self.disable_subs or self.subtitle_disabled:
            return
        try:
            if not self.isPlaying():
                return
            xbmc.log("NLZiet: playback detected, disabling subtitles", xbmc.LOGINFO)
            try:
                self.showSubtitles(False)
                xbmc.log("NLZiet: called player.showSubtitles(False)", xbmc.LOGINFO)
                self.subtitle_disabled = True
            except AttributeError:
                try:
                    self.setSubtitleStream(-1)
                    xbmc.log("NLZiet: called player.setSubtitleStream(-1)", xbmc.LOGINFO)
                    self.subtitle_disabled = True
                except Exception as e:
                    xbmc.log(f"NLZiet: setSubtitleStream failed: {e}", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f"NLZiet PlaybackMonitor subtitle disable exception: {e}", xbmc.LOGWARNING)

    def onPlayBackStarted(self):
        self._disable_subtitles_if_needed()

    def onAVStarted(self):
        # Some Kodi versions trigger onAVStarted more reliably than onPlayBackStarted.
        self._disable_subtitles_if_needed()


def ensure_inputstream_for_drm():
    """Ensure DRM playback dependencies using script.module.inputstreamhelper.

    Returns:
        inputstreamhelper.Helper instance when ready, otherwise None.
    """
    try:
        import inputstreamhelper
    except Exception:
        xbmcgui.Dialog().ok(
            'Dependency missing',
            'Please install script.module.inputstreamhelper to play DRM streams.'
        )
        return None

    try:
        helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        if helper.check_inputstream():
            return helper
    except Exception as e:
        xbmc.log(f"NLZiet inputstreamhelper check failed: {e}", xbmc.LOGERROR)

    return None


# Global playback monitor for live TV subtitle control
_playback_monitor = None

def play_item(content_id, fmt=None, **kwargs):
    username = ADDON.getSetting('username')
    password = ADDON.getSetting('password')
    # Use cached API instance - still makes the stream info call but avoids object init overhead
    try:
        api = get_api_instance()
    except Exception:
        # Fallback to creating a new instance if cache fails
        api = NLZietAPI(username=username, password=password)
    xbmc.log(f"NLZiet play_item called: id={content_id} fmt={fmt}", xbmc.LOGINFO)
    if fmt == 'live':
        info = api.get_stream_info(content_id, context='Live')
        xbmc.log(f"NLZiet LIVE TV: id={content_id} context='Live'", xbmc.LOGINFO)
    elif fmt == 'epg':
        info = api.get_stream_info(content_id, context='Epg', **kwargs)
    else:
        info = api.get_stream_info(content_id)
        xbmc.log(f"NLZiet REGULAR content: id={content_id} (not live)", xbmc.LOGINFO)
    manifest = info.get('manifest')
    is_drm = info.get('is_drm')
    subs_in_info = info.get('subtitles')
    xbmc.log(f"NLZiet play_item: id={content_id} manifest={manifest} is_drm={is_drm} fmt={fmt} has_subs={bool(subs_in_info)}", xbmc.LOGINFO)
    xbmc.log(f"NLZiet info subtitles value: {repr(subs_in_info)} (type: {type(subs_in_info).__name__})", xbmc.LOGINFO)
    if not manifest:
        xbmcgui.Dialog().notification('NLZiet', 'No manifest available', xbmcgui.NOTIFICATION_ERROR)
        return

    # Check subtitle setting once for all processing
    try:
        enable_subs = ADDON.getSetting('subtitles_default')
        xbmc.log(f"NLZiet DEBUG subtitles_default raw value: {repr(enable_subs)} (type: {type(enable_subs).__name__})", xbmc.LOGINFO)
    except Exception as e:
        enable_subs = None
        xbmc.log(f"NLZiet ERROR reading subtitles_default: {e}", xbmc.LOGINFO)
    
    # Convert to boolean - handle all possible Kodi return values
    # Note: Kodi may return '0'/'1' or 'false'/'true' or boolean values
    if enable_subs is None or enable_subs == '' or enable_subs == 'false' or enable_subs == '0' or enable_subs is False:
        subs_enabled = False
    elif enable_subs == 'true' or enable_subs == '1' or enable_subs is True:
        subs_enabled = True
    else:
        # Fallback: try string parsing
        subs_enabled = str(enable_subs).lower().strip() in ('true', '1', 'yes', 'on')
    
    xbmc.log(f"NLZiet subtitles setting: raw={repr(enable_subs)} -> enabled={subs_enabled}", xbmc.LOGINFO)
    is_live = (fmt == 'live')
    xbmc.log(f"NLZiet play_item: fmt={fmt} is_live={is_live} subs_enabled={subs_enabled}", xbmc.LOGINFO)
    
    # For live TV with subtitles disabled: use a playback monitor to disable subs when play starts
    # This prevents inputstream.adaptive from auto-loading subtitle tracks from the manifest
    global _playback_monitor
    if is_live and not subs_enabled:
        xbmc.log(f"NLZiet LIVE TV: subtitle monitor enabled to disable subs on playback start", xbmc.LOGINFO)
        _playback_monitor = NLZietPlaybackMonitor(disable_subs=True)
    else:
        _playback_monitor = None

    if info.get('is_drm'):
        is_helper = ensure_inputstream_for_drm()
        if not is_helper:
            return
        li = xbmcgui.ListItem(path=manifest, offscreen=True)
        # Use the inputstream addon resolved by InputStream Helper.
        try:
            inputstream_addon = is_helper.inputstream_addon
        except Exception:
            inputstream_addon = 'inputstream.adaptive'

        # prefer new property if available
        li.setProperty('inputstream', inputstream_addon)
        li.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        li.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        license_url = info.get('license_url') or ''
        headers = info.get('license_headers') or {}
        xbmc.log("NLZiet DRM: license_url=%s headers=%s" % (license_url, headers), xbmc.LOGINFO)
        drm_security = info.get('drm_security')
        xbmc.log(f"NLZiet DRM security level: {drm_security}", xbmc.LOGINFO)
        try:
            raw = info.get('drm_raw')
            xbmc.log("NLZiet DRM raw (partial): %s" % (str(raw)[:1000]), xbmc.LOGINFO)
        except Exception:
            pass
        if drm_security:
            xbmcgui.Dialog().notification('NLZiet', f'Required DRM: {drm_security}', xbmcgui.NOTIFICATION_INFO)

        # make a safe copy of headers and ensure User-Agent matches the API session
        try:
            headers = dict(headers or {})
        except Exception:
            headers = {}

        try:
            if api and getattr(api, 'user_agent', None):
                headers.setdefault('User-Agent', api.user_agent)
        except Exception:
            pass

        import urllib.parse as _up, json as _json, platform as _platform

        # Extract Nlziet-License directly from the handshake response if available,
        # prefer the raw DRM dict when present.
        try:
            nlziet_license = ''
            drm_obj = info.get('drm_raw') or {}
            if isinstance(drm_obj, dict):
                hdrs = drm_obj.get('headers') or {}
                if isinstance(hdrs, dict):
                    nlziet_license = hdrs.get('Nlziet-License') or hdrs.get('nlziet-license') or ''
            if not nlziet_license:
                nlziet_license = (headers.get('Nlziet-License') or headers.get('nlziet-license') or '')
        except Exception:
            nlziet_license = ''

        # Build the canonical license_key and a matching CRLF `stream_headers` block.
        license_url = info.get('license_url') or ''
        try:
            stream_info = {'drm': info.get('drm_raw') or {}, 'manifestUrl': info.get('manifest')}
            try:
                nlziet_license = stream_info['drm']['headers']['Nlziet-License']
            except Exception:
                nlziet_license = (stream_info.get('drm') or {}).get('headers', {}).get('Nlziet-License') or headers.get('Nlziet-License') or ''

            # derive device/app metadata
            _app_name = 'NLZIET'
            _app_version = '5.13.6'
            _brand = _platform.system() or 'Linux'
            _model = _platform.node() or 'Kodi'
            _platform_version = _platform.release() or ''
            _capabilities = 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile'

            # If this is a live playback request, avoid adding Authorization
            is_live = (fmt == 'live')
            token = api.get_access_token() or ''
            if is_live:
                token = ''

            # header values (unencoded)
            hdr_vals = {
                'Authorization': 'Bearer ' + token if token else '',
                'Nlziet-License': str(nlziet_license),
                'Nlziet-AppName': _app_name,
                'Nlziet-AppVersion': _app_version,
                'Nlziet-BrandName': _brand,
                'Nlziet-ModelName': _model,
                'Nlziet-PlatformVersion': _platform_version,
                'Nlziet-DeviceCapabilities': _capabilities,
                'Content-Type': 'application/octet-stream',
            }

            # canonical header ordering (Authorization first when present)
            header_order = ['Authorization', 'Nlziet-License', 'Nlziet-AppName', 'Nlziet-AppVersion', 'Nlziet-BrandName', 'Nlziet-ModelName', 'Nlziet-PlatformVersion', 'Nlziet-DeviceCapabilities', 'Content-Type']

            pairs = []
            final_headers = {}
            for k in header_order:
                v = hdr_vals.get(k) or headers.get(k) or headers.get(k.lower()) or ''
                if v is None or v == '':
                    continue
                final_headers[k] = str(v)
                pairs.append(f"{k}={_up.quote(str(v), safe='')}")

            # include any remaining handshake headers not present in canonical ordering
            for hk, hv in (headers or {}).items():
                if hk not in final_headers and hv:
                    final_headers[hk] = str(hv)
                    pairs.append(f"{hk}={_up.quote(str(hv), safe='')}")

            header_block = '&'.join(pairs)
            license_url = license_url or 'https://api.nlziet.nl/v9/license/proxy/Widevine'
            license_key = f"{license_url}|{header_block}|R{{SSM}}|"

            # Build CRLF stream headers from final_headers to keep them consistent
            if final_headers:
                header_str = '\r\n'.join(f"{k}: {v}" for k, v in final_headers.items())
                li.setProperty('inputstream.adaptive.stream_headers', header_str)
        except Exception:
            license_key = f"{license_url}|||"

        xbmc.log(f"NLZiet using license_key: {license_key}", xbmc.LOGINFO)

        # Apply the license_key and ensure manifest type is `mpd` for DASH
        li.setProperty('inputstream.adaptive.license_key', license_key)
        li.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        li.setProperty('inputstream.adaptive.manifest_update_decode', 'true')

        # Attach external subtitles (OutOfBand VTT) returned by the handshake
        try:
            subs = info.get('subtitles') or []
            xbmc.log(f"NLZiet DRM subtitles array: {subs} (type: {type(subs).__name__}, len={len(subs) if subs else 0})", xbmc.LOGINFO)
            
            sub_urls = []
            for s in subs:
                if isinstance(s, dict):
                    url = s.get('url') or s.get('uri') or s.get('file')
                else:
                    url = s
                if url:
                    sub_urls.append(url)
            xbmc.log(f"NLZiet DRM extracted sub_urls: {sub_urls}", xbmc.LOGINFO)
            
            if sub_urls and subs_enabled:
                xbmc.log(f"NLZiet attaching subtitles: {sub_urls}", xbmc.LOGINFO)
                try:
                    li.setSubtitles(sub_urls)
                except Exception as e:
                    xbmc.log(f"NLZiet subtitle attach failed: {e}", xbmc.LOGINFO)
                    # fallback: store as property for debugging or later handling
                    try:
                        li.setProperty('nlziet.subtitles', ';'.join(sub_urls))
                    except Exception:
                        pass
            elif sub_urls and not subs_enabled:
                xbmc.log(f'NLZiet: external subtitles found but disabled in settings', xbmc.LOGINFO)
            else:
                xbmc.log(f'NLZiet: no external subtitles in stream response', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"NLZiet exception in subtitle handling: {e}", xbmc.LOGINFO)
            pass

        # do not override inputstream's PSSH handling by supplying malformed
        # `inputstream.adaptive.license_data`. The canonical `license_key` and
        # `stream_headers` are sufficient; leaving `license_data` unset avoids
        # the plugin trying to parse incorrect PSSH data from this property.

        li.setMimeType('application/dash+xml')
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        # non-DRM: simply play the manifest URL
        xbmc.log(f"NLZiet non-DRM manifest: {manifest}", xbmc.LOGDEBUG)
        li = xbmcgui.ListItem(path=manifest)
        
        # Check subtitle setting once
        try:
            enable_subs = ADDON.getSetting('subtitles_default')
            xbmc.log(f"NLZiet DEBUG non-DRM subtitles_default raw: {repr(enable_subs)} (type: {type(enable_subs).__name__})", xbmc.LOGINFO)
        except Exception as e:
            enable_subs = None
            xbmc.log(f"NLZiet ERROR reading subtitles_default: {e}", xbmc.LOGINFO)
        
        # Convert to boolean - handle all possible return values from Kodi
        if enable_subs is None or enable_subs == '' or enable_subs == 'false' or enable_subs is False:
            subs_enabled = False
        elif enable_subs == 'true' or enable_subs is True or enable_subs == '1':
            subs_enabled = True
        else:
            # Fallback: try string parsing
            subs_enabled = str(enable_subs).lower().strip() in ('true', '1', 'yes', 'on')
        
        xbmc.log(f"NLZiet non-DRM subtitles setting: raw={repr(enable_subs)} -> enabled={subs_enabled}", xbmc.LOGINFO)
        
        # Also handle subtitles for non-DRM streams
        try:
            subs = info.get('subtitles') or []
            xbmc.log(f"NLZiet non-DRM subtitles array: {subs} (type: {type(subs).__name__}, len={len(subs) if subs else 0})", xbmc.LOGINFO)
            
            sub_urls = []
            for s in subs:
                if isinstance(s, dict):
                    url = s.get('url') or s.get('uri') or s.get('file')
                else:
                    url = s
                if url:
                    sub_urls.append(url)
            xbmc.log(f"NLZiet non-DRM extracted sub_urls: {sub_urls}", xbmc.LOGINFO)
            
            if sub_urls and subs_enabled:
                xbmc.log(f"NLZiet non-DRM attaching subtitles: {sub_urls}", xbmc.LOGINFO)
                try:
                    li.setSubtitles(sub_urls)
                except Exception as e:
                    xbmc.log(f"NLZiet non-DRM subtitle attach failed: {e}", xbmc.LOGINFO)
            elif sub_urls:
                xbmc.log(f'NLZiet non-DRM: external subtitles found but disabled in settings', xbmc.LOGINFO)
            else:
                xbmc.log(f'NLZiet non-DRM: no subtitles in stream response', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"NLZiet exception in non-DRM subtitle handling: {e}", xbmc.LOGINFO)
        
        xbmcplugin.setResolvedUrl(HANDLE, True, li)


def select_iptv_channels():
    return IPTVController(get_api_instance).select_channels()


def get_compatibility_handlers():
    return default_routes.build_compatibility_handlers(
        main_menu,
        do_login,
        do_search,
        manage_profiles,
        browse_my_list,
        browse_my_list_group,
        toggle_mylist,
        select_profile,
        apply_profile,
        browse_series,
        do_logout,
        confirm_logout,
        refresh_account_info,
        search_group,
        show_series_detail,
        show_series_season,
        browse_placement_row,
        browse_tv_shows,
        browse_tv_genre,
        browse_series_categories,
        browse_series_genre,
        browse_movie_categories,
        browse_movie_genre,
        browse_category,
        play_item,
        select_iptv_channels,
    )


def get_route_dependencies():
    return build_route_dependencies(
        ADDON,
        HANDLE,
        get_api_instance,
        NLZietAPI,
        build_url,
        add_directory_item,
        _pick_landscape_thumb,
        _make_color_tag,
        EXPIRY_COLOR_RAW,
        get_channels_menu_data,
        get_string,
    )


def get_route_handlers():
    return build_route_handlers(
        get_compatibility_handlers(),
        get_route_dependencies()
    )


def router(paramstring):
    context = AddonContext(ADDON, HANDLE, BASE_URL, paramstring)
    Router(context, get_route_handlers()).dispatch(paramstring)


if __name__ == '__main__':
    context = AddonContext.from_kodi()
    Router(context, get_route_handlers()).dispatch()
