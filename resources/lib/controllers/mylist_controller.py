import xbmcgui
import xbmcplugin
import xbmc


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
        if (
            self._addon
            and self._get_api_instance
            and self._api_class
            and self._get_string
        ):
            username = self._addon.getSetting('username')
            password = self._addon.getSetting('password')
            # Use cached API instance to respond instantly to My List actions
            try:
                api = self._get_api_instance()
            except Exception:
                # Fallback to creating a new instance if cache fails
                api = self._api_class(username=username, password=password)
            if not item_id:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('missing_id_mylist'), xbmcgui.NOTIFICATION_ERROR)
                return
            # Defensive: only allow Series or Movies to be toggled
            if content_type and isinstance(content_type, str):
                tl = content_type.lower()
                if not any(x in tl for x in ('series', 'tvshow', 'movie', 'film')):
                    xbmcgui.Dialog().notification('NLZiet', self._get_string('only_series_movies'), xbmcgui.NOTIFICATION_INFO)
                    return
            else:
                # try to detect content type from detail
                try:
                    det = api.get_content_detail(item_id) or {}
                    raw_type = (det.get('raw') or {}).get('type') or det.get('type') or ''
                    if raw_type and not any(x in str(raw_type).lower() for x in ('series', 'tvshow', 'movie', 'film')):
                        xbmcgui.Dialog().notification('NLZiet', self._get_string('only_series_movies'), xbmcgui.NOTIFICATION_INFO)
                        return
                except Exception:
                    pass
            try:
                itm = {'id': item_id, 'title': title, 'type': content_type, 'posterUrl': thumb}
                if api.is_in_my_list(item_id):
                    removed = api.remove_from_my_list(item_id)
                    if removed:
                        xbmcgui.Dialog().notification('NLZiet', 'Removed from My List', xbmcgui.NOTIFICATION_INFO)
                    else:
                        xbmcgui.Dialog().notification('NLZiet', 'Failed to remove from My List', xbmcgui.NOTIFICATION_ERROR)
                else:
                    added = api.add_to_my_list(itm)
                    if added:
                        xbmcgui.Dialog().notification('NLZiet', 'Added to My List', xbmcgui.NOTIFICATION_INFO)
                    else:
                        xbmcgui.Dialog().notification('NLZiet', 'Failed to add to My List', xbmcgui.NOTIFICATION_ERROR)
            except Exception:
                xbmcgui.Dialog().notification('NLZiet', 'My List action failed', xbmcgui.NOTIFICATION_ERROR)
            # Refresh the current container so context menu changes reflect immediately
            try:
                xbmc.executebuiltin('Container.Refresh')
            except Exception:
                pass
            return None
        return self._handlers['toggle_mylist'](
            item_id,
            title,
            content_type,
            thumb
        )
