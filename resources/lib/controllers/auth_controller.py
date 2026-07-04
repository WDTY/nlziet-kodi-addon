import xbmcgui


class AuthController:
    """Authentication-related route adapter."""

    def __init__(self, handlers, get_string=None):
        self._handlers = handlers
        self._get_string = get_string

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
        return self._handlers['refresh_account_info']()

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
