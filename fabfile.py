"""Summary."""
from fabric.api import local, task


@task
def install(version=""):
    """Install project artifacts.

    Args:
        version (str, optional): Description
    """
    local("pip install -r requirements.txt")
    local("python setup.py install")


@task
def clean():
    """Remove all the .pyc files."""
    local("find . -name '*.pyc' -print0|xargs -0 rm", capture=False)
    # Remove the dist folder
    local("rm -rf ./dist && rm -rf ibu.egg-info")


@task
def push(msg):
    """Push to github.

    Args:
        msg (str, required): Description
    """
    local("git add . && git commit -m '{}'".format(msg))
    local("git push")


@task
def deploy(msg="deploy latest version"):
    """Deploy the app to PYPI.

    Args:
        msg (str, optional): Description
    """
    push(msg)
    build = local("python setup.py sdist")
    if build.succeeded:
        local("python setup.py upload")


@task
def test():
    """Test project."""
    local("python setup.py test")
