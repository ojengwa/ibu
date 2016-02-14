# -*- coding: utf-8 -*-
from __future__ import print_function
import yaml
import click

from __init__ import docs_url

DEFAULT_DB_ALIAS = 'src'


class Config(object):
    """Configuration options"""

    def __init__(self, config_file='manifest.yml'):

        try:
            with open(config_file) as stream:
                self.config = yaml.safe_load(stream)
                return(self.config)
        except IOError as e:
            msg = e.strerror + ': ' + e.filename
            msg += '\nPlease review the project docs at {0} ' + docs_url
            click.echo(msg)
