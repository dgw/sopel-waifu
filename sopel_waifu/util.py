"""sopel-waifu utilities

Part of sopel-waifu. Copyright 2024 dgw, technobabbl.es
"""
from __future__ import annotations


RECENT_WAIFUS_KEY = 'recent-waifus'


def cache_waifu(bot, waifu, nick, channel):
    """Store the ``waifu`` that ``nick`` last got in ``channel``."""
    if channel not in bot.memory[RECENT_WAIFUS_KEY]:
        bot.memory[RECENT_WAIFUS_KEY][channel] = bot.make_identifier_memory()

    bot.memory[RECENT_WAIFUS_KEY][channel][nick] = waifu


def get_last_waifu(bot, nick, channel):
    """Get the last waifu that ``nick`` got in ``channel``."""
    return bot.memory[RECENT_WAIFUS_KEY].get(channel, {}).get(nick, None)


def clear_last_waifu(bot, nick, channel):
    """Clear the last waifu that ``nick`` got in ``channel``.

    Used for ``.wifight`` command, if the challenger wins.
    """
    bot.memory[RECENT_WAIFUS_KEY].get(channel, {}).pop(nick, None)


def clean_up_channel(bot, channel):
    """Remove all cached data for a ``channel``."""
    bot.memory[RECENT_WAIFUS_KEY].pop(channel, None)


def clean_up_nickname(bot, nick, channel=None):
    """Remove cached data for a ``nick``, optionally scoped to a ``channel``.

    If no channel is specified, the nick's cached data will be removed for ALL
    channels the bot knows about. Use this operating mode for QUITs, or if the
    bot itself is KICKed from a channel.
    """
    if channel:
        bot.memory[RECENT_WAIFUS_KEY].get(channel, {}).pop(nick, None)
    else:
        for channel in bot.memory[RECENT_WAIFUS_KEY].keys():
            bot.memory[RECENT_WAIFUS_KEY][channel].pop(nick, None)
