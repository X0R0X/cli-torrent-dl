from pathlib import Path
from setuptools import find_packages, setup

def load_requirements():
    return [
        l.strip()
        for l in Path('requirements.txt').read_text().splitlines()
        if not l.startswith('#')
    ]

setup(
    name='tordl',
    packages=find_packages(where='tordl'),
    package_dir={
        '': 'tordl'
    },
    version='1.0.6',
    license='MIT',
    description='CLI Torrent Search and Download',
    author='x0r0x',
    author_email='jakub.schimer@protonmail.com',
    url='https://github.com/X0R0X/cli-torrent-dl/',
    download_url='https://github.com/X0R0X/cli-torrent-dl/archive/refs/heads/master.zip',
    keywords=['torrent', 'search', 'download', 'cli', 'curses'],
    install_requires=load_requirements(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Developers',
        'Topic :: Communications :: File Sharing',
        'Topic :: Home Automation',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: Terminals',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
    ],
)
