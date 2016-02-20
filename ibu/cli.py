# -*- coding: utf-8 -*-
from __future__ import print_function

import click


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group()
def ibu():
    """This is still a work in progress."""
    pass


@click.command(context_settings=CONTEXT_SETTINGS)
def test():
    print("hello")
