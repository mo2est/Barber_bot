"""FSM-состояния пользовательских сценариев."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Шаги записи: услуга → мастер → дата → слот → подтверждение."""

    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_slot = State()
    confirming = State()


class AdminStates(StatesGroup):
    """Шаги создания блокировки времени (TimeOff) администратором."""

    timeoff_choosing_master = State()
    timeoff_entering_range = State()
