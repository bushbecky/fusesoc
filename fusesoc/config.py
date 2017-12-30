import logging

import sys
if sys.version[0] == '2':
    import ConfigParser as configparser
else:
    import configparser

import os

logger = logging.getLogger(__name__)

class Config(object):
    archbits = 0

    def __init__(self, path=None, file=None):
        #TODO: Add option to load custom config file
        self.build_root = None
        self.cache_root = None
        self.cores_root = []
        self.systems_root = None

        config = configparser.SafeConfigParser()
        if file is None:
            if path is None:
                xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or \
                          os.path.join(os.path.expanduser('~'), '.config')
                config_files = ['/etc/fusesoc/fusesoc.conf',
                        os.path.join(xdg_config_home, 'fusesoc','fusesoc.conf'),
                        'fusesoc.conf']
            else:
                config_files = [path]

            logger.debug('Looking for config files from ' + ':'.join(config_files))
            files_read = config.read(config_files)
            logger.debug('Found config files in ' + ':'.join(files_read))
        else:
            logger.debug('Using supplied config file')
            if sys.version[0] == '2':
                config.readfp(file)
            else:
                config.read_file(file)
            file.seek(0)

        for item in ['build_root', 'cache_root', 'systems_root']:
            try:
                setattr(self, item, config.get('main', item))
            except configparser.NoOptionError:
                pass
            except configparser.NoSectionError:
                pass
        item = 'cores_root'
        try:
            setattr(self, item, config.get('main', item).split())
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass

        #Set fallback values
        if self.build_root is None:
            self.build_root   = os.path.abspath('build')
        if self.cache_root is None:
            xdg_cache_home = os.environ.get('XDG_CACHE_HOME') or \
                             os.path.join(os.path.expanduser('~'), '.cache')
            self.cache_root = os.path.join(xdg_cache_home, 'fusesoc')
            if not os.path.exists(self.cache_root):
                os.makedirs(self.cache_root)
        if self.cores_root is None and os.path.exists('cores'):
            self.cores_root   = [os.path.abspath('cores')]
        if self.systems_root is None and os.path.exists('systems'):
            self.systems_root = os.path.abspath('systems')

        logger.debug('build_root='+self.build_root)
        logger.debug('cache_root='+self.cache_root)
        logger.debug('cores_root='+':'.join(self.cores_root))
        logger.debug('systems_root='+self.systems_root if self.systems_root else "Not defined")
