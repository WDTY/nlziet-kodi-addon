import xbmcgui
import xbmcplugin


class MyListController:
    """My List route adapter."""

    def __init__(self, handlers, addon=None, handle=None, get_api_instance=None,
                 api_class=None, add_directory_item=None,
                 pick_landscape_thumb=None, get_string=None):
        self._handlers = handlers
        self._addon = addon
        self._handle = handle
        self._get_api_instance = get_api_instance
        self._api_class = api_class
        self._add_directory_item = add_directory_item
        self._pick_landscape_thumb = pick_landscape_thumb
        self._get_string = get_string

    def list(self):
        if (
            self._addon
            and self._get_api_instance
            and self._api_class
            and self._add_directory_item
            and self._pick_landscape_thumb
            and self._get_string
        ):
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for faster list loading
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            try:
                items = api.get_my_list() or []
            except Exception:
                items = []

            if not items:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('my_list_empty'), xbmcgui.NOTIFICATION_INFO)
                xbmcplugin.endOfDirectory(self._handle)
                return
            # Group My List items into Series/Movies/Other so the My List top-level
            # shows folders the user can open to view each category.
            groups = {'Series': [], 'Movies': [], 'Other': []}
            for itm in items:
                try:
                    typ = (itm.get('type') or '').lower()
                    if 'series' in typ or 'tvshow' in typ:
                        groups['Series'].append(itm)
                    elif 'movie' in typ or 'film' in typ:
                        groups['Movies'].append(itm)
                    else:
                        groups['Other'].append(itm)
                except Exception:
                    groups['Other'].append(itm)

            # Present folders for each non-empty group (Series and Movies prioritized)
            folder_order = ['Series', 'Movies', 'Other']
            any_folder = False
            for g in folder_order:
                lst = groups.get(g) or []
                if not lst:
                    continue
                first = lst[0] if lst else None
                thumb = self._pick_landscape_thumb(first) if first else None
                label = f"{g}: {len(lst)} found"
                self._add_directory_item(label, {'mode': 'my_list_group', 'group': g}, is_folder=True, thumb=thumb)
                any_folder = True

            if not any_folder:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('my_list_empty'), xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_my_list']()

    def group(self, group):
        if (
            self._addon
            and self._get_api_instance
            and self._api_class
            and self._add_directory_item
            and self._get_string
        ):
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance for faster group loading
            try:
                api = self._get_api_instance()
            except Exception:
                api = self._api_class(username=username, password=password)
            try:
                items = api.get_my_list() or []
            except Exception:
                items = []

            if not items:
                xbmcgui.Dialog().notification('NLZiet', 'My List is empty', xbmcgui.NOTIFICATION_INFO)
                xbmcplugin.endOfDirectory(self._handle)
                return

            filtered = []
            for itm in items:
                try:
                    typ = (itm.get('type') or '').lower()
                    if group == 'Series' and ('series' in typ or 'tvshow' in typ):
                        filtered.append(itm)
                    elif group == 'Movies' and ('movie' in typ or 'film' in typ):
                        filtered.append(itm)
                    elif group == 'Other' and not ('series' in typ or 'tvshow' in typ or 'movie' in typ or 'film' in typ):
                        filtered.append(itm)
                except Exception:
                    continue

            if not filtered:
                no_items_text = self._get_string('no_items_for_group') or 'No items found for {}'
                xbmcgui.Dialog().notification('NLZiet', no_items_text.format(group), xbmcgui.NOTIFICATION_INFO)
                xbmcplugin.endOfDirectory(self._handle)
                return

            for itm in filtered:
                try:
                    title = itm.get('title') or itm.get('name') or itm.get('id') or 'Item'
                    thumb = itm.get('thumb') or itm.get('posterUrl') or None
                    typ = (itm.get('type') or '').lower()
                    if 'series' in typ or 'tvshow' in typ:
                        self._add_directory_item(title, {'mode': 'series_detail', 'series_id': itm.get('id')}, is_folder=True, thumb=thumb, content=itm)
                    elif 'episode' in typ:
                        self._add_directory_item(title, {'mode': 'play', 'id': itm.get('id')}, is_folder=False, thumb=thumb, content=itm)
                    elif 'movie' in typ or 'film' in typ:
                        self._add_directory_item(title, {'mode': 'play', 'id': itm.get('id')}, is_folder=False, thumb=thumb, content=itm)
                    else:
                        self._add_directory_item(title, {'mode': 'play', 'id': itm.get('id')}, is_folder=False, thumb=thumb, content=itm)
                except Exception:
                    continue
            xbmcplugin.endOfDirectory(self._handle)
            return None
        return self._handlers['browse_my_list_group'](group)

    def toggle(self, item_id, title, content_type, thumb):
        return self._handlers['toggle_mylist'](
            item_id,
            title,
            content_type,
            thumb
        )
