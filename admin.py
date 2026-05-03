from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.config import get_settings
from app.db.models import Giveaway, GiveawayStatus, User
from app.db.session import session_scope
from app.jobs.scheduler import schedule_giveaway_finish
from app.keyboards import admin_auto_kb, admin_cancel_kb, admin_home_kb, admin_preview_kb
from app.services.gift_service import format_available_gifts
from app.services.giveaway_service import create_manual_giveaway, publish_manual_giveaway
from app.services.runtime import auto_drops_enabled, set_auto_drops_enabled
from app.services.user_service import ban_user
from app.texts import admin_home_text, create_preview_text
from app.utils.html import h

router = Router(name="admin")
settings = get_settings()


class GiveawayCreate(StatesGroup):
    title = State()
    prize = State()
    gift_id = State()
    winners = State()
    duration = State()
    description = State()
    photo = State()
    preview = State()


def is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


async def deny(message_or_callback: Message | CallbackQuery) -> None:
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer("Не админ.", show_alert=True)
    else:
        await message_or_callback.answer("Не админ.")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await deny(message)
        return
    await message.answer(admin_home_text(), reply_markup=admin_home_kb(auto_drops_enabled()), parse_mode="HTML")


@router.callback_query(F.data == "admin:home")
async def cb_admin_home(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    await state.clear()
    await callback.message.edit_text(admin_home_text(), reply_markup=admin_home_kb(auto_drops_enabled()), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:close")
async def cb_admin_close(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "admin:auto")
async def cb_admin_auto(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    enabled = auto_drops_enabled()
    text = (
        "<b>Авто-дропы</b>\n\n"
        f"Статус: <b>{'включены' if enabled else 'выключены'}</b>\n\n"
        "Авто-дроп создается под каждым новым постом канала, который попал в discussion-чат."
    )
    await callback.message.edit_text(text, reply_markup=admin_auto_kb(enabled), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:auto:toggle")
async def cb_admin_auto_toggle(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    new_value = not auto_drops_enabled()
    set_auto_drops_enabled(new_value)
    await callback.message.edit_text(
        f"<b>Авто-дропы</b>\n\nСтатус: <b>{'включены' if new_value else 'выключены'}</b>",
        reply_markup=admin_auto_kb(new_value),
        parse_mode="HTML",
    )
    await callback.answer("Готово")


@router.callback_query(F.data == "admin:create")
async def cb_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    await state.clear()
    await state.set_state(GiveawayCreate.title)
    await callback.message.edit_text(
        "<b>Новый розыгрыш</b>\n\nНапиши название.\n\nПример: <code>РОЗЫГРЫВАЮ 15 МИШЕК</code>",
        reply_markup=admin_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(GiveawayCreate.title)
async def create_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer("Название слишком короткое.")
        return
    await state.update_data(title=title[:256])
    await state.set_state(GiveawayCreate.prize)
    await message.answer("Теперь приз.\n\nПример: <code>15 мишек</code>", parse_mode="HTML", reply_markup=admin_cancel_kb())


@router.message(GiveawayCreate.prize)
async def create_prize(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    prize = (message.text or "").strip()
    if len(prize) < 2:
        await message.answer("Приз слишком короткий.")
        return
    await state.update_data(prize_name=prize[:256])
    await state.set_state(GiveawayCreate.gift_id)
    await message.answer(
        "Теперь <code>gift_id</code> для авто-отправки Telegram Gift.\n\n"
        "Напиши ID подарка или <code>-</code>, если выдашь руками.\n"
        "Список ID можно посмотреть командой /gifts.",
        parse_mode="HTML",
        reply_markup=admin_cancel_kb(),
    )


@router.message(GiveawayCreate.gift_id)
async def create_gift_id(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    raw = (message.text or "").strip()
    gift_id = None if raw in {"-", "нет", "skip"} else raw
    await state.update_data(gift_id=gift_id)
    await state.set_state(GiveawayCreate.winners)
    await message.answer("Сколько победителей?\n\nПример: <code>15</code>", parse_mode="HTML", reply_markup=admin_cancel_kb())


@router.message(GiveawayCreate.winners)
async def create_winners(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    try:
        winners = int((message.text or "").strip())
    except ValueError:
        await message.answer("Нужно число.")
        return
    if not 1 <= winners <= 100:
        await message.answer("Поставь от 1 до 100.")
        return
    await state.update_data(winners_count=winners)
    await state.set_state(GiveawayCreate.duration)
    await message.answer("Сколько минут идет розыгрыш?\n\nПример: <code>60</code>", parse_mode="HTML", reply_markup=admin_cancel_kb())


@router.message(GiveawayCreate.duration)
async def create_duration(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    try:
        duration = int((message.text or "").strip())
    except ValueError:
        await message.answer("Нужно число минут.")
        return
    if not 1 <= duration <= 10080:
        await message.answer("Поставь от 1 минуты до 7 дней.")
        return
    await state.update_data(duration_min=duration)
    await state.set_state(GiveawayCreate.description)
    await message.answer(
        "Напиши условия/описание.\n\n"
        "Например: <code>Подписка + кнопка. Победителей выберет бот.</code>\n\n"
        "Можно написать <code>-</code>, чтобы пропустить.",
        parse_mode="HTML",
        reply_markup=admin_cancel_kb(),
    )


@router.message(GiveawayCreate.description)
async def create_description(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    raw = (message.text or "").strip()
    description = None if raw in {"-", "нет", "skip"} else raw[:1500]
    await state.update_data(description=description)
    await state.set_state(GiveawayCreate.photo)
    await message.answer(
        "Теперь картинка для розыгрыша.\n\n"
        "Отправь фото или напиши <code>-</code>, чтобы пост был без фото.",
        parse_mode="HTML",
        reply_markup=admin_cancel_kb(),
    )


@router.message(GiveawayCreate.photo)
async def create_photo(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    image_file_id = None
    if message.photo:
        image_file_id = message.photo[-1].file_id
    else:
        raw = (message.text or "").strip()
        if raw not in {"-", "нет", "skip"}:
            await message.answer("Нужно фото или <code>-</code>.", parse_mode="HTML")
            return
    await state.update_data(image_file_id=image_file_id)
    data = await state.get_data()
    await state.set_state(GiveawayCreate.preview)
    await message.answer(
        create_preview_text(
            data["title"],
            data["prize_name"],
            data["winners_count"],
            data["duration_min"],
            data.get("description"),
            data.get("gift_id"),
        ),
        parse_mode="HTML",
        reply_markup=admin_preview_kb(),
    )


@router.callback_query(F.data == "admin:publish")
async def cb_publish(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    data = await state.get_data()
    required = {"title", "prize_name", "winners_count", "duration_min"}
    if not required.issubset(data):
        await callback.answer("Черновик пустой, создай заново.", show_alert=True)
        return

    async with session_scope() as session:
        giveaway = await create_manual_giveaway(
            session,
            settings,
            title=data["title"],
            description=data.get("description"),
            prize_name=data["prize_name"],
            gift_id=data.get("gift_id"),
            winners_count=int(data["winners_count"]),
            duration_minutes=int(data["duration_min"]),
            image_file_id=data.get("image_file_id"),
            created_by=callback.from_user.id,
        )
        await publish_manual_giveaway(callback.bot, session, settings, giveaway)
        schedule_giveaway_finish(giveaway.id, giveaway.ends_at)

    await state.clear()
    await callback.message.edit_text("Опубликовал. Розыгрыш запущен.", parse_mode="HTML")
    await callback.answer("Опубликовано")


@router.callback_query(F.data == "admin:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    await state.clear()
    await callback.message.edit_text("Отменил.", reply_markup=admin_home_kb(auto_drops_enabled()))
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await deny(message)
        return
    await state.clear()
    await message.answer("Отменил.")


@router.message(Command("gifts"))
async def cmd_gifts(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await deny(message)
        return
    await message.answer("Загружаю gifts...")
    text = await format_available_gifts(message.bot)
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin:gifts")
async def cb_gifts(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    await callback.answer("Загружаю")
    text = await format_available_gifts(callback.bot)
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin:stats")
async def cb_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await deny(callback)
        return
    async with session_scope() as session:
        users_count = int((await session.execute(select(func.count(User.id)))).scalar_one())
        giveaways_count = int((await session.execute(select(func.count(Giveaway.id)))).scalar_one())
        active_count = int((await session.execute(select(func.count(Giveaway.id)).where(Giveaway.status == GiveawayStatus.ACTIVE.value))).scalar_one())
    await callback.message.answer(
        "<b>Статистика</b>\n\n"
        f"Пользователей: <b>{users_count}</b>\n"
        f"Розыгрышей всего: <b>{giveaways_count}</b>\n"
        f"Активных: <b>{active_count}</b>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await deny(message)
        return
    if not command.args:
        await message.answer("Формат: /ban 123456789")
        return
    try:
        telegram_id = int(command.args.strip())
    except ValueError:
        await message.answer("Нужен numeric telegram_id.")
        return
    async with session_scope() as session:
        await ban_user(session, telegram_id, True)
    await message.answer(f"Забанил <code>{telegram_id}</code>.", parse_mode="HTML")


@router.message(Command("unban"))
async def cmd_unban(message: Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await deny(message)
        return
    if not command.args:
        await message.answer("Формат: /unban 123456789")
        return
    try:
        telegram_id = int(command.args.strip())
    except ValueError:
        await message.answer("Нужен numeric telegram_id.")
        return
    async with session_scope() as session:
        await ban_user(session, telegram_id, False)
    await message.answer(f"Разбанил <code>{telegram_id}</code>.", parse_mode="HTML")
