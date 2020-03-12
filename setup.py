#!/usr/bin/env python

import os
from setuptools import setup, find_packages
from django_dag_admin import __version__
import codecs

def root_dir():
    try:
        return os.path.dirname(__file__)
    except NameError:
        return '.'

classifiers = [
    "Development Status :: 1 - Pre-Alpha",
    "Intended Audience :: Developers",
    'License :: License :: Other/Proprietary License',
    "Programming Language :: Python",
    "Operating System :: OS Independent",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
    "Environment :: Web Environment",
    "Framework :: Django",
    'Framework :: Django :: 2.0',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3.6',
]

setup_args=dict(
    name='django-dag-admin',
    version=__version__,
    url='https://github.com/gammascience/django-dag-admin',
    author='Paul Gammans',
    author_email='pgammans@gannascience.co.uk',
    license='',
    packages=find_packages(exclude=['docs']),
    package_dir={'django_dag_admin': 'django_dag_admin'},
    #package_data={'dag': ['templates/admin/*.html']},
    description='Admin interface for Django-DAG a Directed Acyclic Graph implementation for Django',
    classifiers=classifiers,
    long_description=codecs.open(
            os.path.join(root_dir(), 'README.rst'), encoding='utf-8'
        ).read(),

)

if __name__ == '__main__':
    setup(**setup_args)
