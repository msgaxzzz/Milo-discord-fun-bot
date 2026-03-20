from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from cogs.chat import COOLDOWN_RETENTION, Chat
from cogs.community import Community, SCHEDULE_BATCH_SIZE
from cogs.economy import Economy
from cogs.utility import REMINDER_BATCH_SIZE, Utility


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, query, params=()):
        self.executed.append((query, params))

    async def fetchall(self):
        return list(self.rows)


class FakeDB:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.cursor_instances = []
        self.commit_calls = 0

    def cursor(self):
        cursor = FakeCursor(self.rows)
        self.cursor_instances.append(cursor)
        return cursor

    async def commit(self):
        self.commit_calls += 1


@pytest.mark.asyncio
async def test_afk_listener_deduplicates_repeated_mentions():
    utility = Utility.__new__(Utility)
    utility.bot = SimpleNamespace()
    utility.afk_cache = {}
    utility.get_afk_status = AsyncMock(return_value=None)
    utility.clear_afk_status = AsyncMock()
    set_at = (discord.utils.utcnow() - timedelta(minutes=5)).isoformat()
    utility.get_many_afk_statuses = AsyncMock(return_value={42: ("Lunch", set_at)})

    mentioned_user = SimpleNamespace(id=42, bot=False, display_name="Casey")
    channel = SimpleNamespace(send=AsyncMock())
    message = SimpleNamespace(
        author=SimpleNamespace(id=100, bot=False),
        guild=SimpleNamespace(id=555),
        channel=channel,
        mentions=[mentioned_user, mentioned_user],
    )

    await Utility.afk_message_listener(utility, message)

    utility.get_many_afk_statuses.assert_awaited_once_with(555, [42])
    channel.send.assert_awaited_once()
    sent_text = channel.send.await_args.args[0]
    assert sent_text.count("Casey is AFK") == 1


@pytest.mark.asyncio
async def test_reminder_loop_queries_due_work_in_bounded_batches():
    utility = Utility.__new__(Utility)
    utility.bot = SimpleNamespace(db=FakeDB(), get_user=lambda user_id: None)

    await Utility.reminder_loop.coro(utility)

    cursor = utility.bot.db.cursor_instances[0]
    assert cursor.executed[0][1][1] == REMINDER_BATCH_SIZE


@pytest.mark.asyncio
async def test_schedule_loop_queries_due_work_in_bounded_batches():
    community = Community.__new__(Community)
    community.bot = SimpleNamespace(db=FakeDB())

    await Community.schedule_loop.coro(community)

    cursor = community.bot.db.cursor_instances[0]
    assert cursor.executed[0][1][1] == SCHEDULE_BATCH_SIZE


@pytest.mark.asyncio
async def test_chat_prune_cooldowns_removes_only_expired_entries():
    chat = Chat.__new__(Chat)
    now = discord.utils.utcnow()
    expired_key = (1, 1)
    fresh_key = (1, 2)
    chat.chat_cooldowns = {
        expired_key: now - COOLDOWN_RETENTION - timedelta(minutes=1),
        fresh_key: now - timedelta(minutes=5),
    }

    await Chat._prune_cooldowns.coro(chat)

    assert expired_key not in chat.chat_cooldowns
    assert fresh_key in chat.chat_cooldowns


def test_economy_guild_lock_is_scoped_per_guild():
    economy = Economy.__new__(Economy)
    economy._guild_locks = {}

    guild_one_lock = economy._guild_lock(1)
    same_guild_lock = economy._guild_lock(1)
    other_guild_lock = economy._guild_lock(2)

    assert guild_one_lock is same_guild_lock
    assert guild_one_lock is not other_guild_lock
