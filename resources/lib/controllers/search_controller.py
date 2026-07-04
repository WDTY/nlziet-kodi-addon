class SearchController:
    """Search route adapter."""

    def __init__(self, handlers):
        self._handlers = handlers

    def search(self):
        return self._handlers['do_search']()

    def group(self, query, group):
        return self._handlers['search_group'](query, group)
