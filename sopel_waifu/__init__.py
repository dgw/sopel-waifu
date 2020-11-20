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
    accept_suggestions = config.types.ValidatedAttribute('accept_suggestions', bool, default=False)
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

    if bot.config.waifu.accept_suggestions:
        LOGGER.debug("Waifu suggestions are enabled; loading suggestion cache")
        bot.memory['waifu-suggestions'] = bot.db.get_plugin_value(
            'waifu', 'suggestions', [])


def shutdown(bot):
    if 'waifu-suggestions' in bot.memory:
        LOGGER.debug("Persisting waifu suggestion cache to database...")
        bot.db.set_plugin_value('waifu', 'suggestions', bot.memory['waifu-suggestions'])
        del bot.memory['waifu-suggestions']
        LOGGER.debug("...done!")

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


@module.commands('addwaifu')
@module.example('.addwaifu Holo from Spice & Wolf')
@module.require_chanmsg('No hiding your perverted waifu preferences in PM!')
def add_waifu(bot, trigger):
    """Suggest a waifu for the bot admin to add in custom list."""
    if not bot.config.waifu.accept_suggestions:
        bot.reply("Waifu suggestions aren't enabled.")
        return

    new_waifu = trigger.group(2)
    if not new_waifu:
        bot.reply("Who did you want to suggest?")
        return module.NOLIMIT

    try:
        bot.memory['waifu-suggestions'].append(new_waifu)
    except Exception:
        bot.reply("I'm terribly sorry, but something has gone very wrong. "
                  "Please notify my owner, {}".format(bot.config.core.owner))
        return
    else:
        bot.say("Recorded {}'s suggestion for a new waifu: {}".format(trigger.nick, new_waifu))


@module.commands('dumpwaifus')
@module.require_admin
def dump_waifus(bot, trigger):
    """Dump the list of suggested waifus to a file in Sopel's homedir."""
    if 'waifu-suggestions' not in bot.memory or not bot.memory['waifu-suggestions']:
        bot.reply("No waifu suggestions to dump.")
        return

    filename = os.path.join(bot.config.core.homedir, 'suggested-waifus.txt')

    try:
        with open(filename, 'a') as file:
            for waifu in bot.memory['waifu-suggestions']:
                file.write(waifu + '\n')
    except Exception:
        bot.reply("Sorry, something went wrong.")
        return
    else:
        bot.reply("Dumped waifu suggestions to file. Location sent separately in PM.")
        bot.say("Waifu suggestion file: {}".format(filename), trigger.nick)


@module.commands('clearwaifus')
@module.require_admin('Only a bot admin can clear my waifu suggestion list.')
def clear_suggestions(bot, trigger):
    """Clear the waifu suggestion cache."""
    if 'waifu-suggestions' in bot.memory:
        if bot.memory['waifu-suggestions']:
            LOGGER.info('Cached waifu suggestions:')
            for waifu in bot.memory['waifu-suggestions']:
                LOGGER.info('    %s', waifu)
        LOGGER.debug('Clearing waifu suggestion cache in memory')
        bot.memory['waifu-suggestions'] = []

    LOGGER.debug('Deleting saved waifu suggestions from bot DB')
    bot.db.delete_plugin_value('waifu', 'suggestions')

    bot.reply("Cleared waifu suggestions.")
