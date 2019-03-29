import random
import logging


LOG = logging.getLogger('avocado.test')


def random_select(source, count=1):
    if count > len(source):
        raise Exception("Select count out of range")
    return random.sample(source, count)