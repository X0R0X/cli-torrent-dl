import re

from bs4 import BeautifulSoup

from tordl.core import BaseDl, SearchResult


class TpbParty(BaseDl):
    NAME = 'TPB'
    BASE_URL = 'https://tpb.party'
    SEARCH_URL = '%s/search/%s/%s/99/0' % (BASE_URL, '%s', '%s')

    def _mk_search_url(self, expression):
        return self.SEARCH_URL % (expression, str(self._current_index))

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        try:
            trs = bs.find('table', id='searchResult').findAll('tr')[1:]
            for tr in trs:
                a = tr.find(class_='detName').find('a')
                name = a.text
                link = '/%s' % '/'.join(a.attrs['href'].split('/')[3:])
                tds = tr.findAll('td')
                magnet_url = tds[1].findAll('a')[1].attrs['href']
                seeders = tds[2].text
                leeches = tds[3].text
                size = tr.find(class_='detDesc').text.split(',')[1]
                size = size.replace('Size ', '').replace('i', '')
                result.append(
                    SearchResult(
                        self,
                        name,
                        link,
                        seeders,
                        leeches,
                        size,
                        magnet_url
                    )
                )
        except Exception:
            pass

        return result


class LimeTorrents(BaseDl):
    NAME = 'Lime'
    BASE_URL = 'https://www.limetorrents.lol'
    SEARCH_URL = '%s/search/all/%s/seeds/%s/' % (BASE_URL, '%s', '%s')

    def _mk_search_url(self, expression):
        return self.SEARCH_URL % (expression, str(self._current_index))

    def _mk_magnet_url(self, link):
        return '%s%s' % (self.BASE_URL, link)

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        trs = bs.findAll('tr', attrs={'bgcolor': '#F4F4F4'})
        trs.extend(bs.findAll('tr', attrs={'bgcolor': '#FFFFFF'}))
        for tr in trs:
            try:
                a = tr.find(class_='tt-name').findAll('a')[1]
                name = a.string
                link = a.attrs['href']
                size = tr.findAll(class_='tdnormal')[1].string
                seeders = tr.find(class_='tdseed').string.replace(',', '')
                leechers = tr.find(class_='tdleech').string.replace(',', '')
                result.append(
                    SearchResult(
                        self, name, link, seeders, leechers, size
                    )
                )
            except Exception:
                pass

        return result

    async def _process_magnet_link(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        try:
            return bs.findAll(class_='csprite_dltorrent')[2].attrs['href']
        except Exception:
            return None


class Dl1337xto(BaseDl):
    NAME = '1337x'
    BASE_URL = 'https://1337x.to'
    SEARCH_URL = '%s/search/%s/%s/' % (BASE_URL, '%s', '%s')

    def _mk_search_url(self, expression):
        return self.SEARCH_URL % (expression, str(self._current_index))

    def _mk_magnet_url(self, magnet_page_link):
        return '%s%s' % (self.BASE_URL, magnet_page_link)

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        try:
            trs = bs.find(
                class_='table-list table table-responsive table-striped'
            ).find('tbody').findAll('tr')
            for tr in trs:
                tds = tr.findAll('td')

                a = tds[0].findAll('a')[1]
                name = a.string
                link = a.attrs['href']

                seeders = tds[1].string
                leechers = tds[2].string
                size = '%sB' % tds[4].text.split('B')[0]

                result.append(
                    SearchResult(
                        self, name, link, seeders, leechers, size
                    )
                )
        except Exception:
            pass

        return result

    async def _process_magnet_link(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        try:
            x = bs.find(class_='box-info torrent-detail-page')
            if not x:
                x = bs.find(
                    class_=
                    'box-info torrent-detail-page series-torrent vpn-info-wrap'
                )
            x = x.findAll('div')[1].find('div').find('ul').find('li').find('a')
            return x.attrs['href']
        except Exception:
            return None


class NyaaTracker(BaseDl):
    NAME = 'Nyaa'
    BASE_URL = 'https://nyaa.si'
    SEARCH_URL = '%s/?f=0&c=0_0&q=%s&p=%s&s=seeders&o=desc' % (
        BASE_URL, '%s', '%s'
    )

    def _mk_search_url(self, expression):
        return self.SEARCH_URL % (
            expression, str(self._current_index)
        )

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        try:
            trs = bs.find('tbody').findAll('tr')
            for tr in trs:
                tds = tr.findAll('td')[1:]
                # Remove link to comments that some listings have.
                # Most concise way I have found so far.
                for a in tds[0].findAll(class_='comments'):
                    a.decompose()
                a = tds[0].find('a')
                name = a.attrs['title']
                link = a.attrs['href']
                magnet_url = tds[1].findAll('a')[1].attrs['href']
                # Site uses binary prefixes.
                # Should calculate proper sizes at some point.
                size = tds[2].text.replace('i', '')
                seeders = tds[4].text
                leechers = tds[5].text
                result.append(
                    SearchResult(
                        self,
                        name,
                        link,
                        seeders,
                        leechers,
                        size,
                        magnet_url
                    )
                )
        except Exception:
            pass

        return result


class SukebeiNyaa(NyaaTracker):
    NAME = 'Sukebei'
    BASE_URL = 'https://sukebei.nyaa.si'
    SEARCH_URL = '%s/?f=0&c=0_0&q=%s&p=%s&s=seeders&o=desc' % (
        BASE_URL, '%s', '%s'
    )


class TorrentDownload(BaseDl):
    NAME = 'TD'
    BASE_URL = 'https://www.torrentdownload.info'
    SEARCH_URL = f'{BASE_URL}/search?q=%s&p=%s'

    def _mk_search_url(self, expression):
        return self.SEARCH_URL % (expression, str(self._current_index))

    def _mk_magnet_url(self, link):
        return '%s%s' % (self.BASE_URL, link)

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        try:
            table = bs.findAll(class_='table2')[1]
            trs = table.findAll('tr')[1:]
            for tr in trs:
                a = tr.find(class_='tt-name')

                name = a.text
                link = a.find('a').attrs['href']
                seeders = tr.find(class_='tdseed').text.replace(',', '')
                leechers = tr.find(class_='tdleech').text.replace(',', '')
                size = tr.findAll(class_='tdnormal')[1].text.replace(',', '')

                result.append(
                    SearchResult(
                        self, name, link, seeders, leechers, size
                    )
                )
        except Exception:
            pass

        return result

    async def _process_magnet_link(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        try:
            return bs.findAll(class_='tosa')[2].attrs['href']
        except Exception:
            return None


class SolidTorrents(BaseDl):
    NAME = 'ST'
    BASE_URL = 'https://solidtorrents.to'
    SEARCH_URL = f'{BASE_URL}/search?q=%s&page=%s'

    def _mk_search_url(self, expression):
        return self.SEARCH_URL % (expression, str(self._current_index))

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        try:
            lis = bs.findAll(class_='card search-result my-2')[2:]

            for li in lis:
                a = li.find(class_='title w-100 truncate').find('a')
                name = a.text
                link = a.attrs['href']
                magnet_url = (
                    li.find(class_='links center-flex hide-on-small px-3')
                    .findAll('a')[1]
                    .attrs['href']
                )

                stats_divs = li.find(class_='stats').findAll('div')
                size = stats_divs[1].text
                seeders = self._parse_k_string(stats_divs[2].text)
                leechers = self._parse_k_string(stats_divs[3].text)

                result.append(
                    SearchResult(
                        self,
                        name,
                        link,
                        seeders,
                        leechers,
                        size,
                        magnet_url
                    )
                )
        except Exception:
            pass

        return result


class GloTorrents(BaseDl):
    NAME = 'Glo'
    BASE_URL = 'https://www.glodls.to'
    SEARCH_URL = (
        f'{BASE_URL}/search_results.php?search=%s&sort=seeders&order=desc&page=%s'
    )

    def _mk_search_url(self, expression):
        if self._current_index == 1:
            return self.SEARCH_URL[:-32] % expression
        else:
            return self.SEARCH_URL % (expression, str(self._current_index))

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        try:
            trs = bs.find(class_='ttable_headinner').findAll('tr')[1:]
            for tr in trs:
                c2 = tr.findAll(class_='ttable_col2')
                if len(c2) > 1:
                    c1 = tr.findAll(class_='ttable_col1')
                    a = c2[0].findAll('a')[1]
                    name = a.attrs['title']
                    link = a.attrs['href']
                    magnet_url = c2[1].find('a').attrs['href']
                    size = c1[2].text
                    seeders = c2[2].find('b').text.replace(',', '')
                    leechers = c1[3].find('b').text.replace(',', '')
                    result.append(
                        SearchResult(
                            self,
                            name,
                            link,
                            seeders,
                            leechers,
                            size,
                            magnet_url
                        )
                    )
        except Exception:
            pass

        return result


class Torrentz2(BaseDl):
    NAME = 'Torr2'
    BASE_URL = 'https://torrentz2.nz'
    SEARCH_URL = f'{BASE_URL}/search?q=%s&page=%s'

    def _mk_search_url(self, expression):
        return self.SEARCH_URL % (expression, self._current_index)

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        try:
            dls = bs.find(class_='results').findAll('dl')
            for dl in dls:
                a = dl.find('a')
                name = a.text
                link = '/'.join(a.attrs['href'].split('/')[3:])
                dd = dl.find('dd')
                spans = dd.findAll('span')[2:]
                size = spans[0].text
                seeds = self._parse_k_string(spans[1].text)
                leeches = self._parse_k_string(spans[2].text)
                magnet_url = dd.find('a').attrs['href']

                result.append(
                    SearchResult(
                        self,
                        name,
                        link,
                        seeds,
                        leeches,
                        size,
                        magnet_url
                    )
                )

        except Exception:
            pass

        return result


class YourBitTorrent(BaseDl):
    NAME = 'YBT'
    BASE_URL = 'https://yourbittorrent.com'
    SEARCH_URL = f'{BASE_URL}/?q=%s&page=%s'

    def _mk_search_url(self, expression):
        return self.SEARCH_URL % (expression, self._current_index)

    def _mk_magnet_url(self, link):
        return '%s%s' % (self.BASE_URL, link)

    def _process_search(self, response):
        bs = BeautifulSoup(response, features='html.parser')
        result = []
        try:
            trs = bs.find(
                class_='table table-bordered table-sm table-hover table-striped'
            ).find('tbody').findAll(class_='table-default')

            for tr in trs:
                tds = tr.findAll('td')[1:]
                a = tds[0].find('a')
                name = re.sub("<[^>]*>", '', a.attrs['title'])
                link = a.attrs['href']
                size = tds[1].text
                seeders = tds[3].text
                leechers = tds[4].text

                result.append(
                    SearchResult(
                        self,
                        name,
                        link,
                        seeders,
                        leechers,
                        size
                    )
                )

        except Exception:
            pass

        return result

    async def _process_magnet_link(self, response):
        """
        This fetches URL to the torrent file, with transmission and qbitorrent it works
        fine as a parameter.
        """
        bs = BeautifulSoup(response, features='html.parser')
        tor_file_url = None
        try:
            tor_file_url = bs.findAll(
                class_='col-md-4 text-center'
            )[1].find('a').attrs['href']

            return await self._fetch_torrent_file(tor_file_url)

        except Exception:
            pass

        # return torrent file url at least, for some torrent clients it's enough
        return tor_file_url
