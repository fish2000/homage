#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from __future__ import print_function
from distutils.spawn import find_executable

import asyncio
import concurrent.futures
import contextvars
import multidict
import os
import warnings

# from clu.fs.filesystem import back_tick
from clu.fs.filesystem import TemporaryName, Directory, TemporaryDirectory
from clu.naming import nameof

PID = contextvars.ContextVar('PID')

CONF = """cat /usr/local/etc/redis.conf | grep -v -e "^#" | sed '/^[[:space:]]*$/d'"""

class RedisConf(object):
    
    DEFAULT_SOURCE = '/usr/local/etc/redis.conf'
    
    @staticmethod
    def decompose(value):
        return tuple(value.split())
    
    def __init__(self, source=None, port=6379):
        self.config = multidict.MultiDict()
        self.port = port
        self.source = source
        self.parse(self.source \
           or type(self).DEFAULT_SOURCE)
    
    def parse(self, source):
        with open(source, 'r') as handle:
            lines = filter(None,
                    filter(lambda line: not line.startswith('#'),
                           handle.readlines()))
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
        self.set('port',    str(port))
        self.set('pidfile', f"/var/run/redis_{port}.pid")
    
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
    
    def __enter__(self):
        rdir = TemporaryDirectory(prefix="redis-")
        conf = TemporaryName(prefix='redis-config-',
                             suffix='conf',
                             parent=rdir,
                             randomized=True)
        self.set_port(self.port)
        self.set_dir(rdir)
        conf.write(self.assemble())
        self.rdir = rdir
        self.file = conf
        return self
    
    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if self.file:
            self.file.close()
            del self.file
        if self.rdir:
            self.rdir.close()
            del self.rdir
        return exc_type is None
    
    def __repr__(self):
        instance_id = hex(id(self))
        length = len(self.config)
        return f"RedisConf<[{length} items]> @ {instance_id}"
    
    def __str__(self):
        return self.assemble()

def which(binary_name, pathvar=None):
    """ Deduces the path corresponding to an executable name,
        as per the UNIX command `which`. Optionally takes an
        override for the $PATH environment variable.
        Always returns a string - an empty one for those
        executables that cannot be found.
    """
    return find_executable(binary_name, pathvar or which.pathvar) or ""

which.pathvar = os.environ.get('PATH')

def redis_server(*args):
    return asyncio.create_subprocess_exec(
        which('redis-server'), *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL)

async def run_redis_server():
    print("[daemon] Starting Redis…")
    daemon = await redis_server()
    
    print(f"[daemon] PID = {daemon.pid}")
    PID.set(daemon.pid)
    
    try:
        print("[daemon] Awaiting interrupt signal")
        await daemon.wait()
    except KeyboardInterrupt:
        print("[daemon] Terminating process…")
        daemon.terminate()
    
    if daemon.returncode is None:
        print("[daemon] Killing process…")
        daemon.kill()
    
    print(f"[daemon] RETVAL = {daemon.returncode}")

async def run_redis_task():
    PID.set(-1)
    task = asyncio.create_task(run_redis_server())
    taskID = hex(id(task))
    pid = PID.get()
    print(f"[runctx] Redis server task created <id:{taskID}>")
    print(f"[runctx] PID = {pid}")
    return await task

def schedule(target, *, loop=None):
    if asyncio.iscoroutine(target):
        return asyncio.ensure_future(target, loop=loop)
    typename = nameof(type(target))
    raise TypeError(f"target must be a coroutine (not {typename})")

def main():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            asyncio.run(run_redis_task())
        except KeyboardInterrupt:
            print()
            print("[runctx] Shutting down…")

async def async_background():
    loop = asyncio.new_event_loop()
    with concurrent.futures.ProcessPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, run_redis_task())
    print('custom process pool', result)

def background():
    with concurrent.futures.ProcessPoolExecutor() as executor:
        future = executor.submit(main)
        print(future.result)

if __name__ == '__main__':
    # main()
    # asyncio.run(background())
    background()
    print("YO DOGG")