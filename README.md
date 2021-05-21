# CLI Torrent Downloader

<img src="./img/tordl.gif" width="732">

## About
CLI Torrent Downloader provides convenient and quick way to search torrent  
magnet links (and to run associated torrent client) via major torrent sites 
(ThePirateBay, LimeTorrents, Zooqle, 1337x, GloTorrents, KickAssTorrents, 
SolidTorrents, BTDB, TGx, Nyaa by default) through command line.

## Prerequisites
* Python 3.8+

## Installation   

    $ ./setup.sh

## Config
Edit `~/.config/torrentdl/config.json` to customize your preferred torrent 
client and 
browser (default is qbittorent and firefox).

## Docker
Opening magnet links in your preferred torrent client will not work, of course.

### Build

    $ docker build . -t tordl

### Run JSON RPC Server

    $ docker run -p 57000:57000 -it tordl -s

## Usage

### CLI Usage
Run search from command line:

    $ tordl debian 8

Exclude search results containing user defined strings:

    $ tordl debian ::-8 ::-7 (...)

Show help:

    $ tordl -h

### Browse Mode Usage
* KEY_DOWN, KEY_UP, PAGE_UP, PAGE_DOWN - Navigate
* ENTER - Run torrent client
* SPACE - Open torrent info URL in browser
* ESC - exit
* / - Search
* a - Sort by source (torrent search engine) 
* s - Sort by seeds (default)
* d - Sort by leechers 
* f - Sort by size
* m - Load more search results (if possible)
* p - Search engines selection

#### Browse Mode Search Usage
* KEY_UP - Move to previous in search history
* KEY_DOWN - Move to next in search history
* ENTER - Search
* ESC - Exit search

#### Browse Mode Search Engine Selection Usage
* KEY_UP, KEY_DOWN - Navigate
* ENTER, SPACE - Check / Uncheck selected search engine
* ESC - Save and exit engine selection
* BUTTON_OK - Save and exit engine selection
* BUTTON_SAVE - Persist selection in config and exit engine selection

### Test Mode
Run with `-t` or `--test-search-engines` to test if all search engines are 
functioning. Consider using `--test-all` to test all search engines, not only
those set up in config.

### API Mode
Run with `-a` or `--api`. In this mode, just print the search result in JSON
format to the standard output and exit. Consider using `-m` or 
`--fetch-missing-magnet-links` in this mode.

### RPC Server
Run with `-s` or `--rpc-server` to start RPC Server, see config or `-h`for
settings details. Consider using `-m` or `--fetch-missing-magnet-links` in this
mode.

### RPC Client
Run with `-q` or `--rpc-client`, see `-h` for setting connection details.

### Iam feeling lucky mode
Directly downloads and opens torrent client with magnet link from first search
result. Run with `-d` or `--download`.

## Creating own search engine extensions
See `~/.config/torrentdl/engines.py` and 
`~/.config/torrentdl/config.json#search_engines`.
