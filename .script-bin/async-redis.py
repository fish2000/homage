#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from __future__ import print_function
from pprint import pprint

import asyncio
import concurrent.futures
import contextvars
import logging
import multidict
import os
import signal
import subprocess

from clu.constants.consts import DEBUG
from clu.fs.filesystem import (which,
                               TemporaryName,
                               TemporaryDirectory,
                                        Directory)

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
    
    DEFAULT_SOURCE = '/usr/local/etc/redis.conf'
    
    @staticmethod
    def decompose(value):
        return tuple(value.split())
    
    def __init__(self, source=None, port=6379):
        self.config = multidict.MultiDict()
        self.port = port
        self.source = source
        self.active = False
        self.parse(self.source \
           or type(self).DEFAULT_SOURCE)
    
    def parse(self, source):
        with open(source, 'r') as handle:
            lines = filter(None,
                    map(lambda line: line.strip(),
                    filter(lambda line: not line.startswith('#'),
                           handle.readlines())))
        for line in lines:
            parts = line.split(None, 1)
            self.config.add(parts[0],
             self.decompose(parts[1]))
        return self.config
    
    def add(self, key, value):
        self.config.add(key, self.decompose(value))
    
    def set(self, key, value):
        self.config[key] = self.decompose(value)
    
    def set_port(self, port):
        redisdir = self.get_dir()
        self.set('port',    str(port))
        self.set('pidfile', redisdir.subpath(f"redis_{port}.pid"))
    
    def get_port(self):
        return int(' '.join(self.config.get('port')), base=10)
    
    def set_dir(self, directory):
        self.set('dir', os.fspath(directory))
    
    def get_dir(self):
        return Directory(' '.join(self.config.get('dir')))
    
    def getline(self, key):
        if key not in self.config:
            raise KeyError(key)
        value = ' '.join(self.config.get(key))
        return f"{key} {value}"
    
    def getlines(self, key):
        if key not in self.config:
            raise KeyError(key)
        lines = []
        for value_parts in self.config.getall(key):
            value = ' '.join(value_parts)
            lines.append(f"{key} {value}")
        return lines
    
    def assemble(self):
        lines = []
        for key in self.config.keys():
            lines.extend(self.getlines(key))
        return "\n".join(lines)
    
    @property
    def path(self):
        return self.file.name
    
    def __enter__(self):
        rdir = TemporaryDirectory(prefix="redis-")
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
    
    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if self.file:
            self.file.close()
            del self.file
        if self.rdir:
            self.rdir.close()
            del self.rdir
        self.active = False
        return exc_type is None
    
    def __repr__(self):
        instance_id = hex(id(self))
        length = len(self.config)
        return f"RedisConf<[{length} items]> @ {instance_id}"
    
    def __str__(self):
        return self.assemble()

def redis_server_args(*args):
    return (which('redis-server'), *args)

def redis_server_popen(*args):
    return subprocess.Popen(*args,
       bufsize=-1,
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
    
    if process.returncode is None:
        logging.debug("[process] Killing process…")
        process.kill()
    
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
    
    if daemon.returncode is None:
        logging.debug("[daemon] Killing process…")
        daemon.kill()
    
    logging.debug(f"[daemon] RETVAL = {daemon.returncode}")
    return daemon

class RedRun(object):
    
    def __init__(self, confpath):
        """ Initialize a RedRun manager with a given configuration file """
        path = os.fspath(confpath)
        if not os.path.exists(path):
            raise ValueError("bad Redis configuration file path")
        self.loop = asyncio.get_event_loop()
        self.path = path
        if DEBUG:
            self.loop.set_debug(DEBUG)
    
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
        with concurrent.futures.ProcessPoolExecutor() as executor:
            self.future = await self.loop.run_in_executor(executor,
                                                          run_redis_popen,
                                                         *self.args)
            self.loop.add_signal_handler(signal.SIGINT,  self.future.cancel)
            self.loop.add_signal_handler(signal.SIGTERM, self.future.cancel)
            return await self.future
    
    def execute(self):
        # return asyncio.run(self.execute_popen())
        self.loop.run_until_complete(self.execute_popen())
    
    def __enter__(self):
        self.args = redis_server_args(self.path)
        if DEBUG:
            self.loop.set_exception_handler(self.solve_problems)
        return self
    
    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.loop.close()
        return exc_type is None

def test_redis_conf():
    
    loop = asyncio.get_event_loop()
    
    with RedisConf() as redisconf:
        
        assert redisconf.file.exists
        
        print("REDIS CONF: full text")
        print('*' * 100)
        print(str(redisconf))
        print('*' * 100)
        print("REDIS CONF: multidict")
        print('*' * 100)
        pprint(redisconf.config)
        print('*' * 100)
        
        task = loop.create_task(run_redis_async(redisconf.file.name))
        loop.add_signal_handler(signal.SIGINT,  task.cancel)
        loop.add_signal_handler(signal.SIGTERM, task.cancel)
        
        try:
            loop.run_until_complete(task)
        finally:
            loop.close()
        
    assert not hasattr(redisconf, 'file')

def test_redrun():
    
    with RedisConf() as settings:
        with RedRun(settings.path) as redrunner:
            redrunner.run()

def test_redrun_background_executor():
    with concurrent.futures.ProcessPoolExecutor() as executor:
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
            # asyncio.run(redrunner.execute())
            redrunner.execute()

if __name__ == '__main__':
    # test_redis_conf()
    # test_redrun()
    test_redrun_background()
