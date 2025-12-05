#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
from .gui_main import showUI
from .checker import check_attr_spike

__all__ = ["showUI", "Reload", "check_attr_spike"]


def Reload():
    """
    Reload all modules
    """
    import sys
    for k in list(sys.modules):
        if k.startswith("spikeChecker"):
            del sys.modules[k]
    print("spikeChecker Reloaded.")
