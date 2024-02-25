# coding=utf8
"""sopel-waifu

A Sopel plugin that picks a waifu for you.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import json
import os
import random

from sopel import config, formatting, plugin, tools


LOGGER = tools.get_logger('waifu')
WAIFU_LIST_KEY = 'waifu-list'
WAIFU_SUGGESTIONS_FILE = 'waifu-suggestions.txt'


def get_waifu_suggestions_file(bot):
    return os.path.join(bot.config.core.homedir, WAIFU_SUGGESTIONS_FILE)


class WaifuSection(config.types.StaticSection):
    json_path = config.types.FilenameAttribute('json_path', relative=False)
    """JSON file from which to load list of possible waifus."""
    json_mode = config.types.ChoiceAttribute('json_mode', ['replace', 'extend'], default='extend')
    """How the file specified by json_path should affect the default list."""
    unique_waifus = config.types.BooleanAttribute('unique_waifus', default=True)
    """Whether to deduplicate the waifu list during startup."""
    accept_suggestions = config.types.BooleanAttribute('accept_suggestions', default=False)
    """Whether to accept waifu suggestions via the `.addwaifu` command."""


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

    bot.memory[WAIFU_LIST_KEY] = []
    for filename in filenames:
        with open(filename, 'r') as file:
            data = json.load(file)

        for franchise, waifus in data.items():
            bot.memory[WAIFU_LIST_KEY].extend([
                    '{waifu}{franchise}'.format(
                        waifu=waifu,
                        franchise=(
                            ' ({})'.format(franchise)
                            if franchise and not waifu.endswith('(F/GO)')
                            else ''
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

    # handle formatting syntax of the original waifu-bot
    choice = choice.replace('$c', formatting.CONTROL_COLOR)

    if target:
        msg = "{target}'s waifu is {waifu}"
    else:
        target = trigger.nick
        msg = '{target}, your waifu is {waifu}'

    bot.say(msg.format(target=target, waifu=choice))


@plugin.commands('fmk')
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

    sample = [item.replace('$c', formatting.CONTROL_COLOR) for item in sample]

    msg = "Fuck: {sample[0]}; Marry: {sample[1]}; Kill: {sample[2]}."
    if target:
        msg = target + " will " + msg

    bot.say(msg.format(sample=sample))


@plugin.commands('addwaifu')
@plugin.example('.addwaifu Holo from Spice & Wolf')
@plugin.require_chanmsg('No hiding your perverted waifu preferences in PM!')
def add_waifu(bot, trigger):
    """Suggest a waifu for the bot admin to add in custom list."""
    if not bot.config.waifu.accept_suggestions:
        bot.reply("Waifu suggestions aren't enabled.")
        return

    new_waifu = trigger.group(2)
    if not new_waifu:
        bot.reply("Who did you want to suggest?")
        return plugin.NOLIMIT

    file_path = get_waifu_suggestions_file(bot)
    created = not os.path.isfile(file_path)

    try:
        with open(file_path, 'a') as f:
            f.write(new_waifu + '\n')
    except Exception:
        bot.reply("I'm terribly sorry, but something has gone very wrong. "
                  "Please notify my owner, {}.".format(bot.config.core.owner))
        return
    else:
        bot.say("Recorded {}'s suggestion for a new waifu: {}".format(
            trigger.nick, new_waifu)
        )
        if created:
            bot.say(
                "Created a waifu suggestion file at: {}".format(file_path),
                bot.config.core.owner)


@plugin.commands('clearwaifus')
@plugin.require_admin('Only a bot admin can clear my waifu suggestion list.')
def clear_suggestions(bot, trigger):
    """Clear the waifu suggestion list."""
    file_path = get_waifu_suggestions_file(bot)

    if not os.path.isfile(file_path):
        bot.reply('There are no waifu suggestions to clear.')
        return

    LOGGER.info('Deleting saved waifu suggestions from {}'.format(file_path))
    os.remove(file_path)
    bot.reply("Cleared waifu suggestions.")
