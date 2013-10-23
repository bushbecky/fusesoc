from orpsoc.orpsocconfigparser import OrpsocConfigParser
from orpsoc.config import Config
import os
import logging

logger = logging.getLogger(__name__)

class System:
    def __init__(self, system_file):
        logger.debug('__init__() *Entered*' +
                     '\n    system_file=' + str(system_file)
                    )
        self.backend_name = None

        system_root = os.path.dirname(system_file)
        self.config = OrpsocConfigParser(system_file)

        self.name = os.path.basename(system_file).split('.')[0]

        if self.config.has_option('main', 'backend'):
            self.backend_name = self.config.get('main','backend')
            if self.backend_name and self.config.has_section(self.backend_name):
                self.backend = dict(self.config.items(self.backend_name))

        logger.debug('__init__() -Done-')

    def info(self):
        logger.debug('info() *Entered*')
        print("\nSYSTEM INFO")
        print("Name:                   " + self.name)

        show_list = lambda s: "\n                        ".join(s.split('\n'))

        if self.backend_name:
            print("Backend name:           " + self.backend_name)
            print("    family:             " + self.backend['family'])
            print("    device:             " + self.backend['device'])

            print("\n    tcl_files:          " + show_list(self.backend['tcl_files']))
            print("\n    sdc_files:          " + show_list(self.backend['sdc_files']))
            logger.debug('info() -Done-')

