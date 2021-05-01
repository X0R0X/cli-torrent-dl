#!/usr/bin/env python3

import argparse
import curses
import os
import shutil
import sys
from functools import partial

from tordl import config as cfg, core
from tordl.app import App


def parse_args():
    class ArgParseFormatter(argparse.ArgumentDefaultsHelpFormatter):
        def _get_default_metavar_for_optional(self, action):
            return ''

    ap = argparse.ArgumentParser(
        description='CLI Torrent Downloader provides convenient and quick way '
                    'to search torrent magnet links (and to run associated '
                    'torrent client) via major torrent sites (ThePirateBay, '
                    'LimeTorrents, Zooqle, 1337x, GloTorrents, KickAssTorrents '
                    'by default) through command line.',
        formatter_class=ArgParseFormatter
    )
    ap.add_argument(
        'search',
        nargs='*',
        default='',
        help='Search term. All positional arguments are concatenated to one '
             'string, no need for " "'
    )
    ap.add_argument(
        '-r',
        '--revert-to-default',
        action='store_true',
        default=False,
        help='Purge all custom configuration and revert to default.'
    )
    ap.add_argument(
        '-e',
        '--search-engines',
        dest='cfg_search_engines',
        default=','.join(cfg.SEARCH_ENGINES),
        help='Search engines to be used for torrent search. Overrides the value'
             ' loaded from config in %s' % cfg.CFG_FILE
    )
    ap.add_argument(
        '-c',
        '--torrent-client-cmd',
        dest='cfg_torrent_client_cmd',
        default=cfg.TORRENT_CLIENT_CMD,
        help='Command to execute torrent client with magnet link as a parameter'
    )
    ap.add_argument(
        '-b',
        '--browser-cmd',
        dest='cfg_browser_cmd',
        default=cfg.BROWSER_CMD,
        help='Command to open torrent link in a browser.'
    )
    ap.add_argument(
        '-d',
        '--download',
        action='store_true',
        default=False,
        help='Directly download first search result, don\'t run UI.'
    )
    ap.add_argument(
        '-t',
        '--test-search-engines',
        action='store_true',
        default=False,
        help='Test all active search engines for errors.'
    )
    ap.add_argument(
        '-n',
        '--page-num-download',
        dest='cfg_page_num_download',
        default=cfg.PAGE_NUM_DOWNLOAD,
        type=int,
        help='Fetch N pages of search results from search engines.'
    )
    ap.add_argument(
        '-a',
        '--api',
        default=False,
        action='store_true',
        help='Run in API mode: fetch result and print json to the stdout.'
    )
    ap.add_argument(
        '-p',
        '--pretty-json',
        default=False,
        action='store_true',
        help='Print JSON in pretty format if using --api mode.'
    )
    ap.add_argument(
        '-o',
        '--timeout',
        dest='cfg_request_timeout',
        default=cfg.REQUEST_TIMEOUT,
        type=float,
        help='Search / fetch magnet URL request timeout.'
    )
    parsed = ap.parse_args(sys.argv[1:])
    return parsed


def run_curses_ui(st):
    os.environ.setdefault('ESCDELAY', '0')
    curses.wrapper(partial(App, search=st))


if __name__ == "__main__":
    if '-r' in sys.argv or '--revert-to-default' in sys.argv:
        if os.path.exists(cfg.CFG_DIR):
            shutil.rmtree(cfg.CFG_DIR)
        cfg.init_cfg()
        print('Reverted to default config.')
        exit(0)

    cfg.init_cfg()
    parsed_args = parse_args()
    cfg.override_cfg(parsed_args)

    search_term = ' '.join(parsed_args.search)

    if parsed_args.download:
        core.direct_download(search_term)
    elif parsed_args.test_search_engines:
        core.test_search_engines()
    elif parsed_args.api:
        core.run_api(search_term, parsed_args.pretty_json)
    else:
        run_curses_ui(search_term)

    exit(0)
