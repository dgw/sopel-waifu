"""sopel-waifu database submodule

Part of sopel-waifu. Copyright 2024 dgw, technobabbl.es
"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import select, update

from sopel.db import BASE, MYSQL_TABLE_ARGS

from .errors import NoWaifuError


class FightStats(BASE):
    """Waifu fight stats table SQLAlchemy class."""
    __tablename__ = 'waifu_fight_stats'
    __table_args__ = MYSQL_TABLE_ARGS
    nick_id = Column(Integer, ForeignKey('nick_ids.nick_id'), primary_key=True)
    channel = Column(String(255), primary_key=True)
    waifu = Column(String(255))
    prev_owner_id = Column(Integer, ForeignKey('nick_ids.nick_id'))
    nemesis = Column(String(255))


class WaifuDB:
    """Plugin-specific database object class.

    Methods for mutating waifu-related data need to live *somewhere*. 🤷‍♂️
    """

    def __init__(self, bot):
        self.db = bot.db
        BASE.metadata.create_all(self.db.engine)

    def set_waifu(
        self,
        nick,
        channel,
        waifu,
        prev_owner_id=None,
        nemesis=None,
    ):
        """Record that ``nick`` obtained ``waifu`` in ``channel``.

        Optional ``prev_owner_id`` should be given if ``nick`` *won* ``waifu``
        in a duel, to support checking for revenge during future duels.

        Optional ``nemesis`` should be given (with ``waifu=None``) if ``nick``
        *lost* their waifu in battle, so ``.lastwaifu`` can show who stole her.
        """
        nick_id = self.db.get_nick_id(nick, create=True)
        channel_slug = self.db.get_channel_slug(channel)

        with self.db.session() as session:
            result = session.execute(
                select(FightStats)
                .where(FightStats.nick_id == nick_id)
                .where(FightStats.channel == channel_slug)
            ).scalar_one_or_none()

            # nick+channel combo already known; update it
            if result:
                result.waifu = waifu
                result.prev_owner_id = prev_owner_id
                result.nemesis = nemesis
            # nick+channel combo not known; create it
            else:
                new_stats = FightStats(
                    nick_id=nick_id,
                    channel=channel_slug,
                    waifu=waifu,
                    prev_owner_id=prev_owner_id,
                    nemesis=nemesis,
                )
                session.add(new_stats)

            # whether it's created or just updated, commit the thing
            session.commit()

    def get_waifu(self, nick, channel):
        """Get ``nick``'s current waifu in ``channel``."""
        try:
            nick_id = self.db.get_nick_id(nick)
        except ValueError:
            # if they're not in the DB, they can't possibly have a waifu yet
            return None

        channel_slug = self.db.get_channel_slug(channel)

        with self.db.session() as session:
            result = session.execute(
                select(FightStats.waifu)
                .where(FightStats.nick_id == nick_id)
                .where(FightStats.channel == channel_slug)
            ).scalar_one_or_none()

            return result

    def clear_waifu(self, nick, channel, thief=None):
        """Clear ``nick``'s waifu in ``channel``.

        They must have just lost a ``.wifight`` duel. Tough break.
        """
        self.set_waifu(nick, channel, None, nemesis=thief)

    def get_prev_owner_id(self, nick, channel):
        """Get who previously owned ``nick``'s waifu in ``channel``.

        Only set if ``nick`` won their current waifu in a ``.wifight`` duel.
        """
        try:
            nick_id = self.db.get_nick_id(nick)
        except ValueError:
            # if they're not in the DB, they can't have stolen a waifu yet
            return None

        channel_slug = self.db.get_channel_slug(channel)

        with self.db.session() as session:
            result = session.execute(
                select(FightStats.prev_owner_id)
                .where(FightStats.nick_id == nick_id)
                .where(FightStats.channel == channel_slug)
            ).scalar_one_or_none()

            return result

    def prev_owner_matches(self, nick, channel, who):
        """Was the previous owner of ``nick``'s waifu in ``channel`` ``who``?"""
        return self.get_prev_owner_id(nick, channel) == self.db.get_nick_id(who)

    def get_nemesis(self, nick, channel):
        """Get ``nick``'s nemesis in ``channel``.

        That is, if they don't have a waifu, who stole her?
        """
        try:
            nick_id = self.db.get_nick_id(nick)
        except ValueError:
            # if they're not in the DB, they can't have a nemesis yet
            return None

        channel_slug = self.db.get_channel_slug(channel)

        with self.db.session() as session:
            result = session.execute(
                select(FightStats.waifu, FightStats.nemesis)
                .where(FightStats.nick_id == nick_id)
                .where(FightStats.channel == channel_slug)
            ).one_or_none()

            if result.waifu:
                return None
            return result.nemesis

    def steal_waifu(self, thief, channel, victim):
        """Record that ``thief`` stole ``victim``'s waifu in ``channel``."""
        if (spoils := self.get_waifu(victim, channel)) is None:
            raise NoWaifuError(victim, channel)

        # Would ideally like these two updates to be a single atomic operation,
        # but either sqlalchemy doesn't make it easy, or I'm too stupid to
        # figure out how to structure it.
        self.set_waifu(thief, channel, spoils, self.db.get_nick_id(victim))
        self.clear_waifu(victim, channel, thief=thief)
