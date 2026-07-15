# -*- coding: utf-8 -*-
"""SQLite bilan ishlash uchun barcha funksiyalar."""

import aiosqlite
from datetime import datetime

DB_PATH = "taxibot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price INTEGER DEFAULT 0,
                category TEXT DEFAULT 'city',
                active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                full_name TEXT,
                username TEXT,
                route TEXT,
                category TEXT,
                price INTEGER DEFAULT 0,
                passengers TEXT,
                is_cargo INTEGER DEFAULT 0,
                phone TEXT,
                lat REAL,
                lon REAL,
                pay_method TEXT,
                pay_proof_file_id TEXT,
                status TEXT DEFAULT 'pending_admin',
                driver_id INTEGER,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                full_name TEXT,
                username TEXT,
                phone TEXT,
                car TEXT,
                status TEXT DEFAULT 'pending',
                added_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS driver_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                full_name TEXT,
                username TEXT,
                phone TEXT,
                car TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                first_seen TEXT,
                blocked INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

        cur = await db.execute("SELECT COUNT(*) FROM routes")
        (count,) = await cur.fetchone()
        if count == 0:
            defaults = [
                ("🚖 Toshkentdan -> Chiroqchiga", 150000, "intercity"),
                ("🚖 Chiroqchidan -> Toshkentga", 150000, "intercity"),
                ("🚖 Toshkentdan -> Ko'kdalaga", 100000, "intercity"),
                ("🚖 Ko'kdaladan -> Toshkentga", 100000, "intercity"),
                ("🚖 Chilonzor -> Yunusobod", 30000, "city"),
                ("🚖 Sergeli -> Mirzo Ulug'bek", 35000, "city"),
            ]
            await db.executemany(
                "INSERT INTO routes (title, price, category, active) VALUES (?, ?, ?, 1)",
                defaults,
            )
            await db.commit()


# --------------------------- SETTINGS ---------------------------------------
async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()


# --------------------------- USERS ---------------------------------------
async def upsert_user(user_id: int, full_name: str, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (user_id, full_name, username, first_seen, blocked)
               VALUES (?, ?, ?, ?, 0)
               ON CONFLICT(user_id) DO UPDATE SET full_name=excluded.full_name, username=excluded.username""",
            (user_id, full_name, username, datetime.now().isoformat()),
        )
        await db.commit()


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE blocked=0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def count_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        (c,) = await cur.fetchone()
        return c


# --------------------------- ROUTES ---------------------------------------
async def get_active_routes(category: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if category:
            cur = await db.execute(
                "SELECT id, title, price, category FROM routes WHERE active=1 AND category=? ORDER BY id",
                (category,),
            )
        else:
            cur = await db.execute(
                "SELECT id, title, price, category FROM routes WHERE active=1 ORDER BY id"
            )
        return await cur.fetchall()


async def get_all_routes():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, title, price, category, active FROM routes ORDER BY category, id"
        )
        return await cur.fetchall()


async def get_route(route_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, title, price, category, active FROM routes WHERE id=?", (route_id,)
        )
        return await cur.fetchone()


async def add_route(title: str, price: int, category: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO routes (title, price, category, active) VALUES (?, ?, ?, 1)",
            (title, price, category),
        )
        await db.commit()


async def toggle_route(route_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE routes SET active = 1 - active WHERE id=?", (route_id,)
        )
        await db.commit()


async def delete_route(route_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM routes WHERE id=?", (route_id,))
        await db.commit()


async def set_route_price(route_id: int, price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE routes SET price=? WHERE id=?", (price, route_id))
        await db.commit()


# --------------------------- ORDERS ----------------------------------------
async def create_order(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO orders
               (user_id, full_name, username, route, category, price, passengers, is_cargo,
                phone, lat, lon, pay_method, pay_proof_file_id, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_admin', ?)""",
            (
                data["user_id"],
                data["full_name"],
                data.get("username", ""),
                data["route"],
                data.get("category", "city"),
                data.get("price", 0),
                data.get("passengers"),
                int(data.get("is_cargo", False)),
                data["phone"],
                data["lat"],
                data["lon"],
                data.get("pay_method", "naqd"),
                data.get("pay_proof_file_id"),
                datetime.now().isoformat(),
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        return await cur.fetchone()


async def set_order_status(order_id: int, status: str, driver_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if driver_id is not None:
            await db.execute(
                "UPDATE orders SET status=?, driver_id=? WHERE id=?",
                (status, driver_id, order_id),
            )
        else:
            await db.execute(
                "UPDATE orders SET status=? WHERE id=?", (status, order_id)
            )
        await db.commit()


async def count_orders_today():
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().date().isoformat()
        cur = await db.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (f"{today}%",)
        )
        (c,) = await cur.fetchone()
        return c


async def count_orders_total():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM orders")
        (c,) = await cur.fetchone()
        return c


async def sum_revenue_today():
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().date().isoformat()
        cur = await db.execute(
            "SELECT COALESCE(SUM(price),0) FROM orders WHERE created_at LIKE ? AND status IN ('approved','accepted','done')",
            (f"{today}%",),
        )
        (s,) = await cur.fetchone()
        return s


async def get_recent_orders(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, full_name, route, phone, status, created_at FROM orders ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()


async def get_pending_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, full_name, route, phone, created_at FROM orders WHERE status='pending_admin' ORDER BY id"
        )
        return await cur.fetchall()


async def top_routes(limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT route, COUNT(*) as cnt FROM orders
               GROUP BY route ORDER BY cnt DESC LIMIT ?""",
            (limit,),
        )
        return await cur.fetchall()


# --------------------------- DRIVERS ---------------------------------------
async def add_driver(user_id: int, full_name: str, username: str, phone: str = "", car: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO drivers (user_id, full_name, username, phone, car, status, added_at)
               VALUES (?, ?, ?, ?, ?, 'approved', ?)
               ON CONFLICT(user_id) DO UPDATE SET full_name=excluded.full_name,
                    username=excluded.username, status='approved'""",
            (user_id, full_name, username, phone, car, datetime.now().isoformat()),
        )
        await db.commit()


async def get_drivers():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, user_id, full_name, username, phone, car, status FROM drivers WHERE status='approved' ORDER BY id"
        )
        return await cur.fetchall()


async def get_active_driver_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM drivers WHERE status='approved'")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def remove_driver(driver_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM drivers WHERE id=?", (driver_id,))
        await db.commit()


async def count_drivers():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM drivers WHERE status='approved'")
        (c,) = await cur.fetchone()
        return c


# --------------------------- DRIVER REQUESTS --------------------------------
async def create_driver_request(user_id: int, full_name: str, username: str, phone: str, car: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO driver_requests (user_id, full_name, username, phone, car, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (user_id, full_name, username, phone, car, datetime.now().isoformat()),
        )
        await db.commit()
        return cur.lastrowid


async def get_driver_request(req_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT * FROM driver_requests WHERE id=?", (req_id,))
        return await cur.fetchone()


async def set_driver_request_status(req_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE driver_requests SET status=? WHERE id=?", (status, req_id)
        )
        await db.commit()


async def get_pending_driver_requests():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, full_name, phone, car, created_at FROM driver_requests WHERE status='pending' ORDER BY id"
        )
        return await cur.fetchall()
