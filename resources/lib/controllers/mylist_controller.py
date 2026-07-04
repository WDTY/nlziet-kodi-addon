class MyListController:
    """My List route adapter."""

    def __init__(self, handlers):
        self._handlers = handlers

    def list(self):
        return self._handlers['browse_my_list']()

    def group(self, group):
        return self._handlers['browse_my_list_group'](group)

    def toggle(self, item_id, title, content_type, thumb):
        return self._handlers['toggle_mylist'](
            item_id,
            title,
            content_type,
            thumb
        )
