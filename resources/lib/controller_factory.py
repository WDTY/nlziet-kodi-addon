from resources.lib.controllers import (
    AuthController,
    BrowseController,
    IPTVController,
    MyListController,
    PlaybackController,
    ProfileController,
    SearchController,
)


def build_route_handlers(legacy_handlers, dependencies):
    auth = AuthController(
        legacy_handlers,
        dependencies['get_string'],
        dependencies['addon'],
        dependencies['get_api_instance'],
        dependencies['api_class']
    )
    browse = BrowseController(
        legacy_handlers,
        dependencies['handle'],
        dependencies['get_api_instance'],
        dependencies['add_directory_item'],
        dependencies['addon'],
        dependencies['api_class'],
        dependencies['get_string'],
        dependencies['pick_landscape_thumb'],
        dependencies['make_color_tag'],
        dependencies['expiry_color_raw'],
        dependencies['get_channels_menu_data']
    )
    mylist = MyListController(
        legacy_handlers,
        dependencies['addon'],
        dependencies['handle'],
        dependencies['get_api_instance'],
        dependencies['api_class'],
        dependencies['add_directory_item'],
        dependencies['pick_landscape_thumb'],
        dependencies['get_string']
    )
    iptv = IPTVController(dependencies['get_api_instance'])
    playback = PlaybackController(legacy_handlers)
    profile = ProfileController(legacy_handlers)
    search = SearchController(
        legacy_handlers,
        dependencies['addon'],
        dependencies['handle'],
        dependencies['get_api_instance'],
        dependencies['api_class'],
        dependencies['add_directory_item'],
        dependencies['pick_landscape_thumb'],
        dependencies['make_color_tag'],
        dependencies['expiry_color_raw']
    )
    return {
        'main_menu': browse.main_menu,
        'do_login': auth.login,
        'do_search': search.search,
        'manage_profiles': profile.manage,
        'browse_my_list': mylist.list,
        'browse_my_list_group': mylist.group,
        'toggle_mylist': mylist.toggle,
        'select_profile': profile.select,
        'apply_profile': profile.apply,
        'browse_series': browse.series,
        'do_logout': auth.logout,
        'confirm_logout': auth.confirm_logout,
        'refresh_account_info': auth.account_summary,
        'search_group': search.group,
        'show_series_detail': browse.series_detail,
        'show_series_season': browse.series_season,
        'browse_placement_row': browse.placement_row,
        'browse_tv_shows': browse.tv_shows,
        'browse_tv_genre': browse.tv_genre,
        'browse_series_categories': browse.series_categories,
        'browse_series_genre': browse.series_genre,
        'browse_movie_categories': browse.movie_categories,
        'browse_movie_genre': browse.movie_genre,
        'browse_category': browse.category,
        'play_item': playback.play,
        'select_iptv_channels': iptv.select_channels,
    }
