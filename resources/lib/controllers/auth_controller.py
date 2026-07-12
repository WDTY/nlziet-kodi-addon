import xbmcgui
import xbmc

from resources.lib import account_summary


class AuthController:
    """Authentication-related route adapter."""

    def __init__(self, handlers, get_string=None, addon=None,
                 get_api_instance=None, api_class=None):
        self._handlers = handlers
        self._get_string = get_string
        self._addon = addon
        self._get_api_instance = get_api_instance
        self._api_class = api_class

    def login(self):
        return self._handlers['do_login']()

    def logout(self, keep_mylist=False):
        return self._handlers['do_logout'](keep_mylist=keep_mylist)

    def confirm_logout(self):
        """Show confirmation dialogs before performing logout."""
        d = xbmcgui.Dialog()
        msg = self._get_string('logout_confirm_msg')
        try:
            ok = d.yesno('NLZiet', msg, yeslabel=self._get_string('logout_btn'), nolabel=self._get_string('cancel_btn'))
        except Exception:
            try:
                ok = d.yesno('NLZiet', msg)
            except Exception:
                ok = False

        if not ok:
            try:
                xbmcgui.Dialog().notification('NLZiet', self._get_string('logout_cancelled'), xbmcgui.NOTIFICATION_INFO)
            except Exception:
                pass
            return

        # Confirmed logout - now ask about My List
        keep_mylist = False
        try:
            keep = d.yesno('NLZiet', self._get_string('keep_mylist'), yeslabel=self._get_string('keep_mylist_btn'), nolabel=self._get_string('clear_mylist_btn'))
            keep_mylist = keep
        except Exception:
            try:
                keep = d.yesno('NLZiet', self._get_string('keep_mylist'))
                keep_mylist = keep
            except Exception:
                pass

        self._handlers['do_logout'](keep_mylist=keep_mylist)

    def account_summary(self):
        if self._addon and self._get_api_instance and self._api_class:
            return self.refresh_account_info()
        return self._handlers['refresh_account_info']()

    def refresh_account_info(self, notify=True):
        username = self._addon.getSetting('username')
        password = self._addon.getSetting('password')
        # Use cached API instance to avoid repeated disk I/O and initialization overhead
        try:
            api = self._get_api_instance()
        except Exception:
            # Fallback to creating a new instance if cache fails
            api = self._api_class(username=username, password=password)
        summary = api.get_customer_summary() or {}

        subscription = account_summary.extract_subscription_name(summary) or ''
        subscription_type = account_summary.extract_subscription_type(summary) or ''
        max_devices = account_summary.extract_max_devices(summary) or ''
        subscription_expires = account_summary.extract_subscription_expiry(summary) or ''

        try:
            self._addon.setSetting('subscription_name', subscription)
            self._addon.setSetting('subscription_type', subscription_type)
            self._addon.setSetting('max_devices', max_devices)
            self._addon.setSetting('subscription_expires', subscription_expires)
        except Exception:
            pass

        display_values = []
        if subscription:
            display_values.append(f"{self._get_string('subscription_label')}: {subscription}")
        if subscription_type:
            display_values.append(f"{self._get_string('subscription_type_label')}: {subscription_type}")
        if max_devices:
            display_values.append(f"{self._get_string('max_devices_label')}: {max_devices}")
        if subscription_expires:
            display_values.append(f"{self._get_string('expires_label')}: {subscription_expires}")

        if notify:
            if display_values:
                xbmcgui.Dialog().ok('NLZiet', (self._get_string('account_updated') or 'Account updated') + '\n' + '\n'.join(display_values))
            else:
                xbmcgui.Dialog().ok('NLZiet', self._get_string('account_parse_error') or 'Account info could not be parsed')
        else:
            if display_values:
                xbmc.log('NLZiet: Account info updated: ' + ', '.join(display_values), xbmc.LOGDEBUG)
            else:
                xbmc.log('NLZiet: Account info could not be parsed', xbmc.LOGDEBUG)

    def show_login_dialog(self, preset_email='', preset_password=''):
        """Show login dialog to get email and password from user."""
        dialog = xbmcgui.Dialog()

        # Get email from user (pre-filled if provided)
        # dialog.input(heading, defaultText='', type=0)
        email = dialog.input(self._get_string('login_dialog_email'), preset_email, type=0)
        if not email:
            return None, None

        # Get password from user (pre-filled if provided)
        password = dialog.input(self._get_string('login_dialog_password'), preset_password, type=0)
        if not password:
            return None, None

        return email, password
