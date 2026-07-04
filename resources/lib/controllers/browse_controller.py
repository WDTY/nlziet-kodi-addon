from datetime import datetime

import xbmcgui
import xbmcplugin


class BrowseController:
    """Browse and menu route adapter."""

    def __init__(self, handlers, handle=None, get_api_instance=None,
                 add_directory_item=None, addon=None, api_class=None,
                 get_string=None, pick_landscape_thumb=None,
                 make_color_tag=None, expiry_color_raw=None):
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

    def main_menu(self):
        return self._handlers['main_menu']()

    def series(self):
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
        return self._handlers['show_series_season'](series_id, season_id)

    def placement_row(self, items_url, placement_id, comp_index):
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
        return self._handlers['browse_category'](content_type)
