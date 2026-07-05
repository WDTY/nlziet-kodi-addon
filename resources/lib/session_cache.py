import time

import xbmc


# Global API instance cache to avoid repeated initialization.
_api_cache = None
_api_cache_time = 0
_api_cache_timeout = 300  # 5 minutes - refresh cache after this

# Short-lived channels listing cache to make return-from-playback instant.
_channel_menu_cache_data = []
_channel_menu_cache_epg = {}
_channel_menu_cache_time = 0
_channel_menu_cache_ttl = 45  # seconds


def get_api_instance(addon, api_class):
    """Get or create a cached API instance to avoid repeated disk I/O and initialization."""
    global _api_cache, _api_cache_time
    current_time = time.time()

    # If cache exists and is fresh (within timeout), return it.
    if _api_cache is not None and (current_time - _api_cache_time) < _api_cache_timeout:
        return _api_cache

    # Create new instance (loads cookies, tokens from disk).
    username = addon.getSetting('username') or ''
    password = addon.getSetting('password') or ''
    _api_cache = api_class(username=username, password=password)
    _api_cache_time = current_time
    return _api_cache


def clear_api_cache():
    """Clear the API instance and channel listing caches."""
    global _api_cache, _api_cache_time
    global _channel_menu_cache_data, _channel_menu_cache_epg, _channel_menu_cache_time
    _api_cache = None
    _api_cache_time = 0
    _channel_menu_cache_data = []
    _channel_menu_cache_epg = {}
    _channel_menu_cache_time = 0


def set_api_instance(api_instance):
    """Replace the API cache with a known-good instance (e.g. after login)."""
    global _api_cache, _api_cache_time
    _api_cache = api_instance
    _api_cache_time = time.time()


def get_channels_menu_data(api_instance):
    """Return channels + EPG data with short-lived in-memory caching."""
    global _channel_menu_cache_data, _channel_menu_cache_epg, _channel_menu_cache_time
    now = time.time()
    if _channel_menu_cache_time and (now - _channel_menu_cache_time) < _channel_menu_cache_ttl:
        return _channel_menu_cache_data or [], _channel_menu_cache_epg or {}

    results = api_instance.get_channels() or []
    epg_map = {}
    channel_ids = [r.get('id') for r in results if r.get('id')]
    if channel_ids:
        try:
            # Fetch EPG for all specified channels.
            epg_map = api_instance.get_current_programs(channel_ids) or {}
        except Exception as e:
            xbmc.log(f"get_channels_menu_data: EPG fetch failed: {e}", xbmc.LOGWARNING)
            epg_map = {}

    _channel_menu_cache_data = results
    _channel_menu_cache_epg = epg_map
    _channel_menu_cache_time = now
    return results, epg_map
