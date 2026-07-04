class AuthController:
    """Authentication-related route adapter."""

    def __init__(self, handlers):
        self._handlers = handlers

    def login(self):
        return self._handlers['do_login']()

    def logout(self, keep_mylist=False):
        return self._handlers['do_logout'](keep_mylist=keep_mylist)

    def confirm_logout(self):
        return self._handlers['confirm_logout']()

    def account_summary(self):
        return self._handlers['refresh_account_info']()
