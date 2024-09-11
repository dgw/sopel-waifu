"""sopel-waifu utilities

Part of sopel-waifu. Copyright 2024 dgw, technobabbl.es
"""
from __future__ import annotations


BATTLE_CACHE = 'recent-waifu-battles'
WAIFU_CACHE = 'recent-waifus'
# these are used in too many places to repeat them every time
UTIL_KEYS = (
    BATTLE_CACHE,
    WAIFU_CACHE,
)


def set_waifu_stolen_by(bot, thief, waifu, nick, channel):
    """Store the ``thief`` who took ``nick``'s ``waifu`` in the ``channel``."""
    if channel not in bot.memory[BATTLE_CACHE]:
        bot.memory[BATTLE_CACHE][channel] = bot.make_identifier_memory()

    bot.memory[BATTLE_CACHE][channel][nick] = (thief, waifu)


def get_waifu_stolen_by(bot, nick, channel):
    """Check who took ``nick``'s waifu in the ``channel``, if anyone."""
    return bot.memory[BATTLE_CACHE].get(channel, {}).get(nick, (None, None))


def clear_waifu_stolen_by(bot, nick, channel):
    """Clear who took ``nick``'s waifu in the ``channel``."""
    bot.memory[BATTLE_CACHE].get(channel, {}).pop(nick, None)


def set_last_waifu(bot, waifu, nick, channel):
    """Store the ``waifu`` that ``nick`` last got in ``channel``."""
    if channel not in bot.memory[WAIFU_CACHE]:
        bot.memory[WAIFU_CACHE][channel] = bot.make_identifier_memory()

    bot.memory[WAIFU_CACHE][channel][nick] = waifu


def get_last_waifu(bot, nick, channel):
    """Get the last waifu that ``nick`` got in ``channel``."""
    return bot.memory[WAIFU_CACHE].get(channel, {}).get(nick, None)


def clear_last_waifu(bot, nick, channel):
    """Clear the last waifu that ``nick`` got in ``channel``.

    Used for ``.wifight`` command, if the challenger wins.
    """
    bot.memory[WAIFU_CACHE].get(channel, {}).pop(nick, None)


def clean_up_channel(bot, channel):
    """Remove all cached data for a ``channel``."""
    for key in UTIL_KEYS:
        bot.memory[key].pop(channel, None)


def clean_up_nickname(bot, nick, channel=None):
    """Remove cached data for a ``nick``, optionally scoped to a ``channel``.

    If no channel is specified, the nick's cached data will be removed for ALL
    channels the bot knows about. Use this operating mode for QUITs, or if the
    bot itself is KICKed from a channel.
    """
    if channel:
        for key in UTIL_KEYS:
            bot.memory[key].get(channel, {}).pop(nick, None)
    else:
        for key in UTIL_KEYS:
            for channel in bot.memory[key].keys():
                bot.memory[key][channel].pop(nick, None)


def setup_caches(bot):
    """Set up cache keys in the ``bot``'s memory."""
    for key in UTIL_KEYS:
        bot.memory[key] = bot.make_identifier_memory()


def shutdown_caches(bot):
    """Clean up cache keys used in the ``util`` submodule."""
    for key in UTIL_KEYS:
        try:
            del bot.memory[key]
        except KeyError:
            pass
