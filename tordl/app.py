import asyncio
import curses
import logging
import os
import string
from collections import deque
from concurrent.futures._base import CancelledError
from curses import ascii
from functools import partial
from threading import Thread, Lock
from time import sleep

from tordl import config as cfg, func, core
from tordl.core import SearchResult, DlFacade, SearchProgress


class BaseScrollableWindow(object):
    def __init__(self, screen, items=None, window=None):
        self._screen = screen
        self._window = window
        self._items = items
        self._position = 0
        self._draw_start_index = 0

    @property
    def items(self):
        return self._items

    def process_key(self, key):
        h, _ = self._screen.getmaxyx()
        if key == curses.KEY_UP:
            if self._items:
                self._navigate(-1)
        elif key == curses.KEY_DOWN:
            if self._items:
                self._navigate(1)
        elif key == curses.KEY_PPAGE:
            if self._items:
                self._navigate(-(h - 2) // 2)
        elif key == curses.KEY_NPAGE:
            if self._items:
                self._navigate((h - 2) // 2)

    def _resize(self, max_items):
        if self._position > len(self._items) - max_items:
            self._draw_start_index = self._position - max_items

    def _get_max_items(self, h):
        if self._items:
            if h - 2 < len(self._items):
                max_items = min((h - 2, len(self._items)))
                if self._position >= self._draw_start_index + max_items \
                        or self._position < len(self._items) - max_items and \
                        self._draw_start_index > self._position:
                    if self._position - max_items + 1 > 0:
                        if self._position + 1 == self._draw_start_index:
                            self._draw_start_index = max((0, self._position))
                        else:
                            self._draw_start_index = max(
                                (0, self._position - max_items + 1)
                            )
                    else:
                        self._draw_start_index = max((0, self._position))
            else:
                max_items = len(self._items)
                self._draw_start_index = 0
        else:
            max_items = 0

        return max_items

    def _navigate(self, n):
        self._position += n
        if abs(n) == 1:
            if self._position < 0:
                self._position = len(self._items) - 1
            elif self._position >= len(self._items):
                self._position = 0
        else:
            if self._position < 0:
                self._position = 0
            elif self._position >= len(self._items):
                self._position = len(self._items) - 1


class TopBar(object):
    NO_CAPTION = 'No.'
    TITLE_CAPTION = 'Title'
    SEED_CAPTION = 'Seed'
    LEECH_CAPTION = 'Leech'
    SIZE_CAPTION = 'Size'
    SOURCE_CAPTION = 'Source'

    def __init__(self, screen):
        self._screen = screen

        self._window_top = screen.subwin(1, 0, 0, 1)
        self._window_top.bkgd(' ', curses.color_pair(1) | curses.A_BOLD)

    def resize(self):
        self._window_top = self._screen.subwin(1, 0, 0, 1)
        self._window_top.bkgd(' ', curses.color_pair(1) | curses.A_BOLD)
        self._window_top.clear()

    def draw(
            self,
            w,
            no_len=None,
            source_max=None,
            seeders_max=None,
            leechers_max=None,
            size_max=None
    ):
        self._window_top.addstr(0, 0, ' ' * (w - 2))
        if no_len is not None:
            self._window_top.addstr(0, 0, ' ' * (w - 2))
            self._window_top.addstr(0, 0, self.NO_CAPTION)
            x = no_len + 2
            self._window_top.addstr(0, x, self.TITLE_CAPTION)
            x = (w - (
                    seeders_max + leechers_max + size_max + source_max)) - len(
                self.NO_CAPTION
            ) - 1
            self._window_top.addstr(0, x, self.SOURCE_CAPTION)
            x += source_max + 1
            self._window_top.addstr(0, x, self.SEED_CAPTION)
            x += seeders_max + 1
            self._window_top.addstr(0, x, self.LEECH_CAPTION)
            x += leechers_max + 1
            self._window_top.addstr(0, x, self.SIZE_CAPTION)

    def finish(self):
        self._window_top.clear()

    def refresh(self):
        self._window_top.refresh()

    def clear(self):
        self._window_top.clear()


class BottomBar(object):
    SEARCH_CAPTION = 'Search: '
    SEARCH_IN_PROGRESS_CAPTION = 'Searching...'
    LOADING_MORE_RESULTS_CAPTION = 'Loading more results...'
    FETCHING_TORRENT_CAPTION = 'Fetching torrent...'
    FETCHING_MAGNET_URLS = 'Fetching magnet urls...'

    def __init__(self, screen, search_fn, start_search):
        self._screen = screen
        self._search_fn = search_fn

        self._search_term = ''
        self._search_input = False
        self._search_cur_pos = 0
        self._delta_cur_pos = 0
        self._message = None
        self._search_progress = None

        self._search_history = self._load_search_history()
        self._add_to_search_history(start_search)

        self._search_history_index = len(self._search_history)
        self._search_history_temp = ''

        h, _ = self._screen.getmaxyx()
        self._window_bottom = self._screen.subwin(
            1, 0, self._screen.getmaxyx()[0] - 1, 1
        )
        self._window_bottom.bkgd(' ', curses.color_pair(1) | curses.A_BOLD)

    @property
    def search_input(self):
        return self._search_input

    def resize(self):
        h, _ = self._screen.getmaxyx()
        self._window_bottom = self._screen.subwin(1, 0, h - 1, 1)
        self._window_bottom.bkgd(' ', curses.color_pair(1) | curses.A_BOLD)
        self._window_bottom.addstr(
            0, 0, ' ' * (self._screen.getmaxyx()[1] - 2)
        )
        self._window_bottom.clear()
        self._window_bottom.refresh()

    def finish(self):
        self._window_bottom.clear()
        self._save_search_history(self._search_history)

    def clear(self):
        self._window_bottom.clear()

    def process_key(self, key):
        if key != -1 and chr(key) in '%s%s%s ' % (
                string.ascii_letters, string.digits, string.punctuation
        ):
            i = len(self._search_term) + self._delta_cur_pos
            self._search_term = '%s%s%s' % (
                self._search_term[:i],
                chr(key),
                self._search_term[i:]
            )
            self._search_cur_pos += 1
        elif key in [curses.KEY_ENTER, ord("\n")]:
            self._add_to_search_history(self._search_term)
            self.set_search(False)
            self._search_fn(self._search_term)
        elif key in [curses.KEY_BACKSPACE, ord("\x7f")]:
            i = len(self._search_term) + self._delta_cur_pos
            if i > 0:
                self._search_term = '%s%s' % (
                    self._search_term[:i - 1],
                    self._search_term[i:]
                )
                self._search_cur_pos -= 1
        elif key == curses.KEY_DC:
            i = len(self._search_term) + self._delta_cur_pos
            if i < len(self._search_term):
                self._search_term = '%s%s' % (
                    self._search_term[:i],
                    self._search_term[i + 1:]
                )
                self._delta_cur_pos += 1
        elif key == curses.KEY_LEFT:
            if self._delta_cur_pos + len(self._search_term) > 0:
                self._delta_cur_pos -= 1
        elif key == curses.KEY_RIGHT:
            if self._delta_cur_pos + len(self._search_term) < len(
                    self._search_term
            ):
                self._delta_cur_pos += 1
        elif key == curses.ascii.ESC:
            self.set_search(False)
        elif key == curses.KEY_UP:
            if self._search_history_index > 0:
                if self._search_history_index == len(self._search_history):
                    self._search_history_temp = self._search_term
                self._search_history_index -= 1
                self._search_term = self._search_history[
                    self._search_history_index
                ]
                self._delta_cur_pos = 0
        elif key == curses.KEY_DOWN:
            if self._search_history_index < len(self._search_history) - 1:
                self._search_history_index += 1
                self._search_term = self._search_history[
                    self._search_history_index
                ]
            else:
                self._search_history_index = len(self._search_history)
                self._search_term = self._search_history_temp
            self._delta_cur_pos = 0

    def set_search(self, is_search=True):
        if is_search:
            self._search_term = ''
            self._delta_cur_pos = 0
        self._search_input = is_search

    def draw(self):
        self._window_bottom.addstr(
            0, 0, ' ' * (self._screen.getmaxyx()[1] - 2)
        )
        self._search_cur_pos = len(BottomBar.SEARCH_CAPTION) + \
                               len(self._search_term) + self._delta_cur_pos

        if self.search_input:
            self._window_bottom.addstr(
                0, 0, '%s%s' % (self.SEARCH_CAPTION, self._search_term)
            )
            self._window_bottom.move(0, self._search_cur_pos)
        self._window_bottom.refresh()

        if self._message:
            m = self._message
            if self._search_progress:
                m += ' %.1f%% [%d/%d]' % (
                    self._search_progress.percent,
                    self._search_progress.progress,
                    self._search_progress.max_
                )
            self._window_bottom.addstr(0, 0, m)

    def refresh(self):
        self._window_bottom.refresh()

    def set_search_in_progress(self):
        self._message = self.SEARCH_IN_PROGRESS_CAPTION

    def set_loading_more_progress(self):
        self._message = self.LOADING_MORE_RESULTS_CAPTION

    def set_fetching_magnet_url(self):
        self._message = self.FETCHING_TORRENT_CAPTION

    def set_fetching_magnet_urls(self):
        self._message = self.FETCHING_MAGNET_URLS

    def set_action_complete(self):
        self._message = None
        self._search_progress = None

    def set_search_progress(self, search_progress):
        self._search_progress = search_progress

    def _load_search_history(self):
        history = []
        if os.path.exists(cfg.CFG_HISTORY_FILE):
            with open(cfg.CFG_HISTORY_FILE) as f:
                for line in f.readlines():
                    history.append(line.rstrip('\n'))

        return deque(history, cfg.HISTORY_MAX_LENGTH)

    def _save_search_history(self, search_history):
        with open(cfg.CFG_HISTORY_FILE, 'w') as f:
            for r in search_history:
                f.write('%s\n' % r)

    def _add_to_search_history(self, search_term):
        if search_term and (
                not self._search_history or
                search_term != self._search_history[-1]
        ):
            self._search_history.append(search_term)

        self._search_history_index = len(self._search_history)


class EngineSelectionWindow(BaseScrollableWindow):
    WINDOW_CAPTION = 'Engine Selection'
    BUTTON_OK_CAPTION = 'OK'
    BUTTON_SAVE_CAPTION = 'SAVE'
    MIN_WIN_HEIGHT = 7

    def __init__(self, screen, downloader):
        items = downloader.all_engines.copy()
        items.append(self.BUTTON_OK_CAPTION)
        items.append(self.BUTTON_SAVE_CAPTION)

        super().__init__(screen, items)

        self._active_engines = downloader.engines

        self.active = False

    def set_active(self, active):
        self.active = active
        if active:
            if self._screen.getmaxyx()[0] > 9:
                self._position = 0
                self._mk_window()
            else:
                self.active = False
        else:
            self._window.erase()
            self._window.clear()
            self._window.refresh()
            self._window = None

    def draw(self):
        if self.active:
            win_w = self._mk_win_w()

            max_h = min(len(self.items) + 2, self._screen.getmaxyx()[0] - 4)

            max_items = self._get_max_items(max_h)

            self._window.erase()
            self._window.box()
            self._window.addstr(
                0, (win_w - len(self.WINDOW_CAPTION)) // 2,
                self.WINDOW_CAPTION
            )

            for index in range(max_items):
                if index + self._draw_start_index == self._position:
                    mode = curses.A_REVERSE
                else:
                    mode = curses.A_NORMAL

                item = self._items[self._draw_start_index + index]
                if type(item) is str:
                    if len(self.WINDOW_CAPTION) % 2 == 0:
                        sp = ' ' * ((win_w - len(item) - 3) // 2)
                        cap = '[%s%s%s]' % (sp, item, sp)
                    else:
                        sp = ' ' * ((win_w - len(item) - 4) // 2)
                        cap = '[%s %s%s]' % (sp, item, sp)
                    self._window.addstr(index + 1, 1, cap, mode)
                else:
                    s = self._mk_item_caption(item)
                    cap = '%s%s' % (s, ' ' * (win_w - 3 - len(s)))
                    self._window.addstr(index + 1, 1, cap, mode)
                    s = '[X]' if item in self._active_engines.keys() else '[ ]'
                    self._window.addstr(index + 1, win_w - 4, s, mode)

            self._window.refresh()

    def process_key(self, key):
        super().process_key(key)

        if key in (curses.ascii.ESC, ord('p')):
            self.set_active(False)
        elif key in (curses.KEY_ENTER, ord("\n"), 32):
            p = self._position
            if p == len(self._items) - 2:
                self.set_active(False)
            elif p == len(self._items) - 1:
                cfg.SEARCH_ENGINES = [e.NAME for e in self._active_engines]
                cfg.write_cfg()
                self.set_active(False)
            else:
                self._select_engine()

    def resize(self):
        if self._window:
            if self._screen.getmaxyx()[0] > self.MIN_WIN_HEIGHT:
                self._mk_window()
                self._window.refresh()
            else:
                self.set_active(False)

    def _select_engine(self):
        if len(self._active_engines) > 1 or \
                self._items[self._position] != \
                tuple(self._active_engines.keys())[0]:
            e = self._items[self._position]
            if e in self._active_engines.keys():
                del self._active_engines[e]
            else:
                self._active_engines[e] = e()

    def _mk_win_w(self):
        a = [
            len(i) if type(i) is str else len(self._mk_item_caption(i)) + 7
            for i in self._items
        ]
        a.append(len(self.WINDOW_CAPTION) + 2)
        return max(a)

    def _mk_window(self):
        h, w = self._screen.getmaxyx()
        win_h = min(len(self.items) + 2, h - 4)
        win_w = self._mk_win_w()

        self._window = self._screen.subwin(
            win_h, win_w, (h - win_h) // 2, (w - win_w) // 2
        )
        self._window.bkgd(' ', curses.color_pair(1) | curses.A_BOLD)

    def _mk_item_caption(self, item):
        return ('%s (%s)' % (
            item.BASE_URL, item.NAME
        )).split('//')[1].replace('www.', '')


class ItemWindow(BaseScrollableWindow):
    SORT_ORIGIN = 0
    SORT_SEEDERS = 1
    SORT_LEECHERS = 2
    SORT_SIZE = 3
    SORT_DESC = 0
    SORT_ASC = 1

    LOAD_MORE_CAPTION = 'Load More...'
    SEARCHING_FOR_CAPTION = 'Searching for "%s"...'
    START_SEARCH_CAPTION = 'Press \'/\' to search.'
    NOTHING_FOUND_CAPTION = ' Nothing found, press \'/\' to search. '

    class LoadMoreItem(SearchResult):
        def __init__(self):
            super().__init__(None, ItemWindow.LOAD_MORE_CAPTION, 0, 0, 0, '')

    def __init__(
            self,
            screen,
            load_more_results_fn,
            fetch_magnet_url_with_action,
            start_search_fn,
            open_torrent_link_fn,
            engine_selection_fn,
            copy_link_to_clipboard_fn,
    ):
        super().__init__(screen, None, screen.subwin(0, 0))

        self._load_more_results_fn = load_more_results_fn
        self._fetch_magnet_url_with_action = fetch_magnet_url_with_action
        self._start_search_fn = start_search_fn
        self._open_torrent_link_fn = open_torrent_link_fn
        self._engine_selection_fn = engine_selection_fn
        self._copy_link_to_clipboard_fn = copy_link_to_clipboard_fn

        self._window.keypad(1)

        self._current_sort = self.SORT_SEEDERS
        self._current_sort_type = self.SORT_DESC

        self._start_search_in_prg = False

        logging.getLogger('bs4.dammit').setLevel(logging.ERROR)

    def process_key(self, key):
        do_exit = False

        super().process_key(key)

        if key in (curses.KEY_ENTER, ord("\n")):
            if self._items:
                item = self._items[self._position]
                if type(item) is self.LoadMoreItem:
                    self._load_more_results_fn()
                else:
                    self._fetch_magnet_url_with_action(
                        item,
                        func.run_torrent_client
                    )
        if key == 32:
            self._process_current_item_with_action(self._open_torrent_link_fn)
        elif key == curses.ascii.ESC:
            do_exit = True
        elif key == ord('/'):
            self._start_search_fn()
        elif key == ord('a'):
            self._items = self._sort_items(self._items, self.SORT_ORIGIN)
        elif key == ord('s'):
            self._items = self._sort_items(self._items, self.SORT_SEEDERS)
        elif key == ord('d'):
            self._items = self._sort_items(self._items, self.SORT_LEECHERS)
        elif key == ord('f'):
            self._items = self._sort_items(self._items, self.SORT_SIZE)
        elif key == ord('m'):
            self._load_more_results_fn()
        elif key == ord('p'):
            self._engine_selection_fn()
        elif key == ord('x'):
            self._process_current_item_with_action(
                self._fetch_magnet_url_with_action,
                self._copy_link_to_clipboard_fn
            )

        return do_exit

    def set_items(self, search_results, append=False):
        if append:
            lm = self._items.pop()
            self._items.extend(
                self._sort_items(search_results, self.SORT_SEEDERS, True)
            )
            self._items.append(lm)
        else:
            self._position = 0
            self._items = self._sort_items(
                search_results, self.SORT_SEEDERS, True
            )
            if self._items:
                self._items.append(self.LoadMoreItem())

    def draw(self,
             h,
             w,
             no_len,
             title_length,
             source_max,
             seeders_max,
             leechers_max,
             size_max,
             start_search
             ):
        max_items = super()._get_max_items(h)

        if self._items is None:
            if start_search:
                m = self.SEARCHING_FOR_CAPTION % start_search
            else:
                if not self._start_search_in_prg:
                    m = self.START_SEARCH_CAPTION
                else:
                    m = ''
            self._window.addstr(h // 2, w // 2 - len(m) // 2, m)
        elif not self._items:
            self._window.clear()
            m = self.NOTHING_FOUND_CAPTION
            self._window.addstr(h // 2, w // 2 - len(m) // 2, m)
        else:
            for index in range(max_items):
                item = self._items[index + self._draw_start_index]
                if index + self._draw_start_index == self._position:
                    mode = curses.A_REVERSE
                else:
                    mode = curses.A_NORMAL

                if type(item) is self.LoadMoreItem:
                    msg = '%s' % item.name
                    color = curses.color_pair(2)
                else:
                    color = curses.color_pair(3)
                    msg = "%s. %s|%s|%s|%s|%s" % (
                        str(index + self._draw_start_index + 1).zfill(
                            no_len
                        ),
                        self._format_field(item.name, title_length, True),
                        self._format_field(
                            ','.join([i.NAME for i in item.origins]),
                            source_max
                        ),
                        self._format_field(str(item.seeders), seeders_max),
                        self._format_field(str(item.leechers), leechers_max),
                        self._format_field(item.size, size_max)
                    )
                msg = msg + ' ' * (w - len(msg) - 1)
                self._window.addstr(1 + index, 1, msg, mode | color)

            if max_items < h - 2:
                for i in range(1, (h - 2) - max_items + 1):
                    self._window.addstr(max_items + i, 1, ' ' * (w - 1))

    def resize(self):
        self._window = self._screen.subwin(0, 0)
        self._window.keypad(1)
        self._window.clear()

        if self._items:
            h, _ = self._screen.getmaxyx()
            max_items = min((h - 2, len(self._items)))
            super()._resize(max_items)

    def refresh(self):
        self._window.refresh()

    def finish(self):
        self._window.clear()

    def set_search_start(self, new_search=True):
        self._start_search_in_prg = True
        if new_search:
            self._items = None

    def set_search_end(self):
        self._start_search_in_prg = False

    def clear(self):
        self._window.clear()

    def _sort_items(self, items, sort_type, ignore_reverse=False):
        if items and len(items) > 0:
            if type(items[-1]) is self.LoadMoreItem:
                lmi = items.pop()
            else:
                lmi = None

            if sort_type == self.SORT_SEEDERS:
                items = sorted(
                    items,
                    key=lambda it: it.seeders,
                    reverse=self._sort_reverse(self.SORT_SEEDERS)
                            or ignore_reverse
                )
            elif sort_type == self.SORT_LEECHERS:
                items = sorted(
                    items,
                    key=lambda it: it.leechers,
                    reverse=self._sort_reverse(self.SORT_LEECHERS)
                            or ignore_reverse
                )
            elif sort_type == self.SORT_SIZE:
                items = sorted(
                    items,
                    key=lambda it: it.size_b,
                    reverse=self._sort_reverse(self.SORT_SIZE)
                            or ignore_reverse
                )
            elif sort_type == self.SORT_ORIGIN:
                items = sorted(
                    items,
                    key=lambda it: it.origins[0].NAME,
                    reverse=not self._sort_reverse(self.SORT_ORIGIN)
                            or ignore_reverse
                )

            if lmi:
                items.append(lmi)

            if ignore_reverse:
                self._current_sort_type = self.SORT_DESC

        return items

    def _process_current_item_with_action(self, fn, *args, **kwargs):
        if self._items:
            item = self._items[self._position]
            if type(item) is not self.LoadMoreItem:
                fn(item, *args, **kwargs)

    def _sort_reverse(self, sort_type):
        if self._current_sort == sort_type:
            if self._current_sort_type == self.SORT_DESC:
                self._current_sort_type = self.SORT_ASC
                return False
            else:
                self._current_sort_type = self.SORT_DESC
                return True
        else:
            self._current_sort_type = self.SORT_DESC
            self._current_sort = sort_type
            return True

    def _format_field(self, s, max_, dots=False):
        if not s:
            s = 'None'

        ln = len(s)
        if dots:
            if ln > max_ - 3:
                s = '%s...' % s[:max_ - 3]
            elif ln < max_ + 3:
                s = s + ' ' * (max_ - ln)
        else:
            if ln < max_:
                s = (' ' * (max_ - ln)) + s

        return s


class App(object):
    def __init__(self, screen, search=''):
        self._screen = screen
        self._start_search_str = search

        self._init_search_in_prg = False

        self._loop, self._loop_thread = self._mk_event_loop()
        self._pending_tasks = []
        self._lock = Lock()

        self._downloader = DlFacade(self._loop)

        self._should_exit = False

        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)

        self._top_bar = TopBar(self._screen)
        self._bottom_bar = BottomBar(
            self._screen, self._do_search, self._start_search_str
        )
        self._item_window = ItemWindow(
            screen,
            self._load_more_results,
            self._fetch_magnet_url_with_action,
            self._bottom_bar.set_search,
            self._open_torrent_link,
            self._create_selection_win,
            self._copy_url_to_clipboard
        )
        self._engine_selection_win = EngineSelectionWindow(
            self._screen, self._downloader
        )

        self._display()

    def _mk_event_loop(self):
        core.mk_loop()
        loop = asyncio.new_event_loop()
        t = Thread(target=loop.run_forever)
        t.start()
        return loop, t

    def _display(self):
        while not self._should_exit:
            try:
                self._lock.acquire()

                self._draw()

                if self._start_search_str:
                    if not self._init_search_in_prg:
                        self._fetch_results(self._start_search_str)
                        self._bottom_bar.set_search_in_progress()
                        self._item_window.clear()
                        self._init_search_in_prg = True
                    key = -1
                else:
                    if len(self._pending_tasks) == 0:
                        key = self._screen.getch()
                    else:
                        key = -1
                self._lock.release()

                if key == -1:
                    sleep(0.2)

                if self._bottom_bar.search_input:
                    self._bottom_bar.process_key(key)
                elif self._engine_selection_win.active:
                    self._engine_selection_win.process_key(key)
                    if not self._engine_selection_win.active:
                        self._item_window.clear()
                else:
                    self._should_exit = self._item_window.process_key(key)

                if key == curses.KEY_RESIZE:
                    self._process_screen_resize()

            except KeyboardInterrupt:
                self._should_exit = True
        self._top_bar.finish()
        self._bottom_bar.finish()
        self._item_window.finish()

        curses.doupdate()

        if asyncio.all_tasks(self._loop):
            for p in self._pending_tasks:
                self._loop.call_soon_threadsafe(p.cancel)

        while asyncio.all_tasks(self._loop):
            sleep(0.1)

        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop_thread.join()

    def _draw(self):
        h, w = self._screen.getmaxyx()

        a = [len(str(i.seeders)) for i in self._item_window.items] \
            if self._item_window.items else []
        a.append(len(TopBar.SEED_CAPTION))
        seeders_max = max(a)

        a = [len(str(i.leechers)) for i in self._item_window.items] \
            if self._item_window.items else []
        a.append(len(TopBar.LEECH_CAPTION))
        leechers_max = max(a)

        a = [len(i.size) for i in self._item_window.items] \
            if self._item_window.items else []
        a.append(len(TopBar.SIZE_CAPTION))
        size_max = max(a)

        a0 = []
        if self._item_window.items:
            for item in self._item_window.items:
                if type(item) is not ItemWindow.LoadMoreItem:
                    a0.append(len(','.join([i.NAME for i in item.origins])))
        a0.append(len(TopBar.SOURCE_CAPTION))
        source_max = max(a0)

        no_len = len(str(len(self._item_window.items))) \
            if self._item_window.items else 0

        title_length = w - (
                seeders_max + leechers_max + size_max + no_len + source_max +
                len(TopBar.TITLE_CAPTION) + 2
        )
        if title_length < 0:
            title_length = 0

        try:
            self._item_window.draw(
                h,
                w,
                no_len,
                title_length,
                source_max,
                seeders_max,
                leechers_max,
                size_max,
                self._start_search_str
            )

            if self._item_window.items:
                self._top_bar.draw(
                    w, no_len, source_max, seeders_max, leechers_max, size_max
                )
            else:
                self._top_bar.draw(w)

            self._bottom_bar.draw()

            self._engine_selection_win.draw()
        except Exception:
            # Resize to bigger window during fetching - window.addstr() WTF ?
            pass

        self._top_bar.refresh()
        self._item_window.refresh()
        self._bottom_bar.refresh()

        curses.doupdate()

    def _do_search(self, search_term):
        self._item_window.clear()
        self._top_bar.clear()
        self._bottom_bar.set_search_in_progress()
        self._item_window.refresh()

        self._fetch_results(search_term)

    def _process_screen_resize(self):
        self._lock.acquire()
        self._top_bar.resize()
        self._bottom_bar.resize()
        self._engine_selection_win.resize()
        self._item_window.resize()
        self._lock.release()

    def _create_selection_win(self):
        self._engine_selection_win.set_active(True)

    def _load_more_results(self):
        self._bottom_bar.set_loading_more_progress()
        self._fetch_results(None)

    def _fetch_results(self, search_term):
        self._item_window.set_search_start(
            search_term is not None
        )
        search_progress = SearchProgress()
        self._bottom_bar.set_search_progress(search_progress)
        future = asyncio.run_coroutine_threadsafe(
            self._downloader.fetch_pages(
                search_term,
                search_progress
            ),
            self._loop
        )
        future.add_done_callback(
            partial(self._on_fetch_pages, search_term=search_term)
        )
        self._pending_tasks.append(future)

    def _on_fetch_pages(self, future, search_term):
        if cfg.FETCH_MISSING_MAGNET_LINKS:
            self._lock.acquire()
            self._pending_tasks.remove(future)

            search_progress = SearchProgress()
            self._bottom_bar.set_fetching_magnet_urls()
            self._bottom_bar.set_search_progress(search_progress)

            future = asyncio.run_coroutine_threadsafe(
                self._downloader.fetch_magnet_links(
                    future.result(),
                    cfg.FETCH_MAGNET_LINKS_CONCURRENCE,
                    search_progress
                ),
                self._loop
            )
            future.add_done_callback(
                partial(self._on_fetch_magnet_urls, search_term=search_term)
            )
            self._pending_tasks.append(future)
            self._lock.release()
        else:
            self._on_fetch_magnet_urls(future, search_term)

    def _on_fetch_magnet_urls(self, future, search_term):
        self._lock.acquire()
        if future in self._pending_tasks:
            self._pending_tasks.remove(future)
        try:
            items = future.result()
        except CancelledError:
            items = []

        if cfg.AGGREGATE_SAME_MAGNET_LINKS:
            if search_term is not None:
                items = self._downloader.aggregate_same_magnets(items)
            else:
                items = self._downloader.aggregate_same_magnets(
                    self._item_window.items, items
                )

        self._item_window.set_items(items, search_term is None)
        self._bottom_bar.set_action_complete()
        if self._start_search_str:
            self._init_search_in_prg = False
            self._start_search_str = None
        self._item_window.set_search_end()
        self._lock.release()

    def _fetch_magnet_url_with_action(self, item, action_fn=None):
        self._lock.acquire()

        if item.magnet_url:
            action_fn(item.magnet_url)
        else:
            self._bottom_bar.set_fetching_magnet_url()
            future = asyncio.run_coroutine_threadsafe(
                self._downloader.get_magnet_url(item),
                self._loop
            )
            future.add_done_callback(
                partial(self._on_magnet_url_fetched, action_fn=action_fn)
            )
            self._pending_tasks.append(future)

        self._lock.release()

    def _on_magnet_url_fetched(self, future, action_fn):
        self._lock.acquire()
        self._pending_tasks.remove(future)
        self._bottom_bar.set_action_complete()
        try:
            ml = future.result()
        except CancelledError:
            ml = None

        if ml:
            action_fn(ml)
        else:
            # TODO magnurl error
            pass
        self._bottom_bar.set_action_complete()
        self._lock.release()

    def _open_torrent_link(self, item):
        func.open_torrent_link(
            '%s%s' % (item.origins[0].BASE_URL, item.links[0])
        )

    def _copy_url_to_clipboard(self, magnet_url):
        func.copy_url_to_clipboard(magnet_url)
