#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from __future__ import print_function

import abc

class Metabase(abc.ABCMeta):
    
    def __new__(metacls, name, bases, attributes, **kwargs):
        # Call up:
        return super(Metabase, metacls).__new__(metacls, name,
                                                         bases,
                                                         attributes,
                                                       **kwargs)

class Metaclass(Metabase):
    
    def __new__(metacls, name, bases, attributes, metakeyword="meta", **kwargs):
        # Stow metaclass keyword in attributes:
        if 'metakeyword' not in attributes:
            attributes['metakeyword'] = metakeyword
        
        # Remove metaclass’ keyword and call up:
        return super(Metaclass, metacls).__new__(metacls, name,
                                                          bases,
                                                          attributes,
                                                        **kwargs)

class Mixin(abc.ABC, metaclass=Metabase):
    
    @classmethod
    def __init_subclass__(cls, mixinkeyword="mixin", **kwargs):
        # Remove mixins’ keyword and call up:
        super(Mixin, cls).__init_subclass__(**kwargs)
        
        # Stow mixin keyword on subclass:
        cls.mixinkeyword = mixinkeyword

class Base(Mixin, metaclass=Metaclass):
    pass

class Derived(Base, mixinkeyword="derived-mixin",
                    metakeyword="derived-meta"):
    pass

def test():
    d = Derived()
    print(d)
    print(d.mixinkeyword)
    print(d.metakeyword)

if __name__ == '__main__':
    test()