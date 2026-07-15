# -*- coding: utf-8 -*-
"""To'liq inline admin panel."""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import db
import keyboards as kb

admin_router = Router()

# Admin Telegram ID'lari
# Bir nechta admin bo'lsa: ADMIN_IDS = [123456789, 987654321]
ADMIN_IDS = [8390029745]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    adding_route_title = State()
    adding_route_price = State()
    adding_route_category = State()
    editing_price = State()
    broadcasting = State()
    setting_group = State()
    setting_card = State()
    rejecting_order = State()


# ============================================================
# /admin — kirish
# ============================================================
@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Sizda admin huquqi yo'q.")
        return
    await state.clear()
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=kb.admin_main_menu())


@admin_router.message(Command("groupid"))
async def cmd_groupid(message: Message):
    await message.answer(f"🆔 Ushbu chat ID: <code>{message.chat.id}</code>")


@admin_router.callback_query(F.data == "adm:home")
async def adm_home(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.clear()
    await callback.message.edit_text("🛠 <b>Admin panel</b>", reply_markup=kb.admin_main_menu())
    await callback.answer()


# ============================================================
# STATISTIKA
# ============================================================
@admin_router.callback_query(F.data == "adm:stats")
async def adm_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    users = await db.count_users()
    orders_today = await db.count_orders_today()
    orders_total = await db.count_orders_total()
    drivers = await db.count_drivers()
    revenue_today = await db.sum_revenue_today()
    top = await db.top_routes(5)

    top_text = "\n".join(f"  • {r} — {c} ta" for r, c in top) or "  ma'lumot yo'q"
    revenue_str = f"{revenue_today:,}".replace(",", " ")

    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users}</b>\n"
        f"🚗 Faol haydovchilar: <b>{drivers}</b>\n"
        f"🧾 Bugungi buyurtmalar: <b>{orders_today}</b>\n"
        f"📦 Jami buyurtmalar: <b>{orders_total}</b>\n"
        f"💰 Bugungi (tasdiqlangan) tushum: <b>{revenue_str} so'm</b>\n\n"
        f"🔝 Eng ko'p buyurtma qilingan yo'nalishlar:\n{top_text}"
    )
    await callback.message.edit_text(text, reply_markup=kb.back_button())
    await callback.answer()


# ============================================================
# KUTILAYOTGAN BUYURTMALAR (admin tasdiqlashi kerak)
# ============================================================
@admin_router.callback_query(F.data == "adm:pending")
async def adm_pending(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    orders = await db.get_pending_orders()
    if not orders:
        await callback.message.edit_text(
            "🧾 Hozircha tasdiqlanishi kerak bo'lgan buyurtma yo'q.",
            reply_markup=kb.back_button(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🧾 Kutilayotgan buyurtmalar: {len(orders)} ta.\nHar biri alohida xabarda yuboriladi 👇",
        reply_markup=kb.back_button(),
    )
    for oid, name, route, phone, created in orders:
        time_str = created.split("T")[1][:5] if "T" in created else created
        await callback.message.answer(
            f"🆕 <b>#{oid}</b> — {name}\n{route}\n📞 {phone} • {time_str}",
            reply_markup=kb.order_admin_approve_kb(oid),
        )
    await callback.answer()


# ============================================================
# SO'NGGI BUYURTMALAR
# ============================================================
@admin_router.callback_query(F.data == "adm:orders")
async def adm_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    orders = await db.get_recent_orders(10)
    if not orders:
        text = "📜 Buyurtmalar hali yo'q."
    else:
        status_map = {
            "pending_admin": "⏳ Kutilmoqda",
            "approved": "✅ Tasdiqlangan",
            "rejected": "❌ Rad etilgan",
            "accepted": "🚗 Haydovchi oldi",
        }
        lines = ["📜 <b>So'nggi 10 ta buyurtma</b>\n"]
        for oid, name, route, phone, status, created in orders:
            st = status_map.get(status, status)
            time_str = created.split("T")[1][:5] if "T" in created else created
            lines.append(f"#{oid} {st}\n{name} — {route}\n📞 {phone} • {time_str}")
        text = "\n\n".join(lines)
    await callback.message.edit_text(text, reply_markup=kb.back_button())
    await callback.answer()


# ============================================================
# BUYURTMANI TASDIQLASH / RAD ETISH
# ============================================================
@admin_router.callback_query(F.data.startswith("ord_ok:"))
async def order_approve(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    # order columns: id,user_id,full_name,username,route,category,price,passengers,
    # is_cargo,phone,lat,lon,pay_method,pay_proof_file_id,status,driver_id,created_at
    (oid, user_id, full_name, username, route, category, price, passengers,
     is_cargo, phone, lat, lon, pay_method, pay_proof, status, driver_id, created_at) = order

    if status != "pending_admin":
        await callback.answer("Bu buyurtma allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await db.set_order_status(order_id, "approved")

    who = "📦 Pochta" if is_cargo else f"👥 Yo'lovchilar: {passengers}"
    price_str = f"{price:,}".replace(",", " ") if price else "0"
    order_text = (
        f"🆕 <b>Yangi buyurtma #{order_id}</b>\n\n"
        f"🚖 Yo'nalish: {route}\n"
        f"{who}\n"
        f"💰 Narx: {price_str} so'm\n"
        f"💳 To'lov: {pay_method}\n"
        f"📞 Telefon: {phone}\n"
        f"👤 Mijoz: {full_name} (@{username or 'yoq'})\n"
        f"🕒 Vaqt: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
    )

    group_key = "group_city" if category == "city" else "group_intercity"
    group_id = await db.get_setting(group_key)

    if group_id:
        try:
            await bot.send_message(int(group_id), order_text, reply_markup=kb.order_accept_kb(order_id))
            await bot.send_location(int(group_id), latitude=lat, longitude=lon)
        except Exception as e:
            await callback.message.answer(f"⚠️ Guruhga yuborishda xatolik: {e}")
    else:
        await callback.message.answer(
            f"⚠️ {'Shahar' if category=='city' else 'Viloyatlararo'} guruhi hali sozlanmagan. "
            f"Sozlamalar bo'limidan guruh ID ni kiriting."
        )

    driver_ids = await db.get_active_driver_ids()
    for did in driver_ids:
        try:
            await bot.send_message(did, order_text, reply_markup=kb.order_accept_kb(order_id))
            await bot.send_location(did, latitude=lat, longitude=lon)
        except Exception:
            pass

    try:
        await bot.send_message(user_id, "✅ Buyurtmangiz admin tomonidan tasdiqlandi! Tez orada haydovchi topiladi.")
    except Exception:
        pass

    await callback.message.edit_text(callback.message.text + "\n\n✅ <b>Tasdiqlandi</b>")
    await callback.answer("Tasdiqlandi ✅")


@admin_router.callback_query(F.data.startswith("ord_no:"))
async def order_reject(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    if order[14] != "pending_admin":
        await callback.answer("Bu buyurtma allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    await db.set_order_status(order_id, "rejected")
    try:
        await bot.send_message(
            order[1],
            "❌ Kechirasiz, buyurtmangiz rad etildi. Savol bo'lsa qo'llab-quvvatlashga murojaat qiling.",
        )
    except Exception:
        pass
    await callback.message.edit_text(callback.message.text + "\n\n❌ <b>Rad etildi</b>")
    await callback.answer("Rad etildi")


# ============================================================
# YO'NALISHLAR / NARXLAR
# ============================================================
@admin_router.callback_query(F.data == "adm:routes")
async def adm_routes_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await callback.message.edit_text(
        "🗺 <b>Yo'nalishlar / Narxlar</b>\n\nKategoriyani tanlang:",
        reply_markup=kb.routes_category_menu(),
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adm:routes_cat:"))
async def adm_routes_by_cat(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    category = callback.data.split(":")[2]
    all_routes = await db.get_all_routes()
    routes = [r for r in all_routes if r[3] == category]
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for rid, title, price, cat, active in routes:
        mark = "🔔" if active else "🔕"
        price_str = f"{price:,}".replace(",", " ") if price else "0"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {title} — {price_str} so'm",
            callback_data=f"adm:route:{rid}:{category}",
        )])
    rows.append([InlineKeyboardButton(text="➕ Yangi yo'nalish", callback_data="adm:route_add")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:routes")])
    cat_title = "🏙 Shahar ichida" if category == "city" else "🛣 Viloyatlararo"
    text = f"{cat_title}\n\nBoshqarish uchun tanlang:" if routes else f"{cat_title}\n\nHozircha yo'nalish yo'q."
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adm:route:"))
async def adm_route_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    _, _, rid, back_to = callback.data.split(":")
    rid = int(rid)
    route = await db.get_route(rid)
    if not route:
        await callback.answer("Topilmadi", show_alert=True)
        return
    _, title, price, category, active = route
    status_text = "Faol 🔔" if active else "O'chirilgan 🔕"
    price_str = f"{price:,}".replace(",", " ") if price else "0"
    await callback.message.edit_text(
        f"🗺 <b>{title}</b>\n\nHolati: {status_text}\n💰 Narx: {price_str} so'm",
        reply_markup=kb.route_detail_kb(rid, bool(active), back_to),
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adm:route_toggle:"))
async def adm_route_toggle(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    _, _, rid, back_to = callback.data.split(":")
    await db.toggle_route(int(rid))
    await callback.answer("Holat o'zgartirildi ✅")
    callback.data = f"adm:route:{rid}:{back_to}"
    await adm_route_detail(callback)


@admin_router.callback_query(F.data.startswith("adm:route_del:"))
async def adm_route_del(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    _, _, rid, back_to = callback.data.split(":")
    await db.delete_route(int(rid))
    await callback.answer("O'chirildi 🗑")
    callback.data = f"adm:routes_cat:{back_to}"
    await adm_routes_by_cat(callback)


@admin_router.callback_query(F.data == "adm:route_add")
async def adm_route_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminStates.adding_route_title)
    await callback.message.edit_text(
        "➕ Yangi yo'nalish nomini yuboring.\nMasalan: 🚖 Toshkentdan -> Samarqandga",
        reply_markup=kb.back_button("adm:routes"),
    )
    await callback.answer()


@admin_router.message(AdminStates.adding_route_title)
async def adm_route_add_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(new_title=message.text)
    await state.set_state(AdminStates.adding_route_price)
    await message.answer("💰 Narxini kiriting (faqat raqam, so'mda):")


@admin_router.message(AdminStates.adding_route_price)
async def adm_route_add_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        price = int("".join(ch for ch in message.text if ch.isdigit()) or "0")
    except ValueError:
        price = 0
    await state.update_data(new_price=price)
    await state.set_state(AdminStates.adding_route_category)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb_cat = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏙 Shahar ichida", callback_data="newroute_cat:city")],
            [InlineKeyboardButton(text="🛣 Viloyatlararo", callback_data="newroute_cat:intercity")],
        ]
    )
    await message.answer("Qaysi toifaga tegishli?", reply_markup=kb_cat)


@admin_router.callback_query(AdminStates.adding_route_category, F.data.startswith("newroute_cat:"))
async def adm_route_add_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    category = callback.data.split(":")[1]
    data = await state.get_data()
    await db.add_route(data["new_title"], data["new_price"], category)
    await state.clear()
    await callback.message.edit_text("✅ Yo'nalish qo'shildi.", reply_markup=kb.admin_main_menu())
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adm:route_price:"))
async def adm_route_price_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    _, _, rid, back_to = callback.data.split(":")
    await state.update_data(editing_route_id=int(rid), editing_back_to=back_to)
    await state.set_state(AdminStates.editing_price)
    await callback.message.edit_text(
        "💰 Yangi narxni kiriting (faqat raqam, so'mda):",
        reply_markup=kb.back_button(f"adm:route:{rid}:{back_to}"),
    )
    await callback.answer()


@admin_router.message(AdminStates.editing_price)
async def adm_route_price_set(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    rid = data.get("editing_route_id")
    try:
        price = int("".join(ch for ch in message.text if ch.isdigit()) or "0")
    except ValueError:
        await message.answer("Iltimos faqat raqam kiriting.")
        return
    await db.set_route_price(rid, price)
    await state.clear()
    await message.answer("✅ Narx yangilandi.", reply_markup=kb.admin_main_menu())


# ============================================================
# HAYDOVCHILAR
# ============================================================
@admin_router.callback_query(F.data == "adm:drivers")
async def adm_drivers(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    drivers = await db.get_drivers()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for did, uid, name, username, phone, car, status in drivers:
        rows.append([InlineKeyboardButton(text=f"🚗 {name} ({phone or 'tel yoq'})", callback_data=f"adm:driver:{did}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:home")])
    text = "🚗 <b>Faol haydovchilar</b>" if drivers else "🚗 <b>Faol haydovchilar</b>\n\nHozircha hech kim yo'q."
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adm:driver:"))
async def adm_driver_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    did = int(callback.data.split(":")[2])
    drivers = await db.get_drivers()
    d = next((x for x in drivers if x[0] == did), None)
    if not d:
        await callback.answer("Topilmadi", show_alert=True)
        return
    _, uid, name, username, phone, car, status = d
    await callback.message.edit_text(
        f"🚗 <b>{name}</b>\n@{username or 'yoq'}\n📞 {phone or 'kiritilmagan'}\n"
        f"🚘 Mashina: {car or 'kiritilmagan'}\nID: <code>{uid}</code>",
        reply_markup=kb.driver_detail_kb(did),
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adm:driver_del:"))
async def adm_driver_del(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    did = int(callback.data.split(":")[2])
    await db.remove_driver(did)
    await callback.answer("O'chirildi 🗑")
    await adm_drivers(callback)


# ============================================================
# HAYDOVCHI SO'ROVLARI (yangi arizalar)
# ============================================================
@admin_router.callback_query(F.data == "adm:drv_requests")
async def adm_drv_requests(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    reqs = await db.get_pending_driver_requests()
    if not reqs:
        await callback.message.edit_text(
            "🆕 Hozircha yangi haydovchi so'rovlari yo'q.", reply_markup=kb.back_button()
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"🆕 Kutilayotgan so'rovlar: {len(reqs)} ta 👇", reply_markup=kb.back_button()
    )
    for rid, name, phone, car, created in reqs:
        await callback.message.answer(
            f"🧑\u200d✈️ <b>{name}</b>\n📞 {phone}\n🚘 {car or 'kiritilmagan'}",
            reply_markup=kb.driver_request_admin_kb(rid),
        )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("drv_ok:"))
async def drv_request_approve(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    req_id = int(callback.data.split(":")[1])
    req = await db.get_driver_request(req_id)
    if not req:
        await callback.answer("Topilmadi", show_alert=True)
        return
    _, user_id, full_name, username, phone, car, status, created_at = req
    if status != "pending":
        await callback.answer("Allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    await db.add_driver(user_id, full_name, username, phone, car)
    await db.set_driver_request_status(req_id, "approved")
    try:
        await bot.send_message(user_id, "✅ Tabriklaymiz! Haydovchi sifatida tasdiqlandingiz. Endi buyurtmalarni qabul qila olasiz.")
    except Exception:
        pass
    await callback.message.edit_text(callback.message.text + "\n\n✅ <b>Tasdiqlandi</b>")
    await callback.answer("Tasdiqlandi ✅")


@admin_router.callback_query(F.data.startswith("drv_no:"))
async def drv_request_reject(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    req_id = int(callback.data.split(":")[1])
    req = await db.get_driver_request(req_id)
    if not req:
        await callback.answer("Topilmadi", show_alert=True)
        return
    if req[6] != "pending":
        await callback.answer("Allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    await db.set_driver_request_status(req_id, "rejected")
    try:
        await bot.send_message(req[1], "❌ Kechirasiz, haydovchilik so'rovingiz rad etildi.")
    except Exception:
        pass
    await callback.message.edit_text(callback.message.text + "\n\n❌ <b>Rad etildi</b>")
    await callback.answer("Rad etildi")


# ============================================================
# XABAR TARQATISH (BROADCAST)
# ============================================================
@admin_router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminStates.broadcasting)
    await callback.message.edit_text(
        "📢 Barcha foydalanuvchilarga yuboriladigan xabarni (matn/rasm/video) yuboring:",
        reply_markup=kb.back_button("adm:home"),
    )
    await callback.answer()


@admin_router.message(AdminStates.broadcasting)
async def adm_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    user_ids = await db.get_all_user_ids()
    await state.clear()
    sent, failed = 0, 0
    status_msg = await message.answer(f"⏳ Yuborilmoqda... 0/{len(user_ids)}")
    for i, uid in enumerate(user_ids, 1):
        try:
            await bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
        if i % 20 == 0:
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... {i}/{len(user_ids)}")
            except Exception:
                pass
        await asyncio.sleep(0.05)
    await status_msg.edit_text(
        f"✅ Xabar tarqatish yakunlandi!\n\n📤 Yuborildi: {sent}\n❌ Xatolik: {failed}",
        reply_markup=kb.admin_main_menu(),
    )


# ============================================================
# SOZLAMALAR — guruh ID va karta raqami
# ============================================================
@admin_router.callback_query(F.data == "adm:settings")
async def adm_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    city_group = await db.get_setting("group_city", "o'rnatilmagan")
    inter_group = await db.get_setting("group_intercity", "o'rnatilmagan")
    card = await db.get_setting("card_number", "o'rnatilmagan")
    text = (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"🏙 Shahar guruhi ID: <code>{city_group}</code>\n"
        f"🛣 Viloyatlararo guruh ID: <code>{inter_group}</code>\n"
        f"💳 Karta raqami: <code>{card}</code>\n\n"
        "Guruh ID sini bilish uchun botni guruhga admin qilib qo'shing va o'sha guruhda "
        "<code>/groupid</code> buyrug'ini yuboring."
    )
    await callback.message.edit_text(text, reply_markup=kb.settings_menu_kb())
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adm:set_group:"))
async def adm_set_group_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    group_type = callback.data.split(":")[2]
    await state.update_data(setting_group_type=group_type)
    await state.set_state(AdminStates.setting_group)
    label = "Shahar" if group_type == "city" else "Viloyatlararo"
    await callback.message.edit_text(
        f"🆔 {label} guruhining chat ID sini yuboring.\n"
        f"(Manfiy raqam bo'ladi, masalan: -1001234567890)\n\n"
        f"Guruhda <code>/groupid</code> buyrug'ini yozib, ID ni bilib olishingiz mumkin.",
        reply_markup=kb.back_button("adm:settings"),
    )
    await callback.answer()


@admin_router.message(AdminStates.setting_group)
async def adm_set_group_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    group_type = data.get("setting_group_type")
    text = message.text.strip()
    try:
        int(text)
    except ValueError:
        await message.answer("Iltimos, faqat raqam (chat ID) yuboring.")
        return
    key = "group_city" if group_type == "city" else "group_intercity"
    await db.set_setting(key, text)
    await state.clear()
    await message.answer("✅ Guruh ID saqlandi.", reply_markup=kb.admin_main_menu())


@admin_router.callback_query(F.data == "adm:set_card")
async def adm_set_card_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminStates.setting_card)
    await callback.message.edit_text(
        "💳 Karta raqamini yuboring (mijozlarga to'lov uchun ko'rsatiladi):",
        reply_markup=kb.back_button("adm:settings"),
    )
    await callback.answer()


@admin_router.message(AdminStates.setting_card)
async def adm_set_card_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await db.set_setting("card_number", message.text.strip())
    await state.clear()
    await message.answer("✅ Karta raqami saqlandi.", reply_markup=kb.admin_main_menu())
