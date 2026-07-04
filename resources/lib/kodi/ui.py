import urllib.parse


def build_url(base_url, query):
    return base_url + '?' + urllib.parse.urlencode(query)


def optimize_image_url(url):
    """Optimize image URLs to request higher-resolution versions for fanart.

    The NLZiet image service returns low-res images (1280x720) by default.
    Request a larger resolution to avoid pixelation when displayed as fanart.
    """
    if not url or not isinstance(url, str):
        return url

    # Remove any existing width/crop parameters
    if '?' in url:
        url = url.split('?')[0]

    # Request a much larger width for fanart (3840px = 4K width)
    return url + '?width=3840'
