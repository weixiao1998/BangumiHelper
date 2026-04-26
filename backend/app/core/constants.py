class RegistrationMode:
    OPEN = "open"
    CLOSED = "closed"
    INVITE_ONLY = "invite_only"

    ALL_MODES = [OPEN, CLOSED, INVITE_ONLY]

    @classmethod
    def is_valid(cls, mode: str) -> bool:
        return mode in cls.ALL_MODES
