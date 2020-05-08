import logging

FORMATTER = '%(levelname)s %(message)s'


def get_logger(name):
    logger = logging.getLogger(name)

    handler = logging.StreamHandler()

    formatter = logging.Formatter(FORMATTER)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
