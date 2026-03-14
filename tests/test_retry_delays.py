from datetime import timedelta

from cogs.community import Community, SCHEDULE_RETRY_MAX_SECONDS
from cogs.utility import REMINDER_RETRY_MAX_SECONDS, Utility


def test_reminder_retry_delay_grows_and_caps():
    utility = Utility.__new__(Utility)

    assert utility.reminder_retry_delay(1) == timedelta(minutes=5)
    assert utility.reminder_retry_delay(2) == timedelta(minutes=10)
    assert utility.reminder_retry_delay(3) == timedelta(minutes=20)
    assert utility.reminder_retry_delay(99) == timedelta(seconds=REMINDER_RETRY_MAX_SECONDS)


def test_schedule_retry_delay_grows_and_caps():
    community = Community.__new__(Community)

    assert community.schedule_retry_delay(1) == timedelta(minutes=5)
    assert community.schedule_retry_delay(2) == timedelta(minutes=10)
    assert community.schedule_retry_delay(3) == timedelta(minutes=20)
    assert community.schedule_retry_delay(99) == timedelta(seconds=SCHEDULE_RETRY_MAX_SECONDS)
