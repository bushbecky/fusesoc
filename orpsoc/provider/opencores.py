from orpsoc.provider import Provider
from orpsoc.utils import Launcher

import os.path
import logging

logger = logging.getLogger(__name__)

class ProviderOpenCores(Provider):
    def __init__(self, config):
        logger.debug('__init__() *Entered*')
        self.repo_path = 'http://opencores.org/ocsvn/' + \
            config.get('repo_name') + '/' + config.get('repo_name') + '/' + \
            config.get('repo_root')
        self.revision_number  = config.get('revision')
        logger.debug('__init__() -Done-')

    def fetch(self, local_dir, core_name):
        logger.debug('fetch() *Entered*')
        status = self.status(local_dir)

        if status == 'empty':
            self._checkout(local_dir)
            return True
        elif status == 'modified':
            self.clean_cache()
            self._checkout(local_dir)
            return True
        elif status == 'outofdate':
            self._update()
            return True
        elif status == 'downloaded':
            return False
        else:
            print("provider status is: " + status + " This shouldn't happen")
            return False

    def status(self, local_dir):
        logger.debug('status() *Entered*')
        #FIXME: Check if repo is modified, or is an SVN repo at all, etc..
        if not os.path.isdir(local_dir):
            return 'empty'
        else:
            return 'downloaded'
        
    def _checkout(self, local_dir):
        logger.debug('_checkout() *Entered*')
        print("Checking out " + self.repo_path + " revision " + self.revision_number + " to " + local_dir)
        try:
            l = Launcher('svn', ['co', '-q', '--no-auth-cache',
                                 '-r', self.revision_number,
                                 '--username', 'orpsoc',
                                 '--password', 'orpsoc',
                                 self.repo_path,
                                 local_dir]).run()
        except RuntimeError as e:
            print("Error: Failed to checkout " + self.repo_path)
            print(e.value)
            exit(1)
        logger.debug('_checkout() -Done-')

    def _update(self):
        pass
