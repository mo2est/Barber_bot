"""Tests for keyboard builders (slot timestamp round-trip)."""

import datetime as dt

from bot.callbacks import SlotCb
from bot.keyboards.client import slots_kb


def test_slot_ts_round_trips_to_same_utc_time():
    """start_ts in callback must decode back to the exact UTC slot time.

    Naive datetime.timestamp() interprets the value in the OS local
    timezone, silently shifting the booked time by the server's UTC
    offset (regression: slot shown as 10:15 confirmed as 06:15).
    """
    slot_utc = dt.datetime(2026, 7, 6, 7, 0)  # naive UTC, as stored in DB
    kb = slots_kb([slot_utc], "Europe/Moscow")

    button = kb.inline_keyboard[0][0]
    assert button.text == "10:00"  # rendered in salon-local time

    cb = SlotCb.unpack(button.callback_data)
    decoded_utc = dt.datetime.fromtimestamp(
        cb.start_ts, tz=dt.timezone.utc
    ).replace(tzinfo=None)
    assert decoded_utc == slot_utc


def test_slot_ts_independent_of_slot_position():
    """Every slot in the list must round-trip, not just the first."""
    slots = [dt.datetime(2026, 7, 6, 7, 0) + dt.timedelta(minutes=15 * i) for i in range(8)]
    kb = slots_kb(slots, "Europe/Moscow")

    for row, expected in zip(kb.inline_keyboard, slots):
        cb = SlotCb.unpack(row[0].callback_data)
        decoded = dt.datetime.fromtimestamp(cb.start_ts, tz=dt.timezone.utc).replace(
            tzinfo=None
        )
        assert decoded == expected
