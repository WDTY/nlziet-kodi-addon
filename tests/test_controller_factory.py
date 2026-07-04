from resources.lib.controller_factory import build_route_handlers


class ExplodingApi:
    pass


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
            'add_directory_item': lambda *args, **kwargs: None,
            'pick_landscape_thumb': lambda item: 'thumb',
            'make_color_tag': lambda color, text: text,
            'expiry_color_raw': 'FFFFFFFF',
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
            'add_directory_item': lambda *args, **kwargs: added.append((args, kwargs)),
            'pick_landscape_thumb': lambda item: 'picked-thumb',
            'make_color_tag': lambda color, text: text,
            'expiry_color_raw': 'FFFFFFFF',
            'get_string': lambda key, *args: key,
        }
    )

    handlers['browse_my_list']()

    assert added[0][0][0] == 'Movies: 1 found'
    assert added[0][1]['thumb'] == 'picked-thumb'
