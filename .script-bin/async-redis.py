#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from __future__ import print_function
from pprint import pprint

import asyncio
import concurrent.futures as concur
import contextvars
import logging
import multidict
import os
import re
import signal
import subprocess
import time

from clu.constants.consts import DEBUG, NoDefault
from clu.predicates import resolve, uniquify
from clu.fs.filesystem import (which,
                               TemporaryName,
                               TemporaryDirectory,
                                        Directory,
                                        Intermediate)

'''
RUNNING REDIS:

1. Relevant command lines:
    
    * Detect:
    • ps ax | grep redis-server | grep -v grep
    
    * Kill:
    • kill -9 `ps ax | grep redis-server | grep -v grep | cut -d " " -f 1,1`
    
2. Configuration:
    
    
'''

logging.basicConfig(level=logging.DEBUG,
                    format='%(relativeCreated)6d %(threadName)s %(message)s')

PID = contextvars.ContextVar('PID')

class RedisConf(object):
    
    """ Process Redis configuration-file options, and generate
        temporary configuration files, per use of instance methods
    """
    
    DEFAULT_SOURCE = '/usr/local/etc/redis.conf'
    COMMENT_RE = re.compile("#+(?:[\s\S]*)$")
    
    @staticmethod
    def compose(iterable):
        return ' '.join(iterable)
    
    @staticmethod
    def decompose(value):
        return tuple(value.split())
    
    @classmethod
    def decommentizer(cls):
        return lambda line: cls.COMMENT_RE.sub('', line).rstrip()
    
    def __init__(self, source=None,
                       directory=None,
                       port=6379, *,
                       follow_includes=True):
        """ Initialize a RedisConf instance – optionally with a given
            path to a configuration file and/or a specified port number
        """
        self.config = multidict.MultiDict()
        self.source = source or type(self).DEFAULT_SOURCE
        self.directory = directory
        self.port = port
        self.active = False
        self.process(self.source, follow_includes=follow_includes)
    
    def process(self, source, *, follow_includes=True):
        self.parse(source)
        if follow_includes:
            for include in self.get_includes():
                self.process(include)
    
    def parse(self, source):
        with open(source, 'r') as handle:
            lines = map(self.decommentizer(),
                    filter(None,
                    filter(lambda line: not line.startswith('#'),
                    map(lambda line: line.strip(),
                        handle.readlines()))))
        for line in lines:
            key, value = line.split(None, 1)
            self.add(key, value)
    
    def add(self, key, value):
        self.config.add(key, self.decompose(value))
    
    def set(self, key, value):
        self.config[key] = self.decompose(value)
    
    def get(self, key, default=NoDefault):
        if key in self.config:
            return self.compose(self.config.get(key))
        if default is NoDefault:
            raise KeyError(key)
        return default
    
    def set_boolean(self, key, value):
        self.set(value and 'yes' or 'no')
    
    def get_boolean(self, key):
        return self.get(key).lower().strip() == 'yes'
    
    def set_port(self, port):
        rdir = self.get_dir()
        self.set('port',    str(port))
        self.set('pidfile', rdir.subpath(f"redis_{port}.pid"))
    
    def get_port(self):
        return int(self.get('port'), base=10)
    
    def set_dir(self, directory):
        self.set('dir', os.fspath(directory))
    
    def get_dir(self):
        return Directory(self.get('dir'))
    
    def get_includes(self):
        includes = []
        for value_parts in self.config.popall('include', tuple()):
            value = os.path.abspath(self.compose(value_parts))
            if not os.path.isfile(value):
                raise ValueError(f"bad include directive: {value}")
            includes.append(value)
        return tuple(includes)
    
    def getline(self, key):
        value = self.get(key)
        return f"{key} {value}"
    
    def getlines(self, key):
        if key not in self:
            raise KeyError(key)
        lines = []
        for value_parts in self.config.getall(key):
            value = self.compose(value_parts)
            lines.append(f"{key} {value}")
        return lines
    
    def getall(self):
        lines = []
        for key in uniquify(self.config.keys()):
            lines.extend(self.getlines(key))
        return lines
    
    def assemble(self):
        return "\n".join(self)
    
    @property
    def path(self):
        return resolve(self, 'file.name')
    
    @property
    def is_temporary(self):
        return resolve(self, 'rdir.__class__') is TemporaryDirectory
    
    def setup(self):
        if not self.active:
            rdir = Intermediate(self.directory)
            conf = TemporaryName(prefix='redis-config-',
                                 suffix='conf',
                                 parent=rdir,
                                 randomized=True)
            self.set_dir(rdir)
            self.set_port(self.port)
            conf.write(self.assemble())
            self.rdir = rdir
            self.file = conf
            self.active = True
        return self
    
    def teardown(self):
        if self.active:
            if self.file:
                self.file.close()
                del self.file
            if self.rdir:
                self.rdir.close()
                del self.rdir
            self.active = False
    
    def __enter__(self):
        return self.setup()
    
    def __exit__(self, exc_type=None,
                       exc_val=None,
                       exc_tb=None):
        self.teardown()
        return exc_type is None
    
    def __len__(self):
        return len(self.config)
    
    def __iter__(self):
        yield from self.getall()
    
    def __contains__(self, key):
        return key in self.config
    
    def __getitem__(self, key):
        return self.get(key)
    
    def __setitem__(self, key, value):
        self.set(key, value)
    
    def __delitem__(self, key):
        del self.config[key]
    
    def __repr__(self):
        typename = type(self).__name__
        instance_id = hex(id(self))
        length = self.__len__()
        return f"{typename}<[{length} items]> @ {instance_id}"
    
    def __str__(self):
        return self.assemble()

def redis_server_args(*args):
    return (which('redis-server'), *args)

def redis_server_popen(*args):
    """ Invoke the “redis-server” CLI tool as a blocking
        subprocess, redirect all output to ‘/dev/null’, and
        return the subprocess handle instance
    """
    return subprocess.Popen(args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
         shell=False)

def redis_server_async(*args):
    """ Invoke the “redis-server” CLI tool as an asynchronous
        subprocess, redirect all output to ‘/dev/null’, and
        return the subprocess handle instance
    """
    return asyncio.create_subprocess_exec(*args,
           stdout=asyncio.subprocess.DEVNULL,
           stderr=asyncio.subprocess.DEVNULL)

def run_redis_popen(*args):
    """ Synchronous function wrapping the execution of the Redis server """
    logging.debug("[process] Starting Redis…")
    process = redis_server_popen(*args)
    
    logging.debug(f"[process] PID = {process.pid}")
    PID.set(process.pid)
    
    logging.debug("[process] Running Redis subprocess…")
    try:
        process.wait()
    except KeyboardInterrupt:
        logging.debug("")
        logging.debug("[process] Terminating process…")
        process.terminate()
        time.sleep(1)
    
    if process.returncode is None:
        logging.debug("[process] Killing process…")
        process.kill()
        process.wait(timeout=2)
    
    logging.debug(f"[process] RETVAL = {process.returncode}")
    return process

async def run_redis_async(*args):
    """ Coroutine wrapping the execution of the Redis server """
    logging.debug("[daemon] Starting Redis…")
    daemon = await redis_server_async(*args)
    
    logging.debug(f"[daemon] PID = {daemon.pid}")
    PID.set(daemon.pid)
    
    logging.debug("[daemon] Running Redis daemon…")
    try:
        await daemon.wait()
    except asyncio.CancelledError:
        logging.debug("")
        logging.debug("[daemon] Terminating process…")
        daemon.terminate()
        await asyncio.sleep(1)
    
    if daemon.returncode is None:
        logging.debug("[daemon] Killing process…")
        daemon.kill()
        await asyncio.sleep(1)
    
    logging.debug(f"[daemon] RETVAL = {daemon.returncode}")
    return daemon

class RedRun(object):
    
    def __init__(self, confpath):
        """ Initialize a RedRun manager with a given configuration file """
        path = os.fspath(confpath)
        if not os.path.exists(path):
            raise ValueError("bad Redis configuration file path")
        self.path = path
        self.close_loop = True
    
    def solve_problems(self, loop, context):
        """ Custom exception handler – invoked when in DEBUG mode """
        message = context.get('message')
        logging.warning(f"[redrun] ERROR: {message}")
        loop.call_exception_handler(context)
    
    def run(self):
        """ Call “RedRun.run()” within the managed context to run Redis """
        self.process = run_redis_async(*self.args)
        self.task = self.loop.create_task(self.process)
        self.loop.add_signal_handler(signal.SIGINT,  self.task.cancel)
        self.loop.add_signal_handler(signal.SIGTERM, self.task.cancel)
        self.loop.run_until_complete(self.task)
    
    async def execute_popen(self):
        self.close_loop = False
        with concur.ProcessPoolExecutor(1) as executor:
            self.future = await self.loop.run_in_executor(executor,
                                                          run_redis_popen,
                                                         *self.args)
        return concur.wait([self.future], return_when=concur.FIRST_EXCEPTION)
    
    def execute(self):
        # asyncio.run(self.execute_popen())
        # self.loop.add_signal_handler(signal.SIGINT,  lambda: None)
        # self.loop.add_signal_handler(signal.SIGTERM, lambda: None)
        # self.loop.run_until_complete(self.execute_popen())
        try:
            self.loop.run_until_complete(self.execute_popen())
        except KeyboardInterrupt:
            pass
        # except RuntimeError:
        #     pass
        # coro = await self.execute_popen()
        # self.loop.add_signal_handler(signal.SIGINT,  self.future.cancel)
        # self.loop.add_signal_handler(signal.SIGTERM, self.future.cancel)
        # self.loop.run_until_complete(coro)
    
    def __enter__(self):
        self.loop = asyncio.get_event_loop()
        if DEBUG:
            self.loop.set_debug(DEBUG)
            self.loop.set_exception_handler(self.solve_problems)
        self.args = redis_server_args(self.path)
        return self
    
    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if self.close_loop:
            if not self.loop.is_closed():
                self.loop.close()
        return exc_type is None

def test_redis_conf():
    
    loop = asyncio.get_event_loop()
    if DEBUG:
        loop.set_debug(DEBUG)
    
    with RedisConf() as redisconf:
        
        assert redisconf.file.exists
        
        print("REDIS CONF: repr")
        print('*' * 100)
        print(repr(redisconf))
        print('*' * 100)
        print("REDIS CONF: full text")
        print('*' * 100)
        print(str(redisconf))
        print('*' * 100)
        print("REDIS CONF: multidict")
        print('*' * 100)
        pprint(redisconf.config)
        print('*' * 100)
        
        task = loop.create_task(run_redis_async(
                               *redis_server_args(
                                redisconf.file.name)))
        loop.add_signal_handler(signal.SIGINT,  task.cancel)
        loop.add_signal_handler(signal.SIGTERM, task.cancel)
        
        try:
            loop.run_until_complete(task)
        finally:
            loop.close()
        
    assert not hasattr(redisconf, 'file')

def test_redrun():
    
    with RedisConf() as settings:
        assert settings.active
        assert settings.is_temporary
        with RedRun(settings.path) as redrunner:
            redrunner.run()

def test_redrun_background_executor():
    with concur.ProcessPoolExecutor() as executor:
        future = executor.submit(test_redrun)
        print("YO DOGG")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            executor.shutdown()
        try:
            print(future.result)
        except Exception as exc:
            print(f"[exexec] ERROR: {exc}")

def test_redrun_background():
    
    with RedisConf() as settings:
        with RedRun(settings.path) as redrunner:
            redrunner.execute()

if __name__ == '__main__':
    # test_redis_conf()
    test_redrun()
    # test_redrun_background()
