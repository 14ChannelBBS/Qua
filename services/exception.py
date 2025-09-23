class VerificationRequired(Exception):
    def __init__(self, turnstileSiteKey: str, *args):
        super().__init__(*args)
        self.turnstileSiteKey = turnstileSiteKey


class ContentTooLong(Exception):
    def __init__(self, type: str, max: int, *args):
        super().__init__(*args)
        self.type = type
        self.max = max


class ContentTooShort(Exception):
    def __init__(self, type: str, min: int, *args):
        super().__init__(*args)
        self.type = type
        self.min = min


class PostThreadRateLimit(Exception):
    def __init__(self, remain: int, *args):
        super().__init__(*args)
        self.remain = remain


class PostResponseRateLimit(PostThreadRateLimit):
    pass
