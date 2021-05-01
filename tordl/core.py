import asyncio
import importlib
import inspect
import json
import subprocess
import time
from asyncio import Task, Event
from importlib import machinery, util

from aiohttp import ClientSession, ClientTimeout

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


def direct_download(st, loop=None):
    if not st:
        print('No search term defined, cannot use --download option.')
        exit(1)

    if not loop:
        loop = asyncio.get_event_loop()

    dl = DlFacade()
    print('Searching %s for "%s"...' % (','.join(cfg.SEARCH_ENGINES), st))
    results = loop.run_until_complete(dl.search(st))
    if results:
        results = sorted(results, key=lambda r: r.seeders, reverse=True)
        result = results[0]
        print('Found "%s", seeds: %s, size: %s,  ' % (
            result.name, result.seeders, result.size
        ))
        if result.magnet_url:
            magnet_url = result.magnet_url
        else:
            print('Fetching magnet link...')
            magnet_url = loop.run_until_complete(dl.get_magnet_url(result))

        print('Running torrent client...')
        run_torrent_client(magnet_url)
    else:
        print('No results found.')


def test_search_engines(loop=None):
    if not loop:
        loop = asyncio.get_event_loop()

    st = 'Star Wars'
    dl = DlFacade()
    es = dl.engines.values()
    test_results = []
    for e in es:
        cls = e.__class__
        print(
            'Testing %s [%s]...' % (
                '%s.%s' % (cls.__module__, cls.__qualname__), e.NAME
            )
        )
        error = False
        t = time.time()
        results = loop.run_until_complete(e.search(st))
        t = time.time() - t
        if len(results) > 0:
            print('  - Search results (%d) fetched.' % len(results))
            r = results[0]
            if not r.name:
                error = True
                print('  - ERROR: Name not found !')
            if not r.link and not r.magnet_url:
                error = True
                print('  - ERROR: Link not found !')
            if not r.seeders:
                error = True
                print('  - ERROR: Seeders not found !')
            if not r.leechers:
                error = True
                print('  - ERROR: Leechers not found !')
            if not r.size:
                error = True
                print('  - ERROR: Size not found !')
            if not r.link:
                error = True
                print('  - ERROR: Link not found !')
            if not r.magnet_url:
                magnet_url = loop.run_until_complete(e.get_magnet_url(r))
                if magnet_url:
                    print('  - Magnet URL fetched.')
                else:
                    error = True
                    print('  - ERROR: MagnetURL not found !')
        else:
            error = True
            print('  - ERROR, no results found !')
        if not error:
            test_results.append('[OK] %s [search_time=%.3fs]' % (e.NAME, t))
        else:
            test_results.append('[ERR] %s [search_time=%.3fs]' % (e.NAME, t))

    print('-' * 20)
    for m in test_results:
        print(m)
    print('-' * 20)


def run_api(st, pretty_json=True, loop=None):
    if not st:
        print('No search term defined, cannot use --api option.')
        exit(1)

    if not loop:
        loop = asyncio.get_event_loop()

    api = Api()
    sr = loop.run_until_complete(api.fetch(st))
    print(api.mk_json_output(sr, pretty_json))


class SearchResult(object):
    def __init__(
            self, origin, name, link, seeders, leechers, size, magnet_url=None
    ):
        self.origin = origin
        self.name = name.encode('ascii', 'ignore').decode()
        self.link = link
        self.seeders = seeders
        self.leechers = leechers
        self.size = size.replace(' ', '').encode('ascii', 'ignore').decode()
        self.magnet_url = magnet_url

        sb = self.size.lower()
        if 'kb' in sb:
            self.size_b = float(sb.replace('kb', '')) * 1024
        elif 'mb' in sb:
            self.size_b = float(sb.replace('mb', '')) * (1024 ** 2)
        elif 'gb' in sb:
            self.size_b = float(sb.replace('gb', '')) * (1024 ** 3)
        elif 'tb' in sb:
            self.size_b = float(sb.replace('tb', '')) * (1024 ** 4)
        elif 'b' in sb:
            self.size_b = float(sb.replace('b', ''))
        else:
            try:
                self.size_b = float(sb)
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

        return self._process_search(response) if response else None

    async def get_magnet_url(self, search_result):
        self._set_referer(self._mk_search_url(self._current_search))
        response = await self._get_url(self._mk_magnet_url(search_result.link))
        return self._process_magnet_link(response) if response else None

    async def _get_url(self, url):
        try:
            async with ClientSession(
                    headers=self._headers,
                    timeout=ClientTimeout(cfg.REQUEST_TIMEOUT)
            ) as sess:
                async with sess.get(url) as response:
                    return await response.read()
        except asyncio.exceptions.TimeoutError:
            return None

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
        if dl_classes:
            self._engines = {c: c() for c in dl_classes}
            self._all_engines = self._load_engines()[1]
        else:
            self._engines, self._all_engines = self._load_engines()

    @property
    def engines(self):
        return self._engines

    @property
    def all_engines(self):
        return self._all_engines

    async def search(self, expression, new_search=False):
        tasks = []
        for dl in self._engines.values():
            tasks.append(dl.search(expression, new_search))

        results, _ = await asyncio.wait(tasks)
        result = []
        for r in results:
            r = r.result()
            if r:
                result.extend(r)

        return result

    async def fetch_pages(self, search_term):
        coros = []
        for i in range(cfg.PAGE_NUM_DOWNLOAD):
            coros.append(
                self.search(search_term if i == 0 else None)
            )
        done, _ = await asyncio.wait(coros)
        items = []
        for t in done:
            result = t.result()
            if result:
                items.extend(result)

        return items

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

        all_engines = []
        for name, obj in inspect.getmembers(engines_mod):
            if inspect.isclass(obj):
                mro = obj.mro()
                if len(mro) > 2 and BaseDl in mro:
                    all_engines.append(obj)

        engines = {}
        for c in all_engines:
            if c.NAME in cfg.SEARCH_ENGINES:
                engines[c] = c()

        if not engines:
            raise RuntimeError("No search engines selected.")

        return engines, all_engines


class Api(object):
    class GetMagnetUrlTask(Task):
        def __init__(self, coro, search_result, max_):
            super().__init__(coro)
            self.max_ = max_
            self.search_result = search_result

    def __init__(self, dl_classes=None, concurrent=20):
        self._dl = DlFacade(dl_classes)
        self._concurrent = concurrent

        self._counter = 0
        self._batch_done = Event()

    async def fetch(self, search_term):
        search_results = await self._dl.fetch_pages(search_term)

        await self._fetch_magnet_links(search_results)
        return search_results

    def mk_json_output(self, search_results, pretty=False):
        result = []
        j = {'result': result}
        for sr in search_results:
            o = {
                'name': sr.name,
                'link': '%s%s' % (sr.origin.BASE_URL, sr.link),
                'magnet_url': sr.magnet_url,
                'origin': sr.origin.NAME,
                'seeds': sr.seeders,
                'leeches': sr.leechers,
                'size': sr.size
            }
            result.append(o)

        return json.dumps(j, indent=4 if pretty else None)

    async def _fetch_magnet_links(self, search_results):
        no_ml = []
        for sr in search_results:
            if not sr.magnet_url:
                no_ml.append(sr)

        ln = len(no_ml)
        for i in range(0, ln, self._concurrent):
            max_ = min(i + self._concurrent, ln)
            self._counter = 0
            self._batch_done.clear()
            for j in range(i, max_):
                sr = no_ml[j]
                task = self.GetMagnetUrlTask(
                    self._dl.get_magnet_url(sr), sr, max_ - i
                )
                task.add_done_callback(self._on_fetch_magnet_done)

            await self._batch_done.wait()

    def _on_fetch_magnet_done(self, task):
        self._counter += 1
        task.search_result.magnet_url = task.result()
        if self._counter >= task.max_:
            self._batch_done.set()
