import xbmc
import xbmcgui
import xbmcplugin


class SearchController:
    """Search route adapter."""

    def __init__(self, handlers, addon=None, handle=None,
                 get_api_instance=None, api_class=None,
                 add_directory_item=None, pick_landscape_thumb=None,
                 make_color_tag=None, expiry_color_raw=None,
                 get_string=None):
        self._handlers = handlers
        self._addon = addon
        self._handle = handle
        self._get_api_instance = get_api_instance
        self._api_class = api_class
        self._add_directory_item = add_directory_item
        self._pick_landscape_thumb = pick_landscape_thumb
        self._make_color_tag = make_color_tag
        self._expiry_color_raw = expiry_color_raw
        self._get_string = get_string or (lambda key, *args: key.format(*args) if args else key)

    def _group_label(self, group):
        labels = {
            'Series': self._get_string('series'),
            'Episodes': self._get_string('episodes'),
            'Movies': self._get_string('movies'),
            'Channels': self._get_string('channels'),
            'Other': self._get_string('other'),
        }
        return labels.get(group, group)

    def search(self):
        if (self._addon and self._get_api_instance and self._api_class
                and self._add_directory_item and self._pick_landscape_thumb
                and self._make_color_tag and self._expiry_color_raw):
            kb = xbmc.Keyboard('', self._get_string('search_title'))
            kb.doModal()
            if not kb.isConfirmed():
                return
            query = kb.getText()
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for search
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            results = api.search(query)
            # If the API search failed or returned no results, try fallback endpoints
            if not results:
                fb = []
                ql = (query or '').lower()
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
                    xbmcgui.Dialog().notification('NLZiet', self._get_string('no_results', query), xbmcgui.NOTIFICATION_INFO)
                    xbmcplugin.endOfDirectory(self._handle)
                    return
            # Group search results by their detected type so we can present grouped
            # folders (e.g. "Series" and "Movies") when multiple groups are found.
            group_map = {}
            for item in results:
                try:
                    content_id = item.get('id') or item.get('contentId') or item.get('content_id')
                except Exception:
                    content_id = None
                try:
                    itype = item.get('type') or ''
                    itype_l = (str(itype).lower() if itype else '')
                except Exception:
                    itype_l = ''

                if not itype_l and content_id:
                    try:
                        det = api.get_content_detail(content_id) or {}
                        raw = det.get('raw') or {}
                        itype_l = (str(raw.get('type') or '')).lower()
                    except Exception:
                        itype_l = itype_l

                group = None
                if 'series' in itype_l or 'tvshow' in itype_l:
                    group = 'Series'
                elif 'episode' in itype_l:
                    group = 'Episodes'
                elif 'movie' in itype_l or 'film' in itype_l:
                    group = 'Movies'
                elif 'channel' in itype_l or 'live' in itype_l:
                    group = 'Channels'
                else:
                    sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
                    if sid:
                        group = 'Series'
                    else:
                        group = 'Other'

                group_map.setdefault(group, []).append(item)

            non_empty = [g for g, v in group_map.items() if v]
            # If results span multiple groups, present top-level folders for each group
            # so the user can open e.g. "Series" or "Movies" individually.
            if len(non_empty) > 1:
                for g in non_empty:
                    items_for_group = group_map.get(g) or []
                    thumb = None
                    try:
                        first = items_for_group[0] if items_for_group else None
                        thumb = self._pick_landscape_thumb(first) if first else None
                    except Exception:
                        thumb = None
                    label = f"{self._group_label(g)}: {self._get_string('found_count', len(items_for_group))}"
                    self._add_directory_item(label, {'mode': 'search_group', 'q': query, 'group': g}, is_folder=True, thumb=thumb)
                xbmcplugin.endOfDirectory(self._handle)
                return

            # Otherwise fall back to presenting each result individually (previous behavior)
            for item in results:
                info = None
                try:
                    # prefer description provided directly in the search result to avoid extra requests
                    desc = item.get('description') or item.get('subtitle') or ''
                    if desc:
                        title_for_info = item.get('title') or ''
                        expiry_text = item.get('expires_in') or None
                        truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                        # plot: include colored expiry on the first line for the info dialog
                        plot_full = desc
                        # plotoutline (label2): plain expiry prefix + truncated plot for default skin
                        po = truncated
                        if expiry_text:
                            marker = 'ðŸ”¶ '
                            colored = self._make_color_tag(self._expiry_color_raw, expiry_text)
                            plot_full = f"{colored}\n{desc}" if desc else colored
                            po = f"{marker}{expiry_text} â€” {truncated}" if truncated else f"{marker}{expiry_text}"
                        info = {
                            'title': title_for_info,
                            'plot': plot_full,
                            'plotoutline': po,
                        }
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
                                    info = {
                                        'title': title_for_info,
                                        'plot': plot_full,
                                        'plotoutline': po,
                                    }
                except Exception:
                    info = None
                # decide how to present the search result based on its detected type
                content_id = item.get('id') or item.get('contentId') or item.get('content_id')
                itype = item.get('type') or ''
                itype_l = (str(itype).lower() if itype else '')

                # If the inline type is not present try to fetch detail to detect it
                if not itype_l and content_id:
                    try:
                        det = api.get_content_detail(content_id) or {}
                        raw = det.get('raw') or {}
                        itype_l = (str(raw.get('type') or '')).lower()
                    except Exception:
                        itype_l = itype_l

                title = item.get('title') or item.get('name') or content_id or self._get_string('result')
                thumb = self._pick_landscape_thumb(item)

                # Determine a simple group label so search results indicate their type
                group = None
                if 'series' in itype_l or 'tvshow' in itype_l:
                    group = 'Series'
                elif 'episode' in itype_l:
                    group = 'Episodes'
                elif 'movie' in itype_l or 'film' in itype_l:
                    group = 'Movies'
                elif 'channel' in itype_l or 'live' in itype_l:
                    group = 'Channels'
                else:
                    sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
                    if sid:
                        group = 'Series'

                display_title = f"{self._group_label(group)}: {title}" if group else title

                # Series / TV show -> open series detail (folder)
                if 'series' in itype_l or 'tvshow' in itype_l:
                    self._add_directory_item(display_title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info, content=item)
                # Episode -> playable
                elif 'episode' in itype_l:
                    self._add_directory_item(display_title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info, content=item)
                # Movie -> playable
                elif 'movie' in itype_l or 'film' in itype_l:
                    self._add_directory_item(display_title, {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=thumb, info=info, content=item)
                # Channel / Live -> play as live
                elif 'channel' in itype_l or 'live' in itype_l:
                    self._add_directory_item(display_title, {'mode': 'play', 'id': item.get('id'), 'fmt': 'live'}, is_folder=False, thumb=thumb, info=info, content=item)
                else:
                    # fallback: treat as series if a seriesId exists, otherwise play
                    sid = item.get('seriesId') or (item.get('raw') or {}).get('seriesId') if isinstance(item.get('raw', {}), dict) else None
                    if sid:
                        self._add_directory_item(display_title, {'mode': 'series_detail', 'series_id': sid}, is_folder=True, thumb=thumb, info=info, content=item)
                    else:
                        self._add_directory_item(display_title, {'mode': 'play', 'id': item.get('id') or content_id}, is_folder=False, thumb=thumb, info=info, content=item)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['do_search']()

    def group(self, query, group):
        if (self._addon and self._get_api_instance and self._api_class
                and self._add_directory_item and self._pick_landscape_thumb
                and self._make_color_tag and self._expiry_color_raw):
            q = query
            if not q:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('missing_search_query'), xbmcgui.NOTIFICATION_INFO)
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
                    xbmcgui.Dialog().notification('NLZiet', self._get_string('no_results', q), xbmcgui.NOTIFICATION_INFO)
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

                title = item.get('title') or item.get('name') or content_id or self._get_string('result')
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
