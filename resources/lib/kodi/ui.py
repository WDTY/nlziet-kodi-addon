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


def pick_landscape_thumb(src):
    """Return the best landscape-oriented thumbnail or path for an item."""
    if not src:
        return None
    if isinstance(src, str):
        return optimize_image_url(src)
    try:
        # Prefer explicit landscape / wide keys first
        for k in ('landscapeUrl', 'landscape', 'thumbnailLandscape', 'thumbnail_landscape', 'posterLandscape', 'poster_landscape', 'heroImage', 'heroImageUrl', 'widePosterUrl'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return optimize_image_url(v)

        # Common poster/thumbnail fields (posterUrl may be portrait but is a useful fallback)
        for k in ('posterUrl', 'poster', 'thumbnail', 'thumb'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return optimize_image_url(v)

        # Check nested image dicts for landscape keys
        for img_key in ('image', 'images'):
            img = src.get(img_key)
            if isinstance(img, dict):
                for k in ('landscapeUrl', 'landscape', 'landscape_url', 'wide', 'wideUrl', 'large', 'largeUrl', 'posterUrl', 'thumbnail', 'thumb'):
                    v = img.get(k)
                    if isinstance(v, str) and v:
                        return optimize_image_url(v)
                for kk, vv in img.items():
                    if isinstance(kk, str) and 'landscape' in kk.lower() and isinstance(vv, str) and vv:
                        return vv

        # Any key name containing 'landscape' on the top-level
        for kk, vv in src.items():
            if isinstance(kk, str) and 'landscape' in kk.lower() and isinstance(vv, str) and vv:
                return optimize_image_url(vv)

        # As a final fallback, return any url-like string value
        for vv in src.values():
            if isinstance(vv, str) and (vv.startswith('http://') or vv.startswith('https://') or vv.startswith('file://')):
                return optimize_image_url(vv)
    except Exception:
        pass
    return None


def pick_portrait_thumb(src):
    """Return the best portrait-oriented thumbnail or path for an item."""
    if not src:
        return None
    if isinstance(src, str):
        return optimize_image_url(src)
    try:
        # Prefer explicit portrait / tall keys first
        for k in ('portraitUrl', 'portrait', 'posterUrl', 'poster', 'thumbnailPortrait', 'thumbnail_portrait', 'coverUrl', 'cover'):
            v = src.get(k)
            if isinstance(v, str) and v:
                return optimize_image_url(v)
        # Check nested image dicts for portrait keys
        for img_key in ('image', 'images'):
            img = src.get(img_key)
            if isinstance(img, dict):
                for k in ('portraitUrl', 'portrait', 'portrait_url', 'posterUrl', 'poster', 'coverUrl', 'cover', 'thumbnail', 'thumb'):
                    v = img.get(k)
                    if isinstance(v, str) and v:
                        return optimize_image_url(v)
        # Fallback to any image URL
        for vv in src.values():
            if isinstance(vv, str) and (vv.startswith('http://') or vv.startswith('https://') or vv.startswith('file://')):
                return optimize_image_url(vv)
    except Exception:
        pass
    return None


def set_smart_artwork(li, src, thumb=None):
    """Set artwork on a ListItem with proper aspect ratio handling."""
    if not thumb and not src:
        return

    # Extract different image types from content object
    landscape_img = None
    portrait_img = None

    if src and isinstance(src, dict):
        landscape_img = pick_landscape_thumb(src)
        portrait_img = pick_portrait_thumb(src)

    # Fallback: use provided thumb for both if we don't have separate images
    if not landscape_img and not portrait_img:
        landscape_img = thumb
        portrait_img = thumb
    elif not landscape_img:
        landscape_img = portrait_img
    elif not portrait_img:
        portrait_img = landscape_img

    # Build artwork dict with proper aspect ratio handling
    art = {}

    # Landscape images work best for fanart (16:9 aspect ratio)
    if landscape_img:
        art['fanart'] = landscape_img
        art['landscape'] = landscape_img

    # Portrait images for poster art (2:3 aspect ratio)
    if portrait_img:
        art['poster'] = portrait_img

    # Use landscape for thumb/icon with aspect ratio preservation
    # Kodi will letterbox/pillarbox to fit rather than stretch
    if landscape_img:
        art['thumb'] = landscape_img
        art['icon'] = landscape_img
    elif portrait_img:
        art['thumb'] = portrait_img
        art['icon'] = portrait_img

    # Apply artwork with fallback for older Kodi versions
    if art:
        try:
            li.setArt(art)
        except Exception:
            # Fallback: try simple thumb/icon only
            try:
                if landscape_img:
                    li.setArt({'thumb': landscape_img, 'icon': landscape_img})
            except Exception:
                pass
