import xbmcplugin


class BrowseController:
    """Browse and menu route adapter."""

    def __init__(self, handlers, handle=None, get_api_instance=None,
                 add_directory_item=None):
        self._handlers = handlers
        self._handle = handle
        self._get_api_instance = get_api_instance
        self._add_directory_item = add_directory_item

    def main_menu(self):
        return self._handlers['main_menu']()

    def series(self):
        return self._handlers['browse_series']()

    def series_detail(self, series_id):
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
