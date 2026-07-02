"""CallbackData-фабрики для инлайн-клавиатур."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class ServiceCb(CallbackData, prefix="svc"):
    service_id: int


class MasterCb(CallbackData, prefix="mst"):
    master_id: int


class DateCb(CallbackData, prefix="dt"):
    date_iso: str  # YYYY-MM-DD


class SlotCb(CallbackData, prefix="slt"):
    start_ts: int  # Unix timestamp UTC


class ConfirmCb(CallbackData, prefix="cnf"):
    action: str  # "yes" | "no"


class CancelBookingCb(CallbackData, prefix="cancel_bk"):
    booking_id: int


class BookingNavCb(CallbackData, prefix="bk_nav"):
    action: str  # "back_to_services" | "back_to_masters" | "back_to_dates"


# ── Админ-панель ─────────────────────────────────────────────────────────────


class AdminMenuCb(CallbackData, prefix="adm_menu"):
    action: str  # "today" | "masters" | "services" | "timeoff"


class AdminToggleMasterCb(CallbackData, prefix="adm_tg_mst"):
    master_id: int


class AdminToggleServiceCb(CallbackData, prefix="adm_tg_svc"):
    service_id: int


class AdminTimeoffMasterCb(CallbackData, prefix="adm_to_mst"):
    master_id: int


class AdminDeleteTimeoffCb(CallbackData, prefix="adm_to_del"):
    timeoff_id: int
