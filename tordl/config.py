import os

CFG_DIR = os.path.join(os.path.expanduser('~'), '.torrentdl')
CFG_FILE = os.path.join(CFG_DIR, 'config.json')
CFG_ENGINES_FILE = os.path.join(CFG_DIR, 'engines.py')
CFG_HISTORY_FILE = os.path.join(CFG_DIR, 'search_history.txt')

SEARCH_ENGINES = ['Zooqle', 'TPB', 'Lime', '1337x', 'Glo', 'KAT']
TORRENT_CLIENT_CMD = 'qbittorrent %s'
BROWSER_CMD = 'firefox %s'
HISTORY_MAX_LENGTH = 100
PAGE_NUM_DOWNLOAD = 1
