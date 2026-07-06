import os


def build_main_menu_entries(logged_in, addon_path, pick_png, get_label, path_exists=None):
    if path_exists is None:
        path_exists = os.path.exists
    entries = []

    if logged_in:
        explicit_logout_icon = os.path.join(addon_path, 'resources', 'media', 'menu_logout.png')
        logout_icon = explicit_logout_icon if explicit_logout_icon and path_exists(explicit_logout_icon) else pick_png('logout')
        entries.append({
            'title': get_label('sign_out'),
            'query': {'mode': 'logout_confirm'},
            'thumb': logout_icon,
        })
    else:
        entries.append({
            'title': get_label('login'),
            'query': {'mode': 'login'},
            'thumb': pick_png('login'),
        })

    if logged_in:
        entries.extend([
            {'title': get_label('manage_profiles'), 'query': {'mode': 'profiles'}, 'thumb': pick_png('profiles')},
            {'title': get_label('search'), 'query': {'mode': 'search'}, 'thumb': pick_png('search')},
            {'title': get_label('my_list'), 'query': {'mode': 'my_list'}, 'thumb': pick_png('mylist')},
            {'title': get_label('series'), 'query': {'mode': 'browse_series_categories'}, 'thumb': pick_png('series')},
            {'title': get_label('tv_shows'), 'query': {'mode': 'browse_tv_shows'}, 'thumb': pick_png('tvshows')},
            {'title': get_label('documentary'), 'query': {'mode': 'browse', 'type': 'documentary'}, 'thumb': pick_png('documentary')},
            {'title': get_label('movies'), 'query': {'mode': 'browse_movie_categories'}, 'thumb': pick_png('movies')},
            {'title': get_label('channels'), 'query': {'mode': 'browse', 'type': 'channels'}, 'thumb': pick_png('tv')},
        ])

    return entries


def render_main_menu(
    addon,
    handle,
    check_token_expiry,
    translate_path,
    pick_menu_png,
    refresh_account_info,
    is_logged_in,
    get_label,
    notify_info,
    add_directory_item,
    set_property,
    end_of_directory,
    log_debug,
    thread_factory,
    path_exists=None,
):
    if path_exists is None:
        path_exists = os.path.exists

    check_token_expiry()

    try:
        addon_path = translate_path(addon.getAddonInfo('path')) or ''
    except Exception:
        try:
            addon_path = addon.getAddonInfo('path') or ''
        except Exception:
            addon_path = ''

    def _pick_png(name):
        return pick_menu_png(addon_path, name)

    try:
        thread_factory(target=refresh_account_info, args=(False,), daemon=True).start()
    except Exception:
        log_debug('NLZiet: failed to start account refresh thread')

    logged_in = is_logged_in()

    if not logged_in:
        try:
            notify_info('NLZiet', get_label('login_notification'))
        except Exception:
            log_debug('NLZiet: failed to show login notification')

    for entry in build_main_menu_entries(logged_in, addon_path, _pick_png, get_label, path_exists=path_exists):
        add_directory_item(entry['title'], entry['query'], thumb=entry.get('thumb'))

    try:
        background_path = os.path.join(addon_path, 'resources', 'media', 'background.jpg')
        if path_exists(background_path):
            set_property(handle, 'fanart', background_path)
    except Exception:
        log_debug('NLZiet: failed to set background image')

    end_of_directory(handle)
