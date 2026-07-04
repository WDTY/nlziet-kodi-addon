import xbmcgui
import xbmcplugin


class BrowseController:
    """Browse and menu route adapter."""

    def __init__(self, handlers, handle=None, get_api_instance=None,
                 add_directory_item=None, addon=None, api_class=None,
                 get_string=None):
        self._handlers = handlers
        self._handle = handle
        self._get_api_instance = get_api_instance
        self._add_directory_item = add_directory_item
        self._addon = addon
        self._api_class = api_class
        self._get_string = get_string

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
        return self._handlers['browse_movie_genre'](genre)

    def category(self, content_type):
        return self._handlers['browse_category'](content_type)
