#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from __future__ import print_function

import asyncio
import concurrent.futures
import contextvars
import warnings

from clu.naming import nameof
from clu.fs.filesystem import which

PID = contextvars.ContextVar('PID')

def redis_server(*args):
    return asyncio.create_subprocess_exec(
        which('redis-server'), *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL)

async def run_redis_server(*args):
    print("[daemon] Starting Redis…")
    daemon = await redis_server(*args)
    
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

async def run_redis_task(*args):
    PID.set(-1)
    task = asyncio.create_task(run_redis_server(*args))
    taskID = hex(id(task))
    pid = PID.get()
    argstring = ', '.join(args)
    print(f"[runctx] Redis server task created <id:{taskID}>")
    print(f"[runctx] PID = {pid}")
    print(f"[runctx] args = ({argstring})")
    return await task

def schedule(target, *, loop=None):
    if asyncio.iscoroutine(target):
        return asyncio.ensure_future(target, loop=loop)
    typename = nameof(type(target))
    raise TypeError(f"target must be a coroutine (not {typename})")

def main(*args):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            asyncio.run(run_redis_task(*args))
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
