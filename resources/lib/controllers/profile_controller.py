class ProfileController:
    """Profile route adapter."""

    def __init__(self, handlers):
        self._handlers = handlers

    def manage(self):
        return self._handlers['manage_profiles']()

    def select(self, profile_id):
        return self._handlers['select_profile'](profile_id)

    def apply(self):
        return self._handlers['apply_profile']()
