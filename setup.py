from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='skytap-ansible-inventory',
    version='0.2',

    description='Skytap Ansible Inventory',
    long_description=long_description,
    long_description_content_type='text/markdown',

    url='https://github.com/skytap/skytap-ansible-inventory',

    author='Joe Burchett',
    author_email='jburchett@skytap.com',

    license='Apache 2.0',

    python_requires='>=3.6',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: System :: Systems Administration',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],

    keywords='skytap ansible inventory',
    py_modules=["skytap_inventory"],
    install_requires=[
        'requests==2.31.0',
        'configparser==6.0.0'
    ],


    entry_points={
        'console_scripts': [
            'skytap-inventory=skytap_inventory:main',
        ],
    },
)
