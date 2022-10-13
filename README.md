tordl
=====

<img src="./img/tordl.gif" width="732">

About
-----

tordl provides convenient and quick way to search torrent magnet links (and run
preferred torrent client) via major torrent sites (ThePirateBay, LimeTorrents,
Zooqle, 1337x, GloTorrents, KickAssTorrents, SolidTorrents, BTDB, TGx, Nyaa by
default) through command line.

Table of Contents
-----------------

* [Installation](#installation)
  * [Prerequisites](#prerequisites)
  * [Setup](#setup)
* [Config](#config)
* [Docker](#docker)
  * [Build](#build)
  * [Run JSON RPC Server](#run-json-rpc-server)
* [Usage](#usage)
  * [CLI](#cli)
  * [Modes](#modes)
    * [API Mode](#api-mode)
    * [Browse Mode](#browse-mode)
      * [Search](#search)
      * [Search Engine Selection](#search-engine-selection)
    * [I'm Feeling Lucky Mode](#im-feeling-lucky-mode)
    * [Test Mode](#test-mode)
  * [RPC](#rpc)
    * [RPC Server](#rpc-server)
    * [RPC Client](#rpc-client)
* [JSON Output Format](#json-output-format)
* [Creating Custom Search Engines](#creating-custom-search-engines)

Installation
------------

### Prerequisites

* Python 3.8+

### Setup

    $ ./setup.sh

Config
------

Edit `~/.config/torrentdl/config.json` to customize your preferred torrent 
client (default is qbittorent).

Docker
------

Opening magnet links in your preferred torrent client will not work, of course.

### Build

    $ docker build . -t tordl

### Run JSON RPC Server

    $ docker run -p 57000:57000 -it tordl -s

Usage
-----

### CLI

Run search from command line:

    $ tordl debian 8

Exclude search results containing user defined strings:

    $ tordl debian ::-8 ::-7 (...)

Show help:

    $ tordl -h

### Modes

#### API Mode

Run with `-a` or `--api`. In this mode, just print the search result in JSON
format to the standard output and exit. Consider using `-m` or 
`--fetch-missing-magnet-links` in this mode.

#### Browse Mode

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
* x - Copy magnet link to system clipboard

##### Search

* KEY_DOWN - Move to next in search history
* KEY_UP - Move to previous in search history
* ENTER - Search
* ESC - Exit search

##### Search Engine Selection

* KEY_UP, KEY_DOWN - Navigate
* ENTER, SPACE - Check / Uncheck selected search engine
* ESC - Save and exit engine selection
* BUTTON_OK - Save and exit engine selection
* BUTTON_SAVE - Persist selection in config and exit engine selection

#### I'm Feeling Lucky Mode

Directly downloads and opens torrent client with magnet link from first search
result. Run with `-d` or `--download`.

#### Test Mode

Run with `-t` or `--test-search-engines` to test if all search engines are 
functioning. Consider using `--test-all` to test all search engines, not only
those set up in config.

### RPC

#### RPC Server

Run with `-s` or `--rpc-server` to start RPC Server, see config or `-h`for
settings details. Consider using `-m` or `--fetch-missing-magnet-links` in this
mode. JSON RPC Server follow jsonrpc 2.0 standard. Currently, there is only
one RPC method `search` which expects array of one argument - the search term.

#### RPC Client

Run with `-q` or `--rpc-client`, see `-h` for setting connection details.

JSON Output Format
------------------

```
{
    "result": [
        {
            "name": "Debian 8 7 1 Jessie x64 x86 64 DVD1 ISO Uzerus",
            "links": [
                "https://kickasss.to/debian-8-7-1-jessie-x64-x86_64-dvd1-iso-uzerus-t2086014.html"
            ],
            "magnet_url": "magnet:?xt=urn:btih:40F90995A1C16A1BF454D09907F57700F3E8BD64...",
            "origins": [
                "KAT"
            ],
            "seeds": 2,
            "leeches": 0,
            "size": "3.7GB"
        },
        ...,
        ...,
        ...
}
```

Creating Custom Search Engines
-------------------------------------

See `~/.config/torrentdl/engines.py` and 
`~/.config/torrentdl/config.json#search_engines`.
