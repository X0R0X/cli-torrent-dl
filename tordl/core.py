import asyncio
import importlib
import inspect
import subprocess
from importlib import machinery, util

from aiohttp import ClientSession

import tordl.config as cfg


def run_torrent_client(magnet_url):
    cmd = (cfg.TORRENT_CLIENT_CMD % magnet_url).split(' ')
    subprocess.Popen(
        cmd,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )


def open_torrent_link(link):
    cmd = (cfg.BROWSER_CMD % link).split(' ')
    subprocess.Popen(
        cmd,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )


class SearchResult(object):
    def __init__(
            self, origin, name, link, seeders, leechers, size, magnet_url=None
    ):
        self.origin = origin
        self.name = name
        self.link = link
        self.seeders = seeders
        self.leechers = leechers
        self.size = size.replace(' ', '')
        self.magnet_url = magnet_url

        self.size_b = self.size.lower()
        if 'kb' in self.size_b:
            self.size_b = float(self.size_b.replace('kb', '')) * 1024
        elif 'mb' in self.size_b:
            self.size_b = float(self.size_b.replace('mb', '')) * (1024 ** 2)
        elif 'gb' in self.size_b:
            self.size_b = float(self.size_b.replace('gb', '')) * (1024 ** 3)
        elif 'tb' in self.size_b:
            self.size_b = float(self.size_b.replace('tb', '')) * (1024 ** 4)
        elif 'b' in self.size_b:
            self.size_b = float(self.size_b.replace('b', ''))
        else:
            try:
                self.size_b = float(self.size_b)
            except Exception:
                pass
            else:
                self.size_b = 0.0


class BaseDl(object):
    NAME = ''
    BASE_URL = None
    SEARCH_URL = None
    INDEXED = True

    def __init__(self):
        self._current_index = 1
        self._current_search = None
        self._headers = self._create_headers()

    async def search(self, expression, new_search=False):
        if expression is None and not new_search:
            if not self.INDEXED:
                return []

            self._current_index += 1
        else:
            self._current_index = 1

        if expression:
            self._current_search = expression

        self._set_referer('%s/' % self.BASE_URL)
        response = await self._get_url(
            self._mk_search_url(self._current_search)
        )

        return self._process_search(response)

    async def get_magnet_url(self, search_result):
        self._set_referer(self._mk_search_url(self._current_search))
        response = await self._get_url(self._mk_magnet_url(search_result.link))
        return self._process_magnet_link(response)

    async def _get_url(self, url):
        async with ClientSession(headers=self._headers) as sess:
            async with sess.get(url) as response:
                return await response.read()

    def _mk_search_url(self, expression):
        raise NotImplementedError()

    def _mk_magnet_url(self, link):
        raise NotImplementedError()

    def _process_search(self, response):
        raise NotImplementedError()

    def _process_magnet_link(self, response):
        raise NotImplementedError()

    def _create_headers(self):
        return {
            'Accept': 'text/html,application/xhtml+xml,'
                      'application/xml;q=0.9,image/webp,'
                      '*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': self.BASE_URL.split('://')[1],
            'Origin': self.BASE_URL,
            'Set-GPC': '1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64;'
                          ' x64) AppleWebKit/537.36 (KHTML, '
                          'like Gecko) Chrome/90.0.4430.72 '
                          'Safari/537.36'
        }

    def _set_referer(self, url):
        self._headers['Referer'] = url


class DlFacade(object):
    def __init__(
            self,
            dl_classes=None,
    ):
        self._engines = self._load_engines() \
            if not dl_classes else {c: c() for c in dl_classes}

    @property
    def engines(self):
        return self._engines

    async def search(self, expression, new_search=False):
        tasks = []
        for dl in self._engines.values():
            tasks.append(dl.search(expression, new_search))

        results, _ = await asyncio.wait(tasks)
        result = []
        for r in results:
            result.extend(r.result())

        return result

    async def get_magnet_url(self, search_result):
        e = self._engines[search_result.origin]
        return await e.get_magnet_url(search_result)

    def _load_engines(self):
        loader = importlib.machinery.SourceFileLoader(
            'engines_mod', cfg.CFG_ENGINES_FILE
        )
        spec = importlib.util.spec_from_loader('engines_mod', loader)
        engines_mod = importlib.util.module_from_spec(spec)
        loader.exec_module(engines_mod)

        classes = []
        for name, obj in inspect.getmembers(engines_mod):
            if inspect.isclass(obj):
                mro = obj.mro()
                if len(mro) > 2 and BaseDl in mro:
                    classes.append(obj)

        engines = {}
        for c in classes:
            if c.NAME in cfg.SEARCH_ENGINES:
                engines[c] = c()

        if not engines:
            raise RuntimeError("No search engines selected.")

        return engines
