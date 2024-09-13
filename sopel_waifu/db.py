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
    nemesis = Column(String(255))


class WaifuDB:
    """Plugin-specific database object class.

    Methods for mutating waifu-related data need to live *somewhere*. 🤷‍♂️
    """

    def __init__(self, bot):
        self.db = bot.db
        BASE.metadata.create_all(self.db.engine)

    def set_waifu(self, nick, channel, waifu, commit=True):
        """Record that ``nick`` got ``waifu`` in ``channel``."""
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
                result.nemesis = None
            # nick+channel combo not known; create it
            else:
                new_stats = FightStats(
                    nick_id=nick_id,
                    channel=channel_slug,
                    waifu=waifu,
                    nemesis=None,
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

    def set_nemesis(self, nick, channel, nemesis, commit=True):
        """Record ``nick``'s ``nemesis`` in ``channel``."""
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
                result.waifu = None
                result.nemesis = nemesis
            # nick+channel combo not known; create it
            else:
                new_stats = FightStats(
                    nick_id=nick_id,
                    channel=channel_slug,
                    waifu=None,
                    nemesis=nemesis,
                )
                session.add(new_stats)

            # whether it's created or just updated, commit the thing
            session.commit()

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
                select(FightStats.nemesis)
                .where(FightStats.nick_id == nick_id)
                .where(FightStats.channel == channel_slug)
            ).scalar_one_or_none()

            return result

    def steal_waifu(self, victim, nemesis, channel):
        """Record that ``thief`` stole ``victim``'s waifu in ``channel``."""
        waifu = self.get_waifu(victim, channel)
        if waifu is None:
            raise errors.NoWaifuError(victim, channel)

        # Would ideally like these two operations to be a single atomic
        # operation, but either sqlalchemy doesn't make it easy, or I'm too
        # stupid to figure out how to structure it.
        self.set_waifu(nemesis, channel, waifu)
        self.set_nemesis(victim, channel, nemesis)
