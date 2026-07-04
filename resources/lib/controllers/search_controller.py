import xbmcgui
import xbmcplugin


class SearchController:
    """Search route adapter."""

    def __init__(self, handlers, addon=None, handle=None,
                 get_api_instance=None, api_class=None,
                 add_directory_item=None, pick_landscape_thumb=None,
                 make_color_tag=None, expiry_color_raw=None):
        self._handlers = handlers
        self._addon = addon
        self._handle = handle
        self._get_api_instance = get_api_instance
        self._api_class = api_class
        self._add_directory_item = add_directory_item
        self._pick_landscape_thumb = pick_landscape_thumb
        self._make_color_tag = make_color_tag
        self._expiry_color_raw = expiry_color_raw

    def search(self):
        return self._handlers['do_search']()

    def group(self, query, group):
        if (self._addon and self._get_api_instance and self._api_class
                and self._add_directory_item and self._pick_landscape_thumb
                and self._make_color_tag and self._expiry_color_raw):
            q = query
            if not q:
                xbmcgui.Dialog().notification('NLZiet', 'Missing search query', xbmcgui.NOTIFICATION_INFO)
                return

            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for search results
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            results = api.search(q)
            if not results:
                fb = []
                ql = (q or '').lower()
                try:
                    sers = api.get_series_list(limit=999) or []
                    for s in sers:
                        try:
                            t = (s.get('title') or '')
                            if ql and ql in t.lower():
                                fb.append(s)
                        except Exception:
                            continue
                except Exception:
                    pass
                try:
                    movs = api.get_movies() or []
                    for m in movs:
                        try:
                            t = (m.get('title') or '')
                            if ql and ql in t.lower():
                                fb.append(m)
                        except Exception:
                            continue
                except Exception:
                    pass
                try:
                    chs = api.get_channels() or []
                    for c in chs:
                        try:
                            t = (c.get('title') or '')
                            if ql and ql in t.lower():
                                fb.append(c)
                        except Exception:
                            continue
                except Exception:
                    pass
                if fb:
                    results = fb
                else:
                    xbmcgui.Dialog().notification('NLZiet', f'No results for "{q}"', xbmcgui.NOTIFICATION_INFO)
                    xbmcplugin.endOfDirectory(self._handle)
                    return

            # Present only items that match the requested group
            for item in results:
                info = None
                try:
                    desc = item.get('description') or item.get('subtitle') or ''
                    if desc:
                        title_for_info = item.get('title') or ''
                        expiry_text = item.get('expires_in') or None
                        truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                        plot_full = desc
                        po = truncated
                        if expiry_text:
                            marker = 'ðŸ”¶ '
                            colored = self._make_color_tag(self._expiry_color_raw, expiry_text)
                            plot_full = f"{colored}\n{desc}" if desc else colored
                            po = f"{marker}{expiry_text} â€” {truncated}" if truncated else f"{marker}{expiry_text}"
                        info = {'title': title_for_info, 'plot': plot_full, 'plotoutline': po}
                    else:
                        cid = item.get('id')
                        if cid:
                            detail = api.get_content_detail(cid)
                            if detail:
                                desc = detail.get('description') or detail.get('plot') or ''
                                expiry_text = detail.get('expires_in') or None
                                title_for_info = detail.get('title') or item.get('title') or ''
                                if desc:
                                    truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                                    plot_full = desc
                                    po = truncated
                                    if expiry_text:
                                        marker = 'ðŸ”¶ '
                                        colored = self._make_color_tag(self._expiry_color_raw, expiry_text)
                                        plot_full = f"{colored}\n{desc}" if desc else colored
                                        po = f"{marker}{expiry_text} â€” {truncated}" if truncated else f"{marker}{expiry_text}"
                                    info = {'title': title_for_info, 'plot': plot_full, 'plotoutline': po}
                except Exception:
                    info = None

                content_id = item.get('id') or item.get('contentId') or item.get('content_id')
                itype = item.get('type') or ''
                itype_l = (str(itype).lower() if itype else '')

                if not itype_l and content_id:
                    try:
                        det = api.get_content_detail(content_id) or {}
                        raw = det.get('raw') or {}
                        itype_l = (str(raw.get('type') or '')).lower()
                    except Exception:
                        itype_l = itype_l

                # compute group and skip items that don't match
                group_name = None
                if 'series' in itype_l or 'tvshow' in itype_l:
                    group_name = 'Series'
                elif 'episode' in itype_l:
                    group_name = 'Episodes'
                elif 'movie' in itype_l or 'film' in itype_l:
                    group_name = 'Movies'
                elif 'channel' in itype_l or 'live' in itype_l:
                    group_name = 'Channels'
                else:
                    sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
                    if sid:
                        group_name = 'Series'
                    else:
                        group_name = 'Other'

                if not group_name or str(group_name).lower() != (str(group or '').lower()):
                    continue

                title = item.get('title') or item.get('name') or content_id or 'Result'
                thumb = self._pick_landscape_thumb(item)

                # Inside a search-group listing we show plain titles; the group
                # context is already provided by the parent folder label.
                display_title = title

                if 'series' in itype_l or 'tvshow' in itype_l:
                    self._add_directory_item(display_title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info, content=item)
                elif 'episode' in itype_l:
                    self._add_directory_item(display_title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info, content=item)
                elif 'movie' in itype_l or 'film' in itype_l:
                    self._add_directory_item(display_title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info, content=item)
                elif 'channel' in itype_l or 'live' in itype_l:
                    self._add_directory_item(display_title, {'mode': 'play', 'id': item.get('id'), 'fmt': 'live'}, is_folder=False, thumb=thumb, info=info, content=item)
                else:
                    sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
                    if sid:
                        self._add_directory_item(display_title, {'mode': 'series_detail', 'series_id': sid}, is_folder=True, thumb=thumb, info=info, content=item)
                    else:
                        self._add_directory_item(display_title, {'mode': 'play', 'id': item.get('id') or content_id}, is_folder=False, thumb=thumb, info=info, content=item)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['search_group'](query, group)
