# coding=utf8
"""sopel-waifu

A Sopel plugin that picks a waifu for you.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import json
import os
import random

from sopel import config, formatting, module, tools


LOGGER = tools.get_logger('waifu')


class WaifuSection(config.types.StaticSection):
    json_path = config.types.FilenameAttribute('json_path', relative=False)
    """JSON file from which to load list of possible waifus."""
    json_mode = config.types.ChoiceAttribute('json_mode', ['replace', 'extend'], default='extend')
    """How the file specified by json_path should affect the default list."""
    unique_waifus = config.types.ValidatedAttribute('unique_waifus', bool, default=True)
    """Whether to deduplicate the waifu list during startup."""


def setup(bot):
    bot.config.define_section('waifu', WaifuSection)

    filenames = [os.path.join(os.path.dirname(__file__), 'waifu.json')]
    if bot.config.waifu.json_path:
        if bot.config.waifu.json_mode == 'replace':
            filenames = [bot.config.waifu.json_path]
        elif bot.config.waifu.json_mode == 'extend':
            filenames.append(bot.config.waifu.json_path)
        else:
            raise Exception('Invalid json_mode.')

    bot.memory['waifu-list'] = []
    for filename in filenames:
        with open(filename, 'r') as file:
            data = json.load(file)

        for franchise, waifus in data.items():
            bot.memory['waifu-list'].extend([
                    '{waifu}{franchise}'.format(
                        waifu=waifu,
                        franchise=' ({})'.format(franchise) if franchise else '')
                    for waifu in waifus
                ])

    duplicates = [
        waifu for waifu, count
        in collections.Counter(bot.memory['waifu-list']).items()
        if count > 1
    ]
    if duplicates:
        count = len(duplicates)
        LOGGER.info("Found %s duplicate waifu%s: %s",
                    count, '' if count == 1 else 's', ', '.join(duplicates))

    if bot.config.waifu.unique_waifus:
        bot.memory['waifu-list'] = list(set(bot.memory['waifu-list']))

    bot.memory['waifu-list-fgo'] = [
        waifu for waifu in bot.memory['waifu-list']
        if 'Fate/Grand Order' in waifu
    ]


def shutdown(bot):
    for key in ['waifu-list', 'waifu-list-fgo']:
        try:
            del bot.memory[key]
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
