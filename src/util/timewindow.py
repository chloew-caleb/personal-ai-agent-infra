"""Timezone-safe query windows.

Health and activity queries were initially written with a fixed offset.
When the user moved between Shanghai and New York, "last night" pointed at
the wrong twelve hours. Windows are now built in the user's current zone
(read from configuration, never hard-coded) and converted to UTC only at
the boundary.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")


def last_night_window(user_tz: str, now_utc=None):
    """From 20:00 local yesterday to now, returned as UTC datetimes."""
    tz = ZoneInfo(user_tz)
    now_local = (now_utc or datetime.now(UTC)).astimezone(tz)
    start_local = datetime.combine(now_local.date() - timedelta(days=1), time(20, 0), tz)
    return start_local.astimezone(UTC), now_local.astimezone(UTC)


def local_label(ts_utc: datetime, user_tz: str) -> str:
    """Human-readable local time for a UTC timestamp, e.g. '2026-10-01 13:35 Thu'."""
    return ts_utc.astimezone(ZoneInfo(user_tz)).strftime("%Y-%m-%d %H:%M %a")


if __name__ == "__main__":
    now = datetime(2026, 10, 1, 17, 35, tzinfo=UTC)
    print(local_label(now, "America/New_York"), "|", local_label(now, "Asia/Shanghai"))
    print(last_night_window("America/New_York", now))
