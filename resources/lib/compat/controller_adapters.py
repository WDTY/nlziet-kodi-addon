BrowseController = None
MyListController = None
ProfileController = None
SearchController = None


def _get_controller(name):
    global BrowseController, MyListController, ProfileController, SearchController

    controller = globals()[name]
    if controller is not None:
        return controller

    from resources.lib import controllers

    controller = getattr(controllers, name)
    globals()[name] = controller
    return controller


def _browse_controller(dependencies, variant='full'):
    controller = _get_controller('BrowseController')
    args = [
        {},
        dependencies['handle'],
        dependencies['get_api_instance'],
        dependencies['add_directory_item'],
    ]
    if variant in ('detail', 'full'):
        args.extend([
            dependencies['addon'],
            dependencies['api_class'],
            dependencies['get_string'],
        ])
    if variant == 'full':
        args.extend([
            dependencies['pick_landscape_thumb'],
            dependencies['make_color_tag'],
            dependencies['expiry_color_raw'],
            dependencies['get_channels_menu_data'],
        ])
    return controller(*args)


def _search_controller(dependencies):
    return _get_controller('SearchController')(
        {},
        dependencies['addon'],
        dependencies['handle'],
        dependencies['get_api_instance'],
        dependencies['api_class'],
        dependencies['add_directory_item'],
        dependencies['pick_landscape_thumb'],
        dependencies['make_color_tag'],
        dependencies['expiry_color_raw'],
        dependencies['get_string'],
    )


def _profile_controller(dependencies, handlers=None):
    return _get_controller('ProfileController')(
        handlers or {},
        dependencies['addon'],
        dependencies['get_api_instance'],
        dependencies['api_class'],
        dependencies['build_url'],
        dependencies['handle'],
        dependencies['add_directory_item'],
        dependencies['make_color_tag'],
        dependencies['get_string'],
    )


def _mylist_controller(dependencies):
    return _get_controller('MyListController')(
        {},
        dependencies['addon'],
        dependencies['handle'],
        dependencies['get_api_instance'],
        dependencies['api_class'],
        dependencies['add_directory_item'],
        dependencies['pick_landscape_thumb'],
        dependencies['get_string'],
    )


def browse_series_categories(dependencies):
    return _browse_controller(dependencies, variant='basic').series_categories()


def browse_series_genre(dependencies, genre=None):
    return _browse_controller(dependencies).series_genre(genre)


def browse_series(dependencies):
    return _browse_controller(dependencies).series()


def show_series_detail(dependencies, series_id):
    return _browse_controller(dependencies, variant='detail').series_detail(series_id)


def show_series_season(dependencies, series_id, season_id, episodes_url=None):
    return _browse_controller(dependencies).series_season(series_id, season_id, episodes_url)


def export_series_library(dependencies, series_id):
    return _browse_controller(dependencies).export_series_library(series_id)


def browse_tv_shows(dependencies):
    return _browse_controller(dependencies, variant='basic').tv_shows()


def browse_tv_genre(dependencies, genre=None):
    return _browse_controller(dependencies).tv_genre(genre)


def browse_movie_categories(dependencies):
    return _browse_controller(dependencies, variant='basic').movie_categories()


def browse_movie_genre(dependencies, genre=None):
    return _browse_controller(dependencies).movie_genre(genre)


def browse_placement_row(dependencies, items_url=None, placement_id=None, comp_index=None):
    return _browse_controller(dependencies).placement_row(items_url, placement_id, comp_index)


def browse_category(dependencies, content_type):
    return _browse_controller(dependencies).category(content_type)


def do_search(dependencies):
    return _search_controller(dependencies).search()


def search_group(dependencies, q, group):
    return _search_controller(dependencies).group(q, group)


def manage_profiles(dependencies):
    return _profile_controller(dependencies).manage()


def select_profile(dependencies, profile_id, manage_profiles_handler):
    return _profile_controller(
        dependencies,
        {'manage_profiles': manage_profiles_handler},
    ).select(profile_id)


def browse_my_list(dependencies):
    return _mylist_controller(dependencies).list()


def browse_my_list_group(dependencies, group):
    return _mylist_controller(dependencies).group(group)


def toggle_mylist(dependencies, item_id=None, title=None, type=None, thumb=None):
    return _mylist_controller(dependencies).toggle(item_id, title, type, thumb)
