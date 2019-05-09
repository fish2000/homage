# -*- encoding: utf-8 -*-
from __future__ import print_function, unicode_literals

try:
    from functools import reduce
except (ImportError, SyntaxError):
    pass

Σ = reduce

__all__ = (u'Σ',)
__dir__ = lambda: list(__all__)
