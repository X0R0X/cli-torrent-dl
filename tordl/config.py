import json
import os
import sys

from xdg.BaseDirectory import save_config_path

from tordl import engines

CFG_DIR = os.path.join(
    os.path.expanduser('~'), save_config_path('torrentdl')
)
CFG_FILE = os.path.join(CFG_DIR, 'config.json')
CFG_ENGINES_FILE = os.path.join(CFG_DIR, 'engines.py')
CFG_HISTORY_FILE = os.path.join(CFG_DIR, 'search_history.txt')

SEARCH_ENGINES = [
    '1337x', 'BTDB', 'Glo', 'KAT', 'Lime',
    'Nyaa', 'Solid', 'TGx', 'TPB', 'Zooqle'
]
TORRENT_CLIENT_CMD = 'qbittorrent %s'
TORRENT_CLIPBOARD_MODE = False
BROWSER_CMD = 'firefox %s'

HISTORY_MAX_LENGTH = 100

PAGE_NUM_DOWNLOAD = 1
REQUEST_TIMEOUT = 5

AGGREGATE_SAME_MAGNET_LINKS = True
FETCH_MISSING_MAGNET_LINKS = False
FETCH_MAGNET_LINKS_CONCURRENCE = 20

USE_EXCLUDE_SEARCH = True
EXCLUDE_SEARCH_DELIMITER = '::-'

PRETTY_JSON = False

RPC_BIND_ADDRESS = '127.0.0.1'
RPC_BIND_PORT = 57000
RPC_USER = ''
RPC_PASS = ''


def mk_cfg():
    mod = sys.modules[__name__]
    attrs = dir(mod)
    omit = (
        'os',
        'json',
        'sys',
        'mk_cfg',
        'init_cfg',
        'override_cfg',
        'write_cfg',
        'engines',
        'save_config_path'
    )
    config = {}
    for a in attrs:
        if not a.startswith('CFG') and not a.startswith('__') and a not in omit:
            config[a.lower()] = getattr(mod, a)

    return config


def write_cfg():
    with open(CFG_FILE, 'w') as f:
        f.write(json.dumps(mk_cfg(), indent=4))


def init_cfg():
    if not os.path.exists(CFG_DIR):
        os.makedirs(CFG_DIR)

    if not os.path.exists(CFG_FILE):
        write_cfg()

    if not os.path.exists(CFG_ENGINES_FILE):
        with open(engines.__file__) as f:
            engines_module = f.read()

        with open(CFG_ENGINES_FILE, 'w') as f:
            f.write(engines_module)

    with open(CFG_FILE) as f:
        config = json.load(f)

    mod = sys.modules[__name__]
    for k, v in config.items():
        setattr(mod, k.upper(), v)


def override_cfg(args):
    mod = sys.modules[__name__]

    mod.SEARCH_ENGINES = args.cfg_search_engines.replace(' ', '').split(',')
    mod.RPC_SERVER_BIND_ADDRESS, mod.RPC_SERVER_BIND_PORT = \
        args.rpc_bind.split(':')

    omit = ('cfg_search_engines', 'tordl')
    prefix = 'cfg_'
    for k in args.__dict__:
        if k.startswith(prefix) and k not in omit:
            setattr(mod, k.upper()[len(prefix):], getattr(args, k))
