# coding=utf8
"""sopel-waifu

A Sopel plugin that picks a waifu for you.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import random

from sopel import config, formatting, module


class WaifuSection(config.types.StaticSection):
    json_path = config.types.FilenameAttribute('json_path', relative=False)
    """JSON file from which to load list of possible waifus."""


def setup(bot):
    bot.config.define_section('waifu', WaifuSection)

    if bot.config.waifu.json_path:
        filename = bot.config.waifu.json_path
    else:
        filename = os.path.join(os.path.dirname(__file__), 'waifu.json')

    with open(filename, 'r') as file:
        data = json.load(file)

    bot.memory['waifu-list'] = []
    for franchise, waifus in data.items():
        bot.memory['waifu-list'].extend([
                '{waifu} ({franchise})'.format(waifu=waifu, franchise=franchise)
                for waifu in waifus
            ])

    bot.memory['waifu-list-fgo'] = [
        waifu for waifu in bot.memory['waifu-list']
        if 'Fate/Grand Order' in waifu
    ]


def shutdown(bot):
    try:
        del bot.memory['waifu-list']
    except KeyError:
        pass


@module.commands('waifu', 'fgowaifu', 'fgowf')
@module.example('.waifu Peorth', user_help=True)
@module.example('.waifu', user_help=True)
def waifu(bot, trigger):
    """Pick a random waifu for yourself or the given nick."""
    target = trigger.group(3)
    command = trigger.group(1).lower()

    key = 'waifu-list'
    if command in ['fgowaifu', 'fgowf']:
        key = 'waifu-list-fgo'
    try:
        choice = random.choice(bot.memory[key])
    except IndexError:
        bot.reply("Sorry, looks like the waifu list is empty!")

    # handle formatting syntax of the original waifu-bot
    choice = choice.replace('$c', formatting.CONTROL_COLOR)

    if target:
        msg = "{target}'s waifu is {waifu}"
    else:
        target = trigger.nick
        msg = '{target}, your waifu is {waifu}'

    bot.say(msg.format(target=target, waifu=choice))
