import logging

FORMATTER = '%(asctime)s %(levelname)s %(module)s %(process)d %(thread)d %(message)s'

logging.basicConfig(format=FORMATTER)


def get_logger(name):
    logger = logging.getLogger(name)

    handler = logging.StreamHandler()

    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    return logger
