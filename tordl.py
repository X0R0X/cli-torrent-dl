#!/usr/bin/env python3

import argparse
import os
import sys

from tordl import config as cfg, func


def parse_args():
    class ArgParseFormatter(argparse.ArgumentDefaultsHelpFormatter):
        def _get_default_metavar_for_optional(self, action):
            return ''

    ap = argparse.ArgumentParser(
        description='CLI Torrent Downloader provides convenient and quick way '
                    'to search torrent magnet links (and to run associated '
                    f'torrent client) via major torrent sites ('
                    f'{', '.join(cfg.SEARCH_ENGINES)} by default) through '
                    f'a command line.',
        formatter_class=ArgParseFormatter
    )
    """
    Search / Generic
    """
    ap.add_argument(
        'search',
        nargs='*',
        default='',
        help='Search term. All positional arguments are concatenated to one '
             'string, no need for " "'
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
        '-n',
        '--page-num-download',
        dest='cfg_page_num_download',
        default=cfg.PAGE_NUM_DOWNLOAD,
        type=int,
        help='Fetch N pages of search results from search engines.'
    )
    ap.add_argument(
        '-o',
        '--timeout',
        dest='cfg_request_timeout',
        default=cfg.REQUEST_TIMEOUT,
        type=float,
        help='Search / fetch magnet URL request timeout.'
    )
    ap.add_argument(
        '-g',
        '--dont-aggregate-same-magnet-links',
        dest='cfg_aggregate_same_magnet_links',
        default=cfg.AGGREGATE_SAME_MAGNET_LINKS,
        action='store_false',
        help='If the magnet link of two search result is the same, aggregate it'
             ' to one record. Consider using --fetch-missing-magnet-links.'
    )
    ap.add_argument(
        '-m',
        '--fetch-missing-magnet-links',
        dest='cfg_fetch_missing_magnet_links',
        default=cfg.FETCH_MISSING_MAGNET_LINKS,
        action='store_true',
        help='Some torrent sites (1337x.to, limetorrents.info) don\'t provide '
             'magnet links in the search result - we need to fetch associated '
             'html link to obtain it. If this flag is turned on, tordl will '
             'fetch magnet links automatically. WARNING: This will considerably'
             ' slow down the search process.'
    )
    ap.add_argument(
        '-l',
        '--fetch-magnet-link-concurrence',
        dest='cfg_fetch_magnet_link_concurrence',
        default=cfg.FETCH_MAGNET_LINKS_CONCURRENCE,
        type=int,
        help='If --fetch-missing-magnet-links is turned on, tordl will be '
             'fetching N magnet links concurrently to speed up the process.'
    )
    ap.add_argument(
        '--exclude-search-off',
        dest='cfg_use_exclude_search',
        default=cfg.USE_EXCLUDE_SEARCH,
        action='store_false',
        help='Switch exclude search off. Exclude search enables You to filter '
             'out results containing excluded strings. Example: "tordl debian '
             '{d}8.0.0 {d}8.0.1"'.format(d=cfg.EXCLUDE_SEARCH_DELIMITER)
    )
    ap.add_argument(
        '--exclude-search-delimiter',
        dest='cfg_exclude_search-delimiter',
        default=cfg.EXCLUDE_SEARCH_DELIMITER,
        type=str,
        help='After this character sequence the next string is considered to be'
             ' excluded from search result.'
    )
    """
    System
    """
    ap.add_argument(
        '-R',
        '--revert-to-default',
        action='store_true',
        default=False,
        help='Purge all custom configuration and revert to default.'
    )
    ap.add_argument(
        '-r',
        '--reload-search-engines',
        action='store_true',
        default=False,
        help='Reload search engines from the source code. Useful when there is an update.'
    )
    ap.add_argument(
        '-c',
        '--torrent-client-cmd',
        dest='cfg_torrent_client_cmd',
        default=cfg.TORRENT_CLIENT_CMD,
        help='Command to execute torrent client with magnet link as a parameter'
    )

    """
    Mode Test Search Engines
    """
    ap.add_argument(
        '-t',
        '--test-search-engines',
        action='store_true',
        default=False,
        help=(
            'Test all active search engines for errors, or supply additional position '
            'arguments as preferred search engines'
        )
    )
    ap.add_argument(
        '--test-all',
        action='store_true',
        default=False,
        help='When running Search Engine Test, test all engines, not just '
             'currently selected ones.'
    )
    """
    Mode Direct Download
    """
    ap.add_argument(
        '-d',
        '--download',
        action='store_true',
        default=False,
        help='Directly download first search result, don\'t run UI.'
    )
    """
    Mode API
    """
    ap.add_argument(
        '-a',
        '--api',
        default=False,
        action='store_true',
        help='Run in API mode: fetch result and print json to the stdout. '
             'Consider using --fetch-missing-magnet-links as well.'
    )
    """
    Mode JSON RPC Server
    """
    ap.add_argument(
        '-s',
        '--rpc-server',
        default=False,
        action='store_true',
        help='Run JSON RPC Server. Consider using '
             '--fetch-magnet-link-concurrence as well.'
    )
    """
    Mode JSON RPC Client
    """
    ap.add_argument(
        '-q',
        '--rpc-client',
        default=False,
        action='store_true',
        help='Run as a JSON RPC Client.'
    )
    """
    Mode RPC Generic
    """
    ap.add_argument(
        '-i',
        '--rpc-bind',
        default='%s:%s' % (cfg.RPC_BIND_ADDRESS, cfg.RPC_BIND_PORT),
        type=str,
        help='RPC Server bind address and port. (ADDRESS:PORT format).'
    )
    """
    Run Modes Generic
    """
    ap.add_argument(
        '-p',
        '--pretty-json',
        dest='cfg_pretty_json',
        default=False,
        action='store_true',
        help='Print JSON in pretty format if using --api mode.'
    )

    parsed = ap.parse_args(sys.argv[1:])
    return parsed


if __name__ == "__main__":
    if '-R' in sys.argv or '--revert-to-default' in sys.argv:
        if os.path.exists(cfg.CFG_FILE):
            os.remove(cfg.CFG_FILE)
        if os.path.exists(cfg.CFG_ENGINES_FILE):
            os.remove(cfg.CFG_ENGINES_FILE)
        cfg.init_cfg()
        print('Reverted to default config.')
        exit(0)
    elif '-r' in sys.argv or '--reload-search-engines' in sys.argv:
        cfg.SEARCH_ENGINES = cfg.CFG_SEARCH_ENGINES_DEFAULT
        cfg.write_cfg()
        print('Default search engine settings reloaded.')
        exit(0)

    cfg.init_cfg()
    parsed_args = parse_args()
    cfg.override_cfg(parsed_args)

    term = ' '.join(parsed_args.search)

    if parsed_args.download:
        func.direct_download(term)
    elif parsed_args.test_search_engines:
        func.test_search_engines(parsed_args.test_all, term)
    elif parsed_args.api:
        print(func.run_api(term, parsed_args.cfg_pretty_json))
    elif parsed_args.rpc_server:
        func.run_rpc_server()
    elif parsed_args.rpc_client:
        func.run_rpc_client(term)
    else:
        func.run_curses_ui(term)

    exit(0)
