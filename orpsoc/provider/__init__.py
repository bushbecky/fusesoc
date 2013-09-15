class Provider(object):
    def __init__(self, config):
        pass

    def fetch(self):
        pass

    def status(self, local_dir):
        pass

from orpsoc.provider.opencores import ProviderOpenCores
from orpsoc.provider.github import GitHub
from orpsoc.provider.url import ProviderURL

def ProviderFactory(items):
    if items.get('name') == 'opencores':
        return ProviderOpenCores(dict(items))
    elif items.get('name') == 'github':
        return GitHub(dict(items))
    elif items.get('name') == 'url':
        return ProviderURL(dict(items))
    else:
        raise Exception('Unknown provider')
