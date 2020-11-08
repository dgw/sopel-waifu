# coding=utf8
"""sopel-waifu

A Sopel plugin that picks a waifu for you.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import random

from sopel import formatting, module


def setup(bot):
    filename = os.path.join(os.path.dirname(__file__), 'waifu.json')
    with open(filename, 'r') as file:
        bot.memory['waifu-data'] = json.load(file)


def shutdown(bot):
    try:
        del bot.memory['waifu-data']
    except KeyError:
        pass


@module.commands('waifu')
@module.example('.waifu Peorth', user_help=True)
@module.example('.waifu', user_help=True)
def waifu(bot, trigger):
    """Pick a random waifu for yourself or the given nick."""
    target = trigger.group(3)
    choice = random.choice(bot.memory['waifu-data']['1'])

    # handle formatting syntax of the original waifu-bot
    choice = choice.replace('$c', formatting.CONTROL_COLOR)
    # TODO: need a function like xkcd-Bucket's &someone() subroutine
    # to get a random nick that's spoken recently, so as to avoid HLing
    # idle users in waifu spam
    choice = choice.replace('${randomchannelnick}', bot.nick)

    if target:
        msg = bot.memory['waifu-data']['2pre'].replace('$t', target)
    else:
        msg = bot.memory['waifu-data']['1pre'].replace('$s', trigger.nick)

    bot.say(msg + choice)