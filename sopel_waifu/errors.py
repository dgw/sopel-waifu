"""sopel-waifu errors submodule

Part of sopel-waifu. Copyright 2024 dgw, technobabbl.es
"""
from __future__ import annotations


class WaifuError(Exception):
    """Base class for sopel-waifu plugin errors."""


class NoWaifuError(WaifuError):
    """This user doesn't have a waifu yet!"""
    def __init__(self, nick, channel):
        self.nick = nick
        self.channel = channel

    def __str__(self):
        return f"{self.nick} doesn't have a waifu in {self.channel} yet."
