TELEGRAM_ERRORS = (
    'Unauthorized',
    'BadRequest',
    'TimedOut',
    'NetworkError',
    'ServerError',
    'RetryAfter',
    'ConnectionError',
)
# Почему-то не проходят тесты TelegramError;
# Пишут о проблемах с импортом.
