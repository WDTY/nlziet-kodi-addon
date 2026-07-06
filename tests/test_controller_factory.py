from resources.lib.controller_factory import build_route_dependencies, build_route_handlers


class ExplodingApi:
    pass


def test_factory_builds_route_dependencies(fake_addon):
    def get_api_instance():
        return 'api'

    def build_url(query):
        return query

    def add_directory_item(*args, **kwargs):
        return None

    def pick_landscape_thumb(item):
        return item

    def make_color_tag(color, text):
        return text

    def get_channels_menu_data(api):
        return api

    def get_string(key, *args):
        return key

    dependencies = build_route_dependencies(
        fake_addon,
        9,
        get_api_instance,
        ExplodingApi,
        build_url,
        add_directory_item,
        pick_landscape_thumb,
        make_color_tag,
        'FFFFFFFF',
        get_channels_menu_data,
        get_string,
    )

    assert dependencies == {
        'addon': fake_addon,
        'handle': 9,
        'get_api_instance': get_api_instance,
        'api_class': ExplodingApi,
        'build_url': build_url,
        'add_directory_item': add_directory_item,
        'pick_landscape_thumb': pick_landscape_thumb,
        'make_color_tag': make_color_tag,
        'expiry_color_raw': 'FFFFFFFF',
        'get_channels_menu_data': get_channels_menu_data,
        'get_string': get_string,
    }


def test_factory_creates_expected_route_handlers_without_side_effects(fake_addon):
    calls = []

    def fail_if_called():
        raise AssertionError('factory construction should not fetch API')

    handlers = build_route_handlers(
        {'do_login': lambda: calls.append('login')},
        {
            'addon': fake_addon,
            'handle': 9,
            'get_api_instance': fail_if_called,
            'api_class': ExplodingApi,
            'build_url': lambda query: 'url',
            'add_directory_item': lambda *args, **kwargs: None,
            'pick_landscape_thumb': lambda item: 'thumb',
            'make_color_tag': lambda color, text: text,
            'expiry_color_raw': 'FFFFFFFF',
            'get_channels_menu_data': lambda api: ([], {}),
            'get_string': lambda key, *args: key,
        }
    )

    assert {
        'main_menu', 'do_login', 'browse_my_list', 'browse_my_list_group',
        'toggle_mylist', 'play_item', 'select_iptv_channels'
    }.issubset(handlers)

    handlers['do_login']()
    assert calls == ['login']


def test_factory_my_list_handler_uses_shared_dependencies(fake_addon):
    items = [{'id': 'm1', 'title': 'Movie', 'type': 'movie'}]
    added = []

    class Api:
        def get_my_list(self):
            return items

    handlers = build_route_handlers(
        {},
        {
            'addon': fake_addon,
            'handle': 12,
            'get_api_instance': lambda: Api(),
            'api_class': Api,
            'build_url': lambda query: 'url',
            'add_directory_item': lambda *args, **kwargs: added.append((args, kwargs)),
            'pick_landscape_thumb': lambda item: 'picked-thumb',
            'make_color_tag': lambda color, text: text,
            'expiry_color_raw': 'FFFFFFFF',
            'get_channels_menu_data': lambda api: ([], {}),
            'get_string': lambda key, *args: key,
        }
    )

    handlers['browse_my_list']()

    assert added[0][0][0] == 'Movies: 1 found'
    assert added[0][1]['thumb'] == 'picked-thumb'
