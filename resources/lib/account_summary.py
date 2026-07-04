import re
from datetime import datetime


def extract_max_devices(summary):
    """Try to parse max devices from API summary payload."""
    def _find(data):
        if isinstance(data, dict):
            title = str(data.get('title') or data.get('name') or '')
            if title and 'apparaten' in title.lower():
                # direct title may contain number
                m = re.search(r"(\d+)", title)
                if m:
                    return m.group(1)
            terms = data.get('terms') or data.get('term') or []
            if isinstance(terms, list):
                for t in terms:
                    if isinstance(t, dict):
                        label = str(t.get('label') or '')
                        if 'apparaten' in label.lower():
                            m = re.search(r"(\d+)", label)
                            if m:
                                return m.group(1)
                        res = _find(t)
                        if res:
                            return res
            for v in data.values():
                res = _find(v)
                if res:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = _find(item)
                if res:
                    return res
        return None

    result = _find(summary)
    return str(result) if result else ''


def extract_subscription_name(summary):
    """Try to parse subscription name from API summary payload."""
    if not isinstance(summary, dict):
        return ''
    # first, look for direct subscription field
    sub = summary.get('subscription') or summary.get('plan') or summary.get('product') or {}
    if isinstance(sub, dict):
        name = sub.get('name') or sub.get('title') or ''
        if name:
            return str(name)
    # fallback: find any name field in root with known hints
    for k in ('name', 'subscriptionName', 'planName'):
        if summary.get(k):
            return str(summary.get(k))
    # recursively find object with 'name' and context
    def _find(data):
        if isinstance(data, dict):
            for k, v in data.items():
                if k.lower() == 'name' and isinstance(v, str) and v.strip():
                    return v
                res = _find(v)
                if res:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = _find(item)
                if res:
                    return res
        return None
    found = _find(summary)
    return str(found) if found else ''


def extract_subscription_type(summary):
    """Try to parse subscription type from API summary payload."""
    if not summary:
        return ''

    if isinstance(summary, dict):
        sub = summary.get('subscription') or summary.get('plan') or summary.get('product') or {}
        if isinstance(sub, dict):
            for key in ('subscriptionType', 'planType', 'productType', 'tier', 'type'):
                value = sub.get(key)
                if value is not None and str(value).strip():
                    return str(value)

        for key in ('subscription_type', 'subscriptionType', 'planType', 'productType'):
            value = summary.get(key)
            if value is not None and str(value).strip():
                return str(value)

    def _find(data, in_subscription_context=False):
        if isinstance(data, dict):
            keys = {str(k).lower() for k in data.keys()}
            ctx = in_subscription_context or bool(keys & {'subscription', 'plan', 'product', 'subscriptiontype', 'plantype', 'producttype'})

            for key in ('subscriptionType', 'planType', 'productType', 'tier', 'type'):
                if key in data:
                    value = data.get(key)
                    if value is not None and str(value).strip():
                        if key != 'type' or ctx:
                            return str(value)

            for k, v in data.items():
                next_ctx = ctx or str(k).lower() in {'subscription', 'plan', 'product'}
                result = _find(v, next_ctx)
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = _find(item, in_subscription_context)
                if result:
                    return result

        return None

    found = _find(summary)
    return str(found) if found else ''


def extract_subscription_expiry(summary):
    """Try to parse subscription expiry (nextDate) from API summary payload."""
    if not summary:
        return ''
    # direct field on root
    if isinstance(summary, dict):
        if 'nextDate' in summary and summary.get('nextDate'):
            return format_date_string(summary.get('nextDate'))
        sub = summary.get('subscription') or summary.get('plan') or summary.get('product') or {}
        if isinstance(sub, dict) and sub.get('nextDate'):
            return format_date_string(sub.get('nextDate'))
    # recurse into lists/dicts
    if isinstance(summary, (list, tuple)):
        for item in summary:
            d = extract_subscription_expiry(item)
            if d:
                return d
    if isinstance(summary, dict):
        for v in summary.values():
            d = extract_subscription_expiry(v)
            if d:
                return d
    return ''


def format_date_string(dtstr):
    """Normalize various date formats to YYYY-MM-DD string."""
    if not dtstr:
        return ''
    s = str(dtstr)
    formats = ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    # try numeric timestamp (seconds or milliseconds)
    try:
        t = float(s)
        if t > 1e12:
            t = t / 1000.0
        dt = datetime.fromtimestamp(t)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return s
