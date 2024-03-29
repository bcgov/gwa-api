import os

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


def read(filename):
    file_path = os.path.join(os.path.dirname(__file__), filename)
    return open(file_path).read()

class PyTest(TestCommand):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ""

    def run_tests(self):
        import shlex

        # import here, cause outside the eggs aren't loaded
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


setup(
    name='gwa-kong',
    author='Aidan Cope',
    author_email='',
    version='1.2.0',
    description="GWA Kong API",
    long_description=read('README.md'),
    license='Apache 2.0',

    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'config',
        'authlib',
        'flask',
        'flask-cors',
        'flask-compress',
        'gevent',
        'pyyaml',
        'pyhcl',
        'python-keycloak',
        'requests',
        'swagger-ui-py==0.3.0',
        'flask-jwt-simple',
    ],
    setup_requires=[
    ],
    tests_require=[
        'mocker',
        'pytest',
        'pytest-cov',
        'pytest-mock',
        'pycodestyle',
        'pylint'
    ],
    cmdclass={"pytest": PyTest},
)
