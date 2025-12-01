from setuptools import setup, find_packages
from codecs import open
from os import path
import sys
sys.path.append('./controller')
from version import __version__
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()
setup(
    name='controller',
    version=__version__,
    description='Controller for Raspberry Pi',
    long_description=long_description,
    url='https://github.com/rushiranpise/controller',
    author='SunFounder',
    author_email='service@sunfounder.com',
    license='GNU',
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU License',
        'Programming Language :: Python :: 3',
    ],
    keywords='sunfounder, Controller',
    packages=find_packages(exclude=[ 'doc', 'tests*' ,'examples']),
    install_requires=['websockets'],
    entry_points={
        'console_scripts': [
            '',
        ],
    },
)
