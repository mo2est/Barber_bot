"""
SQLAlchemy модели бота записи.

Соглашения:
- Все суммы хранятся в копейках (Integer), отображаются делением на 100.
- Все времена — в UTC. Конвертация в локальный пояс — на уровне отображения.
- Мастера и услуги "удаляются" через is_active=False (soft delete),
  чтобы не ломать ссылки в исторических бронях.
"""

from __future__ import annotations

from datetime import datetime, time
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""

    # Удобные timestamps, доступны во всех потомках через миксин
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Перечисления
# ─────────────────────────────────────────────────────────────────────────────


class BookingStatus(StrEnum):
    """Статусы брони."""

    ACTIVE = "active"           # запланирована, ещё не прошла
    COMPLETED = "completed"     # клиент пришёл, услуга оказана
    CANCELLED_CLIENT = "cancelled_client"   # отменена клиентом
    CANCELLED_SALON = "cancelled_salon"     # отменена салоном
    NO_SHOW = "no_show"         # клиент не пришёл


class Weekday(StrEnum):
    """Дни недели для шаблона рабочих часов."""

    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


# ─────────────────────────────────────────────────────────────────────────────
# Основные сущности
# ─────────────────────────────────────────────────────────────────────────────


class Salon(Base):
    """Заведение (точка). Пока одна, но идентификатор закладываем под мультитенант."""

    __tablename__ = "salons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow", nullable=False)

    masters: Mapped[list["Master"]] = relationship(back_populates="salon")
    services: Mapped[list["Service"]] = relationship(back_populates="salon")

    def __repr__(self) -> str:
        return f"<Salon id={self.id} name={self.name!r}>"


class Master(Base):
    """Мастер салона."""

    __tablename__ = "masters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    salon_id: Mapped[int] = mapped_column(ForeignKey("salons.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    salon: Mapped[Salon] = relationship(back_populates="masters")
    services: Mapped[list["MasterService"]] = relationship(
        back_populates="master", cascade="all, delete-orphan"
    )
    working_hours: Mapped[list["WorkingHours"]] = relationship(
        back_populates="master", cascade="all, delete-orphan"
    )
    time_off: Mapped[list["TimeOff"]] = relationship(
        back_populates="master", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="master")

    def __repr__(self) -> str:
        return f"<Master id={self.id} name={self.name!r}>"


class Service(Base):
    """Услуга салона: название, длительность, базовая цена."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    salon_id: Mapped[int] = mapped_column(ForeignKey("salons.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Длительность в минутах. Должна быть кратна шагу сетки слотов (15 минут).
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Базовая цена в копейках. У конкретного мастера может быть своя — см. MasterService.
    base_price_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    salon: Mapped[Salon] = relationship(back_populates="services")
    masters: Mapped[list["MasterService"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name!r} duration={self.duration_minutes}>"


class MasterService(Base):
    """Связь мастер↔услуга: какие услуги делает мастер.

    Может переопределять цену и длительность под конкретного мастера
    (старший барбер делает дольше и дороже).
    """

    __tablename__ = "master_services"
    __table_args__ = (UniqueConstraint("master_id", "service_id", name="uq_master_service"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)

    # Если None — используется базовое значение из Service.
    price_override_kopecks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_override_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    master: Mapped[Master] = relationship(back_populates="services")
    service: Mapped[Service] = relationship(back_populates="masters")

    @property
    def effective_price_kopecks(self) -> int:
        """Финальная цена с учётом override."""
        return self.price_override_kopecks or self.service.base_price_kopecks

    @property
    def effective_duration_minutes(self) -> int:
        """Финальная длительность с учётом override."""
        return self.duration_override_minutes or self.service.duration_minutes


class WorkingHours(Base):
    """Шаблон рабочих часов мастера по дням недели.

    Пример: Иван — Пн-Пт 10:00-20:00, Сб 11:00-18:00, Вс выходной (нет записи).
    """

    __tablename__ = "working_hours"
    __table_args__ = (
        UniqueConstraint("master_id", "weekday", name="uq_master_weekday"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False)

    weekday: Mapped[Weekday] = mapped_column(String(3), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    master: Mapped[Master] = relationship(back_populates="working_hours")


class TimeOff(Base):
    """Исключения из рабочих часов: отпуск, выходной, обед.

    Перекрывает WorkingHours на указанный интервал.
    """

    __tablename__ = "time_off"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False)

    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # UTC
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)    # UTC
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    master: Mapped[Master] = relationship(back_populates="time_off")


# ─────────────────────────────────────────────────────────────────────────────
# Клиент и брони
# ─────────────────────────────────────────────────────────────────────────────


class Client(Base):
    """Клиент бота. Идентификатор — Telegram ID."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Telegram ID может быть большим (8 байт)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # +79991234567

    bookings: Mapped[list["Booking"]] = relationship(back_populates="client")

    def __repr__(self) -> str:
        return f"<Client id={self.id} tg={self.telegram_id} name={self.first_name!r}>"


class Booking(Base):
    """Запись клиента к мастеру на услугу в конкретное время.

    Частичный уникальный индекс на (master_id, start_at) среди активных
    броней — последняя линия защиты от дублей при гонке двух кликов
    "Подтвердить" почти одновременно (логическая проверка overlap в
    хендлере её не покрывает, т.к. между SELECT и INSERT есть окно).
    Отменённые/прошедшие брони из индекса исключены, поэтому слот можно
    переиспользовать после отмены.
    """

    __tablename__ = "bookings"
    __table_args__ = (
        Index(
            "uq_active_master_slot",
            "master_id",
            "start_at",
            unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)

    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # UTC
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)    # UTC

    # Зафиксированная на момент бронирования цена в копейках.
    # Чтобы изменение прайса задним числом не ломало историю.
    price_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[BookingStatus] = mapped_column(
        String(32), default=BookingStatus.ACTIVE, nullable=False
    )

    # ID задачи в APScheduler, чтобы можно было её отменить при отмене брони
    reminder_job_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    client: Mapped[Client] = relationship(back_populates="bookings")
    master: Mapped[Master] = relationship(back_populates="bookings")
    service: Mapped[Service] = relationship()

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} client={self.client_id} "
            f"master={self.master_id} start={self.start_at}>"
        )
