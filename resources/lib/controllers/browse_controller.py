class BrowseController:
    """Browse and menu route adapter."""

    def __init__(self, handlers):
        self._handlers = handlers

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
        return self._handlers['browse_tv_shows']()

    def tv_genre(self, genre):
        return self._handlers['browse_tv_genre'](genre)

    def series_categories(self):
        return self._handlers['browse_series_categories']()

    def series_genre(self, genre):
        return self._handlers['browse_series_genre'](genre)

    def movie_categories(self):
        return self._handlers['browse_movie_categories']()

    def movie_genre(self, genre):
        return self._handlers['browse_movie_genre'](genre)

    def category(self, content_type):
        return self._handlers['browse_category'](content_type)
