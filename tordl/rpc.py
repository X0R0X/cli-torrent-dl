import asyncio
import json
import logging
import sys
from asyncio import Event
from pprint import pformat

import aiohttp
from aiohttp import ClientSession
from aiohttp.web import Application, json_response

from tordl.func import Api


def init_logger(log_stdout, name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        '%(asctime)s : %(levelname)s : %(message)s'
    )
    if log_stdout:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.handlers = [
            handler
        ]
    return logger


class RpcMsg(object):
    JSON_ERROR = {
        'jsonrpc': '2.0',
        'error': {
            'message': None,
            'code': None
        },
        'result': None,
        'id': 0
    }
    JSON_RESPONSE = {
        'jsonrpc': '2.0',
        'error': None,
        'result': None,
        'id': 0
    }
    ERR_INVALID_HTTP_METHOD = 1, 'Invalid HTTP method (use POST)'
    ERR_MALFORMED_JSON = 2, 'Malformed JSON: '
    ERR_INVALID_RPC_METHOD = 3, 'Invalid RPC method name: '
    ERR_GENERIC = 4, 'Error: '


class JsonRpcServer(object):
    METHOD_SEARCH = 'search'

    def __init__(
            self,
            host,
            port,
            user='',
            password='',
            log=None,
            log_stdout=False,
            api=None,
            loop=None
    ):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._log = log or init_logger(log_stdout, self.__class__.__name__)
        self._loop = loop

        self._app = Application()
        self._app.router.add_post('/', self._handle_request)
        self._app.router.add_get('', self._handle_request)

        self._api = api or Api()

    def start(self):
        aiohttp.web.run_app(
            self._app,
            host=self._host,
            port=self._port,
            reuse_address=True,
            reuse_port=True
        )

    async def _handle_request(self, request):
        if request.method == 'POST':
            try:
                request = await request.content.read()

                self._log.debug('Message received: %s' % request)
                j = json.loads(request)

                method = j['method']
                id_ = j['id']
                params = j['params']

                if method == self.METHOD_SEARCH:
                    sr = await self._api.fetch_with_magnet_links(params[0])
                    m = self._mk_msg(
                        sr,
                        id_=id_
                    )
                    return json_response(data=m)
                else:
                    self._log_err('Invalid RPC method: %s' % method)
                    return json_response(data=self._mk_msg(
                        None,
                        RpcMsg.ERR_INVALID_RPC_METHOD,
                        method,
                        id_
                    ))
            except json.decoder.JSONDecodeError as e:
                self._log_err(e)
                return json_response(data=self._mk_msg(
                    None, RpcMsg.ERR_MALFORMED_JSON, e
                ))
            except Exception as e:
                self._log_err(e)
                try:
                    return json_response(data=self._mk_msg(
                        None, RpcMsg.ERR_GENERIC, e
                    ))
                except BaseException:
                    pass

        else:
            return json_response(
                data=self._mk_msg(None, RpcMsg.ERR_INVALID_HTTP_METHOD)
            )

    def _log_err(self, e, traceback=False):
        if type(e) is BaseException:
            self._log.error(
                '%s during receiving message: %s' % (type(e), e)
            )
        else:
            self._log.error('Error during receiving message: %s' % e)
        if traceback:
            self._log.error(e.with_traceback())

    def _mk_msg(self, response=None, err_msg=None, err_add=None, id_=0):
        if response is not None:
            m = RpcMsg.JSON_RESPONSE
            m['result'] = response
        else:
            m = RpcMsg.JSON_ERROR
            m['error']['code'], m['error']['message'] = err_msg
            if err_add:
                m['error']['message'] += ' %s' % err_add
        m['id'] = id_
        return m


class JsonRpcClient(object):
    def __init__(
            self,
            host,
            port,
            user='',
            password='',
            log=None,
            log_stdout=False,
            loop=None
    ):
        self._url = 'http://%s:%d' % (host, port)
        self._user = user
        self._password = password
        self._log = log or init_logger(log_stdout, self.__class__.__name__)
        self._loop = loop or asyncio.get_event_loop()

        self._id = 0
        self._stop_event = Event()

    async def search(self, search_term):
        return await self._fetch('search', search_term)

    def stop(self):
        self._stop_event.set()

    async def _fetch(self, method, *params):
        if not self._stop_event.is_set():
            self._id += 1

            json_data = {
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': self._id
            }

            self._log.debug(
                'Calling RPC id=%d, method=%s, params=%s' %
                (
                    self._id,
                    method,
                    str(params)
                )
            )
            try:
                async with ClientSession(loop=self._loop) as session:
                    async with session.post(
                            self._url, json=json_data
                    ) as response:
                        r = response.read()
                        result = json.loads(await r)
                        if result['error'] is not None:
                            e = result['error']
                            self._log.error(
                                'RPC Error: id=%d, %s, code=%s, method=%s, '
                                'params=%s' % (
                                    self._id,
                                    e['message'],
                                    e['code'],
                                    method,
                                    str(params)
                                )
                            )
                            return e
                        else:
                            result = result['result']
                            print(result)
                            self._log.debug(
                                'RPC Response received id=%d, method=%s, '
                                'params=%s, '
                                'result=%s' % (
                                    self._id,
                                    method,
                                    str(params),
                                    pformat(result)
                                )
                            )
                            return result
            except BaseException as e:
                self._log.error('%s: %s' % (type(e), e))
