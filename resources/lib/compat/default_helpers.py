from resources.lib import account_summary
from resources.lib.kodi import ui as kodi_ui


# Raw expiry color to test. Kept as a compatibility constant for default.py.
EXPIRY_COLOR_RAW = 'ffoooo66'


def make_color_tag(color_raw, text):
    """Return a Kodi COLOR tag using the raw value provided by the caller."""
    return kodi_ui.make_color_tag(color_raw, text)


def build_url(base_url, query):
    return kodi_ui.build_url(base_url, query)


def optimize_image_url(url):
    return kodi_ui.optimize_image_url(url)


def pick_landscape_thumb(src):
    return kodi_ui.pick_landscape_thumb(src)


def pick_portrait_thumb(src):
    return kodi_ui.pick_portrait_thumb(src)


def set_smart_artwork(li, src, thumb=None):
    return kodi_ui.set_smart_artwork(li, src, thumb=thumb)


def extract_max_devices(summary):
    return account_summary.extract_max_devices(summary)


def extract_subscription_name(summary):
    return account_summary.extract_subscription_name(summary)


def extract_subscription_type(summary):
    return account_summary.extract_subscription_type(summary)


def extract_subscription_expiry(summary):
    return account_summary.extract_subscription_expiry(summary)


def format_date_string(dtstr):
    return account_summary.format_date_string(dtstr)
