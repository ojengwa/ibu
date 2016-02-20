# -*- coding: utf-8 -*-
"""
Summary.

Attributes:
    CONTEXT_SETTINGS (TYPE): Description
"""
from __future__ import print_function

import click


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(name='ibu')
@click.option('-d/-s', '--debug/--silent', default=False)
@click.option('-v', '--version')
def cli():
    """
    Summary.

    Returns:
        TYPE: Description
    """


@cli.command(context_settings=CONTEXT_SETTINGS)
def fixture():
    """
    Summary.

    Returns:
        TYPE: Description
    """
    print("hello")


@cli.command(context_settings=CONTEXT_SETTINGS)
def schema():
    """
    Summary.

    Returns:
        TYPE: Description
    """
    print("hello")

if __name__ == '__main__':
    cli()