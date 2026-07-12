class PlaybackController:
    """Playback route adapter."""

    def __init__(self, handlers):
        self._handlers = handlers

    def play(self, content_id, **params):
        return self._handlers['play_item'](content_id, **params)

    def filter_manifest_subtitles(self, manifest_url):
        """
        Placeholder for future manifest filtering.
        Currently unused - we use player subtitle API instead.
        """
        return manifest_url
