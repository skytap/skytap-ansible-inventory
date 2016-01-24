from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='skytap-ansible-inventory',
    version='0.1',

    description='Skytap Ansible Inventory',
    long_description=long_description,

    url='https://github.com/skytap/skytap-ansible-inventory',

    author='Joe Burchett',
    author_email='jburchett@skytap.com',

    license='Apache 2.0',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: System :: Systems Administration',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='skytap ansible inventory',
    py_modules=["skytap_inventory"],
    install_requires=['six', 'requests'],

    entry_points={
        'console_scripts': [
            'skytap_inventory=skytap_inventory:main',
        ],
    },
)
