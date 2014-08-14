#!/usr/bin/env python
""" Simplistic monitoring solution that is a pleasure to use """

from setuptools import setup, find_packages

setup(
    # http://pythonhosted.org/setuptools/setuptools.html
    name='overc',
    version='1.0.9-1',
    author='Mark Vartanyan',
    author_email='kolypto@gmail.com',

    url='https://github.com/kolypto/py-overc',
    license='BSD',
    description=__doc__,
    long_description=open('README.rst').read(),
    keywords=['monitoring'],

    packages=find_packages(),
    scripts=[],
    entry_points={
        'console_scripts': [
            'overcli = overcli:main',
        ]
    },

    install_requires=[
    ],
    extras_require={
        'server': [
            'flask >= 0.10.1',
            'sqlalchemy >= 0.9.6',
            'mysql-python >= 1.2.5'
        ],
        '_dev': ['wheel', 'nose', 'freezegun']
    },
    include_package_data=True,
    zip_safe=False,  # so we can access resources
    test_suite='tests',

    platforms='any',
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        #'Programming Language :: Python :: 3',
    ],
)
