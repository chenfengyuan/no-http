#!/usr/bin/env python
import re
from signal import signal, SIGINT
import asyncio
import uvloop
asyncio.set_event_loop(uvloop.new_event_loop())

HTTP_RE = re.compile(rb'(?:User-Agent)|(?: HTTP/1.\d)')


class EchoClientProtocol(asyncio.Protocol):
    def __init__(self, pair):
        self.transport = None
        self.buffer = []
        self.closed = False
        self.pair = pair

    def connection_made(self, transport):
        self.transport = transport
        peername = transport.get_extra_info('peername')
        sockname = transport.get_extra_info('sockname')
        print('pipe: {} <--> {} <-> {}'.format(self.pair.peername, sockname, peername))
        if self.buffer:
            for msg in self.buffer:
                transport.write(msg)
            self.buffer = []

    def data_received(self, data):
        self.pair.send_data(data)

    def connection_lost(self, exc):
        if exc:
            print('client: connection exc:'.format(exc))
        if self.closed:
            print('client: connection close(closed)')
            return
        print('client: The server closed the connection')
        self.pair.pair_close()

    def pair_close(self):
        if self.closed:
            print('client: pair close(closed)')
            return
        print('client: pair close(not closed)')
        self.closed = True
        self.transport.close()

    def send_data(self, data):
        if not self.transport:
            self.buffer.append(data)
        else:
            self.transport.write(data)


class EchoServerClientProtocol(asyncio.Protocol):
    def __init__(self, server_port):
        self.pair = None
        self.pair_coro = None
        self.pair_task = None
        self.closed = False
        self.peername = ''
        self.server_port = server_port

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.peername = peername
        self.transport = transport
        loop = asyncio.get_event_loop()
        self.pair = EchoClientProtocol(self)
        self.pair_coro = loop.create_connection(lambda: self.pair, '127.0.0.1', self.server_port)
        self.pair_task = asyncio.ensure_future(self.pair_coro)
        self.pair_task.add_done_callback(self.pair_done_cb)

    def pair_done_cb(self, future):
        if future.exception():
            print('server pair exc done: {}'.format(future.exception()))
            self.pair_close()

    def data_received(self, data):
        if HTTP_RE.search(data):
            print('server: detect http request :{}'.format(data.decode('iso8859-1')))
            self.transport.close()
            return
        self.pair.send_data(data)

    def send_data(self, data):
        self.transport.write(data)

    def connection_lost(self, exc):
        if self.closed:
            print('server: connection close(closed)')
            return
        print('server: The client.closed the connection')
        self.pair.pair_close()

    def pair_close(self):
        if self.closed:
            print('server: pair close(closed)')
            return
        print('server: pair close(not closed)')
        self.closed = True
        self.transport.close()


def main():
    import sys
    argv = sys.argv
    loop = asyncio.get_event_loop()
    coro = loop.create_server(lambda: EchoServerClientProtocol(int(argv[2])), '127.0.0.1', int(argv[1]))
    signal(SIGINT, lambda s, f: loop.stop())
    asyncio.ensure_future(coro)
    try:
        loop.run_forever()
    except:
        loop.stop()


if __name__ == '__main__':
    main()
