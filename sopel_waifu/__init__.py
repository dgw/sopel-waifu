"""sopel-waifu

A Sopel plugin that picks a waifu for you.

Copyright 2020-2024 dgw, technobabbl.es
"""
from __future__ import annotations

import collections
import json
import os
import random

from sopel import config, formatting, plugin, tools

from . import util


LOGGER = tools.get_logger('waifu')
OUTPUT_PREFIX = '[waifu] '
WAIFU_LIST_KEY = 'waifu-list'
WAIFU_SUGGESTIONS_FILE = 'waifu-suggestions.txt'


def get_waifu_suggestions_file(bot):
    return os.path.join(bot.config.core.homedir, WAIFU_SUGGESTIONS_FILE)


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

    bot.memory[util.RECENT_WAIFUS_KEY] = bot.make_identifier_memory()


def shutdown(bot):
    for key in (WAIFU_LIST_KEY, util.RECENT_WAIFUS_KEY):
        try:
            del bot.memory[key]
        except KeyError:
            pass


@plugin.echo
@plugin.event('PART')
@plugin.priority('low')
@plugin.unblockable
def part_cleanup(bot, trigger):
    """Clean up cached data when a user leaves a channel."""
    if trigger.nick == bot.nick:
        # We're outta here! Nuke the whole channel's cache.
        util.clean_up_channel(bot, trigger.sender)
    else:
        # Someone else left; clean up after them.
        util.clean_up_nickname(bot, trigger.nick, trigger.sender)


@plugin.echo
@plugin.event('QUIT')
@plugin.priority('low')
@plugin.unblockable
def quit_cleanup(bot, trigger):
    """Clean up cached data after a user quits IRC."""
    # If Sopel itself quits, shutdown() will handle the cleanup.
    util.clean_up_nickname(bot, trigger.nick)


@plugin.echo
@plugin.event('KICK')
@plugin.priority('low')
@plugin.unblockable
def kick_cleanup(bot, trigger):
    """Clean up cached data when a user is kicked from a channel."""
    nick = bot.make_identifier(trigger.args[1])
    if nick == bot.nick:
        # We got kicked! Nuke the whole channel.
        util.clean_up_channel(bot, trigger.sender)
    else:
        # Clean up after whoever got the boot.
        util.clean_up_nickname(bot, nick, trigger.sender)


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
    util.set_last_waifu(bot, choice, target, trigger.sender)


@plugin.command('lastwaifu')
@plugin.require_chanmsg
@plugin.output_prefix(OUTPUT_PREFIX)
@plugin.example('.lastwaifu Peorth', user_help=True)
@plugin.example('.lastwaifu', user_help=True)
def last_waifu(bot, trigger):
    """Get a reminder of someone's last waifu, without picking a new one.

    This is scoped to the current channel.
    """
    target = trigger.group(3) or trigger.nick

    cached = util.get_last_waifu(bot, target, trigger.sender)
    if cached is None:
        bot.say("{} hasn't gotten a waifu recently.".format(target))
        return plugin.NOLIMIT

    bot.say("{}'s last waifu was {}.".format(target, cached))


@plugin.command('wifight')
@plugin.rate_user(
    300, "Relax, {nick}. You can challenge someone again in {time_left}.")
@plugin.require_chanmsg
@plugin.output_prefix('[Waifu Fight!] ')
@plugin.example('.wifight Peorth')
def waifu_fight(bot, trigger):
    """Fight someone for their last waifu."""
    challenger = trigger.nick

    target = trigger.group(3)
    if not target or target == challenger:
        if target == challenger:
            who = formatting.bold('someone else')
        else:
            who = 'someone'

        bot.reply("You have to actually challenge {}, smh.".format(who))
        return plugin.NOLIMIT

    spoils = util.get_last_waifu(bot, target, trigger.sender)
    if not spoils:
        bot.reply(
            "Sorry, {} has no recent waifu for you to fight over."
            .format(target)
        )
        return plugin.NOLIMIT

    winner = random.choice((challenger, target))
    if winner == challenger:
        util.clear_last_waifu(bot, target, trigger.sender)
        util.set_last_waifu(bot, spoils, challenger, trigger.sender)
        bot.say(
            "{} wins! {} is no longer {}'s waifu.".format(
                challenger, spoils, target,
            )
        )
    else:
        bot.say(
            "{} defeats {} and keeps {} as their waifu.".format(
                target, challenger, spoils,
            )
        )


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


@plugin.commands('addwaifu')
@plugin.output_prefix(OUTPUT_PREFIX)
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
@plugin.output_prefix(OUTPUT_PREFIX)
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
