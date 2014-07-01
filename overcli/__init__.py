#! /usr/bin/env python

import pkg_resources

__author__ = "Mark Vartanyan"
__email__ = "kolypto@gmail.com"
__version__ = pkg_resources.get_distribution('overc').version

from overcli.commands import main

if __name__ == '__main__':
    main()
