"""sopel-waifu

A Sopel plugin that picks a waifu for you.
"""
from __future__ import annotations

import collections
import json
import os
import random

from sopel import config, formatting, plugin, tools


LOGGER = tools.get_logger('waifu')
OUTPUT_PREFIX = '[waifu] '
WAIFU_LIST_KEY = 'waifu-list'


def _unescape_formatting(text):
    # Original waifu-bot on Rizon used $c to escape ^K for colors.
    # More formatting types can be handled here too, if they'd be useful.
    return text.replace('$c', formatting.CONTROL_COLOR)


class WaifuSection(config.types.StaticSection):
    json_path = config.types.FilenameAttribute('json_path', relative=False)
    """JSON file from which to load list of possible waifus."""
    json_mode = config.types.ChoiceAttribute('json_mode', ['replace', 'extend'], default='extend')
    """How the file specified by json_path should affect the default list."""
    unique_waifus = config.types.BooleanAttribute('unique_waifus', default=True)
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
            raise config.ConfigurationError('Invalid json_mode.')

    bot.memory[WAIFU_LIST_KEY] = []
    for filename in filenames:
        with open(filename, 'r') as file:
            data = json.load(file)

        for franchise, waifus in data.items():
            bot.memory[WAIFU_LIST_KEY].extend([
                    _unescape_formatting(
                        '{waifu}{franchise}'.format(
                            waifu=waifu,
                            franchise=' ({})'.format(
                                formatting.italic(franchise)
                                if franchise else ''
                            )
                        )
                    )
                    for waifu in waifus
                ])

    duplicates = [
        waifu for waifu, count
        in collections.Counter(bot.memory[WAIFU_LIST_KEY]).items()
        if count > 1
    ]
    if duplicates:
        count = len(duplicates)
        LOGGER.info("Found %s duplicate waifu%s: %s",
                    count, '' if count == 1 else 's', ', '.join(duplicates))

    if bot.config.waifu.unique_waifus:
        bot.memory[WAIFU_LIST_KEY] = list(set(bot.memory[WAIFU_LIST_KEY]))


def shutdown(bot):
    try:
        del bot.memory[WAIFU_LIST_KEY]
    except KeyError:
        pass


@plugin.commands('waifu')
@plugin.output_prefix(OUTPUT_PREFIX)
@plugin.example('.waifu Peorth', user_help=True)
@plugin.example('.waifu', user_help=True)
def waifu(bot, trigger):
    """Pick a random waifu for yourself or the given nick."""
    target = trigger.group(3)

    try:
        choice = random.choice(bot.memory[WAIFU_LIST_KEY])
    except IndexError:
        bot.reply("Sorry, looks like the waifu list is empty!")
        return

    if target:
        msg = "{target}'s waifu is {waifu}"
    else:
        target = trigger.nick
        msg = '{target}, your waifu is {waifu}'

    bot.say(msg.format(target=target, waifu=choice))


@plugin.commands('fmk')
@plugin.output_prefix(OUTPUT_PREFIX)
@plugin.example('.fmk Peorth', user_help=True)
@plugin.example('.fmk', user_help=True)
def fmk(bot, trigger):
    """Pick random waifus to fuck, marry and kill."""
    target = trigger.group(3)

    try:
        sample = random.sample(bot.memory[WAIFU_LIST_KEY], 3)
    except ValueError:
        condition = 'empty' if len(bot.memory[WAIFU_LIST_KEY]) == 0 else 'too short'
        bot.reply(
            "Sorry, looks like the waifu list is {condition}!",
            condition=condition,
        )
        return

    msg = "Fuck: {sample[0]}; Marry: {sample[1]}; Kill: {sample[2]}."
    if target:
        msg = target + " will " + msg

    bot.say(msg.format(sample=sample))
