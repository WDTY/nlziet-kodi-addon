from datetime import datetime, timedelta
import re

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import xbmc
import xbmcgui
import xbmcplugin


class BrowseController:
    """Browse and menu route adapter."""

    def __init__(self, handlers, handle=None, get_api_instance=None,
                 add_directory_item=None, addon=None, api_class=None,
                 get_string=None, pick_landscape_thumb=None,
                 make_color_tag=None, expiry_color_raw=None,
                 get_channels_menu_data=None):
        self._handlers = handlers
        self._handle = handle
        self._get_api_instance = get_api_instance
        self._add_directory_item = add_directory_item
        self._addon = addon
        self._api_class = api_class
        self._get_string = get_string
        self._pick_landscape_thumb = pick_landscape_thumb
        self._make_color_tag = make_color_tag
        self._expiry_color_raw = expiry_color_raw
        self._get_channels_menu_data = get_channels_menu_data

    def main_menu(self):
        return self._handlers['main_menu']()

    def series(self):
        if (self._addon and self._get_api_instance and self._api_class
                and self._add_directory_item and self._pick_landscape_thumb
                and self._make_color_tag and self._expiry_color_raw):
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for faster menu navigation
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)

            # Prefer placement rows (home/explore layout) when available
            try:
                comps = api.get_placement_rows('explore-series') or []
            except Exception:
                comps = []

            if comps:
                for idx, comp in enumerate(comps):
                    try:
                        comp_title = comp.get('title') or comp.get('name') or comp.get('id') or f"Row {idx+1}"
                        # Skip placement rows we don't want in the Series submenu
                        try:
                            comp_id = comp.get('id') or comp.get('placementId') or comp.get('name') or ''
                        except Exception:
                            comp_id = ''
                        lower_title = str(comp_title).strip().lower()
                        if lower_title == 'series' or str(comp_id).lower() == 'explore-series-genres':
                            continue
                        items_url = comp.get('itemsUrl') or comp.get('url') or (comp.get('link', {}) or {}).get('href') if isinstance(comp.get('link', {}), dict) else comp.get('itemsUrl')
                        # Provide a folder that opens the row contents. If the component
                        # exposes an itemsUrl we pass it directly; otherwise we pass the
                        # placement id + index so the handler can re-fetch inline items.
                        query = {'mode': 'placement_row'}
                        if items_url:
                            query['items_url'] = items_url
                        else:
                            query['placement_id'] = 'explore-series'
                            query['comp_index'] = str(idx)
                        self._add_directory_item(comp_title, query, is_folder=True)
                    except Exception:
                        continue
                xbmcplugin.endOfDirectory(self._handle)
                return

            # Fallback: simple series list when placements are unavailable
            results = api.get_series_list()
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
                        info = {
                            'title': title_for_info,
                            'plot': plot_full,
                            'plotoutline': po,
                        }
                except Exception:
                    info = None
                self._add_directory_item(item.get('title') or item.get('id') or 'Series', {'mode': 'series_detail', 'series_id': item.get('id')}, is_folder=True, thumb=self._pick_landscape_thumb(item), info=info, content=item)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_series']()

    def series_detail(self, series_id):
        if (self._addon and self._get_api_instance and self._api_class
                and self._add_directory_item and self._get_string):
            if not series_id:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('missing_series_id'), xbmcgui.NOTIFICATION_ERROR)
                return
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for faster detail loading
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            detail = api.get_series_detail(series_id)
            if not detail:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('unable_fetch_series'), xbmcgui.NOTIFICATION_ERROR)
                return
            seasons = detail.get('seasons') or []
            # If no seasons discovered, offer direct episode listing
            if not seasons:
                self._add_directory_item(self._get_string('all_episodes'), {'mode': 'series_season', 'series_id': series_id, 'season_id': ''}, is_folder=True)
            else:
                for s in seasons:
                    title = s.get('title') or f"{self._get_string('season')} {s.get('id')}"
                    self._add_directory_item(title, {'mode': 'series_season', 'series_id': series_id, 'season_id': s.get('id')}, is_folder=True)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['show_series_detail'](series_id)

    def series_season(self, series_id, season_id):
        if (self._addon and self._get_api_instance and self._api_class
                and self._add_directory_item and self._get_string
                and self._pick_landscape_thumb):
            if not series_id:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('missing_series_id'), xbmcgui.NOTIFICATION_ERROR)
                return
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for faster episode loading
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            xbmc.log(f"NLZiet show_series_season: series_id={series_id} season_id={season_id}", xbmc.LOGDEBUG)
            episodes = api.get_series_episodes(series_id, season_id=season_id or None, limit=400)
            # If the API returned no episodes, but the `season_id` appears to be
            # an items/episodes URL, attempt to fetch items directly from that URL
            # (some detail payloads expose an `episodes_url` instead of numeric ids).
            if not episodes and season_id and isinstance(season_id, str) and (season_id.startswith('http') or '/episodes' in season_id or 'items' in season_id):
                try:
                    xbmc.log(f"NLZiet attempting fallback get_items_from_url for season_id={season_id}", xbmc.LOGDEBUG)
                    episodes = api.get_items_from_url(season_id) or []
                except Exception:
                    episodes = []
            if not episodes:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('no_episodes_found'), xbmcgui.NOTIFICATION_INFO)
                return
            for ep in episodes:
                info = None
                try:
                    desc = ep.get('description') or ep.get('subtitle') or ''
                    title_for_info = ep.get('title') or ''
                    aired_date = ep.get('raw', {}).get('broadcastAt') or ep.get('aired_date') or ep.get('broadcastDate') or ep.get('aired') or None

                    # Format broadcast date info
                    date_info = ''
                    if aired_date:
                        try:
                            # Parse and format date
                            if 'T' in aired_date:
                                date_obj = datetime.fromisoformat(aired_date.replace('Z', '+00:00'))
                            else:
                                date_obj = datetime.strptime(aired_date, '%Y-%m-%d')

                            date_formatted = date_obj.strftime('%d-%m-%Y')
                            date_info = f"Uitgezonden: {date_formatted}"
                        except Exception:
                            date_info = ''

                    # Build description with broadcast date if available
                    plot_full = desc
                    po = desc

                    if date_info:
                        plot_full = f"{date_info}\n{desc}" if desc else date_info
                        po = f"{date_info} â€” {desc[:100]}" if desc else date_info

                    if desc or date_info:
                        truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                        info = {
                            'title': title_for_info,
                            'plot': plot_full,
                            'plotoutline': po,
                        }
                except Exception:
                    info = None

                # Prefer an already-formatted episode numbering string when available.
                # First, prefer subtitle patterns like 'S1:A2' (some payloads include
                # this canonical format in `subtitle`). If present, use it as
                # "S1:A2 <Episode Title>". Otherwise fall back to the API's
                # formatted label or numeric SxxExx formatting.
                formatted_label = ep.get('formatted_episode_numbering') or ep.get('formattedEpisodeNumbering') or (ep.get('raw') or {}).get('formattedEpisodeNumbering')
                label_title = ep.get('title') or ''

                # Check subtitle for the canonical 'S{n}:A{m}' pattern (e.g. 'S1:A2 Secrets').
                # If present, extract the remainder of the subtitle after the code and
                # prefer that as the human-friendly episode title ("S1:A2 <ep title>").
                subtitle_code = None
                sub = ''
                try:
                    sub = ep.get('subtitle') or ''
                    if sub and isinstance(sub, str):
                        m = re.search(r"\bS\d+:A\d+\b", sub, re.I)
                        if m:
                            subtitle_code = m.group(0)
                            # remainder after the matched code
                            remainder = sub[m.end():].strip()
                            # strip common separators (colon, dash, en-dash, em-dash)
                            remainder = re.sub(r'^[\s\-:\u2013\u2014]+', '', remainder)
                        else:
                            remainder = ''
                    else:
                        remainder = ''
                except Exception:
                    subtitle_code = None
                    remainder = ''

                if subtitle_code:
                    if remainder:
                        label = f"{subtitle_code} {remainder}"
                    else:
                        # no explicit episode title in subtitle, show code and fall back to series title if available
                        label = f"{subtitle_code} - {label_title}" if label_title else subtitle_code
                elif sub and isinstance(sub, str) and sub.strip():
                    # subtitle exists but contains no S#:A# code â€” use the subtitle as
                    # the human-friendly episode title (e.g. 'Korfspiracy').
                    label = sub.strip()
                elif formatted_label:
                    # Use the canonical formatted label from the API/app when present
                    label = f"{formatted_label} - {label_title}" if label_title else formatted_label
                else:
                    # Prefer normalized episode_number/season_number when available
                    ep_num = ep.get('episode_number') or ep.get('episodeNumber') or ep.get('number') or ep.get('episode')
                    season_num = ep.get('season_number') or ep.get('seasonNumber') or None
                    label = label_title or ''
                    try:
                        n = int(ep_num) if ep_num is not None and str(ep_num).isdigit() else None
                    except Exception:
                        n = None
                    try:
                        s = int(season_num) if season_num is not None and str(season_num).isdigit() else None
                    except Exception:
                        s = None

                    if n is not None:
                        if s is not None:
                            label = f"S{s:02d}E{n:02d} - {label}" if label else f"S{s:02d}E{n:02d}"
                        else:
                            label = f"Episode {n} - {label}" if label else f"Episode {n}"
                    else:
                        label = label or ep.get('id') or 'Episode'

                self._add_directory_item(label, {'mode': 'play', 'id': ep.get('id')}, is_folder=False, thumb=self._pick_landscape_thumb(ep), info=info, content=ep)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['show_series_season'](series_id, season_id)

    def placement_row(self, items_url, placement_id, comp_index):
        if (self._addon and self._get_api_instance and self._api_class
                and self._add_directory_item and self._get_string
                and self._pick_landscape_thumb and self._make_color_tag
                and self._expiry_color_raw):
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for faster placement loading
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            items = []

            # Direct items URL
            if items_url:
                try:
                    items = api.get_items_from_url(items_url) or []
                except Exception:
                    items = []
            # Fallback: fetch placement and use inline items by index
            elif placement_id is not None and comp_index is not None:
                try:
                    comps = api.get_placement_rows(placement_id) or []
                    idx = int(comp_index)
                    comp = comps[idx] if 0 <= idx < len(comps) else None
                    if comp:
                        if isinstance(comp.get('items'), list) and comp.get('items'):
                            for itm in comp.get('items'):
                                src = itm.get('item') if isinstance(itm, dict) and itm.get('item') else itm.get('content') if isinstance(itm, dict) and itm.get('content') else itm
                                if isinstance(src, dict):
                                    items.append(src)
                        else:
                            u = comp.get('itemsUrl') or comp.get('url') or (comp.get('link', {}) or {}).get('href')
                            if u:
                                items = api.get_items_from_url(u) or []
                except Exception:
                    items = []

            if not items:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('no_items_found'), xbmcgui.NOTIFICATION_INFO)
                return

            for src in items:
                try:
                    content_id = src.get('id') or src.get('contentId') or src.get('content_id') or src.get('seriesId') or src.get('movieId') or src.get('assetId')
                    title = src.get('title') or src.get('name') or ''
                    thumb = self._pick_landscape_thumb(src)
                    desc = src.get('description') or src.get('summary') or ''
                    info = None
                    if desc:
                        expiry_text = src.get('expires_in') or None
                        truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                        plot_full = desc
                        po = truncated
                        if expiry_text:
                            marker = 'ðŸ”¶ '
                            colored = self._make_color_tag(self._expiry_color_raw, expiry_text)
                            plot_full = f"{colored}\n{desc}" if desc else colored
                            po = f"{marker}{expiry_text} â€” {truncated}" if truncated else f"{marker}{expiry_text}"
                        info = {'title': title, 'plot': plot_full, 'plotoutline': po}

                    if content_id:
                        # Treat as series when possible
                        self._add_directory_item(title, {'mode': 'series_detail', 'series_id': content_id}, is_folder=True, thumb=thumb, info=info, content=src)
                    else:
                        self._add_directory_item(title, {'mode': 'play', 'id': src.get('playUrl') or src.get('streamUrl') or src.get('id')}, is_folder=False, thumb=thumb, info=info, content=src)
                except Exception:
                    continue
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_placement_row'](
            items_url,
            placement_id,
            comp_index
        )

    def tv_shows(self):
        if self._get_api_instance and self._add_directory_item:
            api = self._get_api_instance()

            genres = api.get_tv_show_genres()
            for genre in genres:
                query = {'mode': 'browse_tv_genre', 'genre': genre.get('genre') or 'all'}
                self._add_directory_item(genre.get('name'), query, is_folder=True)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_tv_shows']()

    def tv_genre(self, genre):
        if (self._get_api_instance and self._add_directory_item
                and self._pick_landscape_thumb and self._make_color_tag
                and self._expiry_color_raw):
            api = self._get_api_instance()

            # Get shows for the genre (None for 'all')
            genre_param = None if genre == 'all' else genre
            results = api.get_videos_by_genre(genre=genre_param, limit=999)

            for item in results:
                # Use subtitle as primary display title if available (for episodes with episode names)
                display_title = item.get('subtitle') or item.get('title') or ''
                info = None
                try:
                    desc = item.get('description') or item.get('subtitle') or ''
                    title_for_info = item.get('title') or ''
                    expiry_text = item.get('expires_in') or None
                    aired_date = item.get('aired_date') or None

                    truncated = (desc[:250] + '...') if len(desc) > 250 else desc
                    plot_full = desc
                    po = truncated

                    # Add aired/broadcast date info if available
                    date_info = ''
                    if aired_date:
                        try:
                            # Parse and format date
                            if 'T' in aired_date:
                                date_obj = datetime.fromisoformat(aired_date.replace('Z', '+00:00'))
                            else:
                                date_obj = datetime.strptime(aired_date, '%Y-%m-%d')

                            date_formatted = date_obj.strftime('%d-%m-%Y')
                            date_info = f"Uitgezonden: {date_formatted}"
                        except Exception:
                            date_info = ''

                    # Build full plot with date info
                    parts = []
                    if date_info:
                        parts.append(date_info)
                    if expiry_text:
                        marker = 'ðŸ”¶ '
                        colored = self._make_color_tag(self._expiry_color_raw, expiry_text)
                        parts.append(colored)
                    if desc:
                        parts.append(desc)

                    plot_full = '\n'.join(parts) if parts else ''

                    # Build plotoutline with date
                    po_parts = []
                    if date_info:
                        po_parts.append(date_info)
                    if expiry_text:
                        marker = 'ðŸ”¶ '
                        po_parts.append(f"{marker}{expiry_text}")
                    if truncated:
                        po_parts.append(truncated)

                    po = ' â€” '.join(po_parts) if po_parts else truncated

                    # Create info if we have any data (title, date, or description)
                    if title_for_info or date_info or expiry_text or desc:
                        info = {
                            'title': title_for_info,
                            'plot': plot_full,
                            'plotoutline': po,
                        }
                except Exception:
                    info = None

                # Determine query mode based on item type
                item_type = (item.get('type') or '').lower()
                query = {'mode': 'play', 'id': item.get('id')}
                is_folder = False

                if item_type == 'series':
                    # Series open as folders showing seasons/episodes
                    query = {'mode': 'series_detail', 'series_id': item.get('id')}
                    is_folder = True

                self._add_directory_item(display_title, query, is_folder=is_folder, thumb=self._pick_landscape_thumb(item), info=info, content=item)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_tv_genre'](genre)

    def series_categories(self):
        if self._get_api_instance and self._add_directory_item:
            api = self._get_api_instance()

            genres = api.get_series_genres()
            for genre in genres:
                name = genre.get('name')
                genre_param = genre.get('genre')
                self._add_directory_item(name, {'mode': 'browse_series_genre', 'genre': genre_param or 'all'}, is_folder=True)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_series_categories']()

    def series_genre(self, genre):
        if (self._get_api_instance and self._add_directory_item
                and self._pick_landscape_thumb and self._make_color_tag
                and self._expiry_color_raw):
            api = self._get_api_instance()

            # Handle "all" as None for the API
            genre_param = None if genre == 'all' else genre
            results = api.get_series_by_genre(genre_param)

            for item in results:
                item_type = item.get('type', 'Series')
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
                        info = {
                            'title': title_for_info,
                            'plot': plot_full,
                            'plotoutline': po,
                        }
                except Exception:
                    info = None

                # Series items should open as folders showing seasons/episodes
                if item_type == 'Series':
                    self._add_directory_item(item.get('title') or item.get('id') or 'Series', {'mode': 'series_detail', 'series_id': item.get('id')}, is_folder=True, thumb=self._pick_landscape_thumb(item), info=info, content=item)
                else:
                    # Episodes would be playable - but shouldn't appear at top level in genre view
                    pass

            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_series_genre'](genre)

    def movie_categories(self):
        if self._get_api_instance and self._add_directory_item:
            api = self._get_api_instance()

            genres = api.get_movie_genres()
            for genre in genres:
                name = genre.get('name')
                genre_param = genre.get('genre')
                self._add_directory_item(name, {'mode': 'browse_movie_genre', 'genre': genre_param or 'all'}, is_folder=True)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_movie_categories']()

    def movie_genre(self, genre):
        if (self._get_api_instance and self._add_directory_item
                and self._pick_landscape_thumb and self._make_color_tag
                and self._expiry_color_raw):
            api = self._get_api_instance()

            # Handle "all" as None for the API
            genre_param = None if genre == 'all' else genre
            results = api.get_movies_by_genre(genre_param)

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
                        info = {
                            'title': title_for_info,
                            'plot': plot_full,
                            'plotoutline': po,
                        }
                except Exception:
                    info = None

                # Movies are playable items
                self._add_directory_item(item.get('title'), {'mode': 'play', 'id': item.get('id')}, is_folder=False, thumb=self._pick_landscape_thumb(item), info=info, content=item)

            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_movie_genre'](genre)

    def category(self, content_type):
        if (self._addon and self._get_api_instance and self._api_class
                and self._add_directory_item and self._pick_landscape_thumb
                and self._make_color_tag and self._expiry_color_raw
                and self._get_channels_menu_data):
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for faster menu navigation
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            epg_map = {}
            if content_type.lower() == 'movies':
                results = api.get_movies()
            elif content_type.lower() == 'videos':
                results = api.get_videos()
            elif content_type.lower() == 'documentary':
                results = api.get_documentaries()
            elif content_type.lower() == 'channels':
                results, epg_map = self._get_channels_menu_data(api)
            else:
                results = api.search(content_type, content_type=content_type)
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
                        info = {
                            'title': title_for_info,
                            'plot': plot_full,
                            'plotoutline': po,
                        }
                    else:
                        cid = item.get('id')
                        # Skip detail fetch for channels - they don't support /v9/content/detail/ endpoint
                        if cid and content_type.lower() != 'channels':
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
                        # Attach EPG info for channels (current 'Nu live' and next 'Straks')
                        if content_type.lower() == 'channels' and item.get('id'):
                            try:
                                channel_id = item.get('id')
                                channel_epg = epg_map.get(channel_id)

                                # New structure: channel_epg has 'current' and 'next' keys
                                if channel_epg:
                                    now = datetime.now(tz=ZoneInfo('Europe/Amsterdam'))
                                    now_plus_6 = now + timedelta(hours=6)
                                    epg_lines = []
                                    for pgm in channel_epg:
                                        # only supports python >= 3.7
                                        start = datetime.fromisoformat(pgm['start'])
                                        end = datetime.fromisoformat(pgm['stop'])
                                        if end > now_plus_6:
                                            break
                                        if end > now:
                                            epg_lines.append(' - '.join((
                                                start.strftime("%H:%M"),
                                                pgm["title"])))

                                    # Update info with EPG data
                                    if epg_lines:
                                        epg_text = '\n'.join(epg_lines[:12])
                                        if info:
                                            info['plotoutline'] = epg_text
                                            info['plot'] = epg_text
                                        else:
                                            firstpgm = epg_lines[0].split(" - ", 1)[1]
                                            info = {'title': f"{item.get('title')}   [COLOR orange]{firstpgm}[/COLOR]",
                                                    'plotoutline': epg_text,
                                                    'plot': epg_text}
                                            item['title'] = info['title']
                            except (KeyError, TypeError):
                                pass
                except Exception as e:
                    info = None

                # Determine query mode based on item type
                # Documentaries and Series should open series detail, not try to play directly
                item_type = (item.get('type') or '').lower()
                query = {'mode': 'play', 'id': item.get('id')}
                is_folder = False

                if item_type == 'series' or content_type.lower() == 'documentary':
                    # Series and documentaries open as folders with series detail
                    query = {'mode': 'series_detail', 'series_id': item.get('id')}
                    is_folder = True
                elif content_type.lower() == 'channels':
                    query['fmt'] = 'live'

                self._add_directory_item(item.get('title'), query, is_folder=is_folder, thumb=self._pick_landscape_thumb(item), info=info, content=item)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_category'](content_type)
