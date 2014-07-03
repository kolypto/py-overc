import pkg_resources

__version__ = pkg_resources.get_distribution('overc').version

from .src import OvercApplication
