import sys
import types

import pytest


class KodiRecorder:
    def __init__(self):
        self.set_content = []
        self.ended = []
        self.notifications = []
        self.executed = []

    def reset(self):
        self.__init__()


RECORDER = KodiRecorder()


class FakeAddon:
    def __init__(self, addon_id='plugin.video.nlziet', path='C:/addon'):
        self._info = {'id': addon_id, 'path': path}
        self._settings = {}

    def getAddonInfo(self, key):
        return self._info.get(key, '')

    def getSetting(self, key):
        return self._settings.get(key, '')

    def setSetting(self, key, value):
        self._settings[key] = value


class FakeDialog:
    def notification(self, heading, message, icon=None):
        RECORDER.notifications.append((heading, message, icon))


@pytest.fixture(autouse=True)
def reset_kodi_recorder():
    RECORDER.reset()
    yield
    RECORDER.reset()


@pytest.fixture
def kodi_recorder():
    return RECORDER


@pytest.fixture
def fake_addon():
    return FakeAddon()


def _install_kodi_stubs():
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGDEBUG = 0
    xbmc.LOGINFO = 1
    xbmc.LOGWARNING = 2
    xbmc.LOGERROR = 3
    xbmc.executebuiltin = lambda command: RECORDER.executed.append(command)
    xbmc.translatePath = lambda path: path
    xbmc.log = lambda *args, **kwargs: None
    xbmc.Player = type('Player', (), {})

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.NOTIFICATION_INFO = 'info'
    xbmcgui.NOTIFICATION_ERROR = 'error'
    xbmcgui.Dialog = FakeDialog

    xbmcplugin = types.ModuleType('xbmcplugin')
    xbmcplugin.setContent = lambda handle, content: RECORDER.set_content.append((handle, content))
    xbmcplugin.endOfDirectory = lambda handle: RECORDER.ended.append(handle)
    xbmcplugin.setProperty = lambda *args, **kwargs: None

    xbmcaddon = types.ModuleType('xbmcaddon')
    xbmcaddon.Addon = lambda *args, **kwargs: FakeAddon()

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda path: path

    sys.modules.setdefault('xbmc', xbmc)
    sys.modules.setdefault('xbmcgui', xbmcgui)
    sys.modules.setdefault('xbmcplugin', xbmcplugin)
    sys.modules.setdefault('xbmcaddon', xbmcaddon)
    sys.modules.setdefault('xbmcvfs', xbmcvfs)


_install_kodi_stubs()
