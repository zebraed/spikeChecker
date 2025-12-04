#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
from .gui_main import showUI

__all__ = ["showUI", "Reload"]


def Reload():
    """
    モジュール全体をリロードする
    """
    import sys
    for k in list(sys.modules):
        if k.startswith("spikeChecker"):
            del sys.modules[k]
    print("spikeChecker Reloaded.")
