from resources.lib.i18n import get_string


def test_get_string_returns_dutch_translation():
    assert get_string('search') == 'Zoeken'


def test_get_string_formats_arguments():
    assert get_string('no_items_for_group', 'Series') == 'Geen items gevonden voor Series'


def test_get_string_falls_back_to_key():
    assert get_string('missing-key') == 'missing-key'
