"""
A database agnotics migration and data export tool.

Attributes:
    dependency_links (TYPE): Description
    here (TYPE): App setup and
    install_requires (TYPE): Description
    VERSION (str): Description
"""
import re
import ast

from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

_version_re = re.compile(r'__version__\s+=\s+(.*)')


with open('ibu/__init__.py', 'rb') as f:
    VERSION = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))


# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# get the dependencies and installs
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
dependency_links = [x.strip().replace('git+', '')
                    for x in all_reqs if 'git+' not in x]

setup(
    name='ibu',
    version=VERSION,
    description='A database agnotics migration and data export tool.',
    long_description=long_description,
    url='https://github.com/ojengwa/ibu',
    download_url='https://github.com/ojengwa/ibu/tarball/' + VERSION,
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
    ],
    keywords='database, migration, export, data, db, postgres, mysql,',
    packages=['ibu'],
    include_package_data=True,
    author='Bernard Ojengwa',
    install_requires=install_requires,
    depedency_links=dependency_links,
    author_email='bernardojengwa@gmail.com'
)
