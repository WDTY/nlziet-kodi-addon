import xbmcgui


class IPTVController:
    """IPTV Manager settings route adapter."""

    def __init__(self, get_api_instance):
        self._get_api_instance = get_api_instance

    def select_channels(self):
        from resources.lib.iptvmgr import read_enabled_channels, save_enabled_channels
        api = self._get_api_instance()
        # Read the list of currently available channels from NLZiet
        available_channels = api.get_channels()
        available_ids = [chan['id'] for chan in available_channels]

        # Since Kodi's multi-select dialog selects items by listing indexes to
        # the selected items in its list, calculate the indexes of the currently
        # enabled channels.
        enabled_channels = read_enabled_channels(api)
        if enabled_channels is None:
            # Not saved yet, enable all
            enabled_indices = list(range(len(available_ids)))
        else:
            enabled_indices = []
            for chan_id in enabled_channels:
                try:
                    enabled_indices.append(available_ids.index(chan_id))
                except ValueError:
                    pass
        # Open a multiselect dialog and allow the user to make a new selection.
        new_indices = xbmcgui.Dialog().multiselect(
            api.addon.getAddonInfo('name'),
            [chan['title'] for chan in available_channels],
            preselect=enabled_indices
        )
        # Store the new selection to file.
        enabled_channels = [available_channels[idx]['id'] for idx in new_indices]
        save_enabled_channels(api, enabled_channels)
