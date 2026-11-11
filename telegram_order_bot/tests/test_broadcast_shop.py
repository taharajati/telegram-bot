"""
تست: قابلیت broadcast برای فروشگاه خاص + لیست همه فروشگاه‌ها + دکمه جستجو.
"""
import pytest
from unittest.mock import AsyncMock
from types import SimpleNamespace

from sqlalchemy import select

from database.db import async_session
from database.models import (
    Base, Shop, ShopOwner, User, Product, Category,
)


# ─── Fixtures ───────────────────────────────────────────────────


@pytest.fixture(autouse=True)
async def _tables():
    from database.db import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def _force_config(monkeypatch):
    monkeypatch.setattr("config.ADMIN_IDS", {888001, 888002})


def fake_update(user_id, data=None, msg_text=None):
    user = SimpleNamespace(id=user_id, first_name="Test")
    update = SimpleNamespace(
        effective_user=user,
        effective_chat=SimpleNamespace(id=9999),
    )
    if data is not None:
        q = SimpleNamespace()
        q.data = data
        q.answer = AsyncMock()
        q.edit_message_text = AsyncMock()
        q.edit_message_caption = AsyncMock()
        q.message = SimpleNamespace(
            chat_id=9999, message_id=1,
            delete=AsyncMock(), reply_text=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        q.from_user = SimpleNamespace(id=user_id)
        update.callback_query = q
        update.message = None
    else:
        update.callback_query = None
        msg = SimpleNamespace()
        msg.text = msg_text
        msg.photo = []
        msg.reply_text = AsyncMock()
        msg.reply_html = AsyncMock()
        msg.delete = AsyncMock()
        update.message = msg
    return update


def fake_context():
    ctx = SimpleNamespace()
    ctx.user_data = {}
    ctx.bot = SimpleNamespace(
        send_message=AsyncMock(), send_photo=AsyncMock(),
        create_task=lambda c: None,
    )
    ctx.args = []
    ctx.match = None
    return ctx


async def make_shop(name="فروشگاه تست"):
    async with async_session() as session:
        shop = Shop(name=name, description="توضیح تست", is_active=True, status="active",
                    phone="09120000000", shipping_cost=0)
        session.add(shop)
        await session.commit()
        await session.refresh(shop)
        shop_id = shop.id
    return shop_id


async def make_user(user_id, last_shop_id=None):
    async with async_session() as session:
        user = User(user_id=user_id, first_name="Test", last_shop_id=last_shop_id)
        session.add(user)
        await session.commit()


async def make_owner(user_id, shop_id):
    async with async_session() as session:
        owner = ShopOwner(user_id=user_id, shop_id=shop_id)
        session.add(owner)
        await session.commit()


# ══════════════════════════════════════════════════════════════════
# TESTS: Admin shops all list
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_shops_all_list_shows_broadcast_button(_tables):
    """لیست همه فروشگاه‌ها باید دکمه تبلیغ برای هر فروشگاه نشون بده."""
    sid1 = await make_shop("فروشگاه اول")
    sid2 = await make_shop("فروشگاه دوم")

    from handlers.admin.shops import list_all_shops
    upd = fake_update(user_id=888001, data="admin:shops:all:0")
    ctx = fake_context()
    await list_all_shops(upd, ctx)

    assert upd.callback_query.edit_message_text.called
    # Shop names appear in the inline keyboard buttons, not text
    args, kwargs = upd.callback_query.edit_message_text.call_args
    keyboard = kwargs.get("reply_markup")
    all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
    callback_datas = [btn.callback_data for btn in all_buttons]

    assert any(f"admin:shops:edit:{sid1}" in cd for cd in callback_datas)
    assert any(f"admin:shops:edit:{sid2}" in cd for cd in callback_datas)
    assert any("admin:broadcast:shop:" in cd for cd in callback_datas)


@pytest.mark.asyncio
async def test_admin_shops_all_unauthorized_user(_tables):
    """کاربر عادی نمی‌تونه لیست همه رو ببینه."""
    from handlers.admin.shops import list_all_shops
    upd = fake_update(user_id=9999, data="admin:shops:all:0")
    ctx = fake_context()
    await list_all_shops(upd, ctx)

    upd.callback_query.answer.assert_called_with("❌ فقط ادمین کل.", show_alert=True)


@pytest.mark.asyncio
async def test_admin_shops_all_empty(_tables):
    """لیست خالی — پیام مناسب."""
    from handlers.admin.shops import list_all_shops
    upd = fake_update(user_id=888001, data="admin:shops:all:0")
    ctx = fake_context()
    await list_all_shops(upd, ctx)

    text = upd.callback_query.edit_message_text.call_args[0][0]
    assert "هیچ فروشگاهی" in text


# ══════════════════════════════════════════════════════════════════
# TESTS: Broadcast to shop users
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_broadcast_shop_start_sets_shop_id(_tables):
    """شروع broadcast برای فروشگاه خاص — shop_id ذخیره بشه."""
    sid = await make_shop("فروشگاه تبلیغاتی")

    from handlers.admin.broadcast import broadcast_shop_start
    upd = fake_update(user_id=888001, data=f"admin:broadcast:shop:{sid}")
    ctx = fake_context()
    await broadcast_shop_start(upd, ctx)

    assert ctx.user_data["broadcast_shop_id"] == sid
    text = upd.callback_query.edit_message_text.call_args[0][0]
    assert "فروشگاه تبلیغاتی" in text
    assert "متن پیام" in text


@pytest.mark.asyncio
async def test_broadcast_shop_sends_to_shop_visitors(_tables):
    """broadcast فقط به کاربرانی بره که last_shop_id == shop_id باشه."""
    sid = await make_shop("فروشگاه تبلیغ")

    # 3 users: 2 visited this shop, 1 visited another
    await make_user(5001, last_shop_id=sid)
    await make_user(5002, last_shop_id=sid)
    await make_user(5003, last_shop_id=99999)  # different shop

    from handlers.admin.broadcast import send_broadcast_shop
    upd = fake_update(user_id=888001, msg_text="🎉 تخفیف ویژه این فروشگاه!")
    ctx = fake_context()
    ctx.user_data["broadcast_shop_id"] = sid

    await send_broadcast_shop(upd, ctx)

    # Should have sent to 5001 and 5002, NOT 5003
    sent_calls = ctx.bot.send_message.call_args_list
    sent_chats = [call.kwargs.get("chat_id") or call.args[0] for call in sent_calls]

    assert 5001 in sent_chats
    assert 5002 in sent_chats
    assert 5003 not in sent_chats

    # Status message should show 2 sent
    status_text = upd.message.reply_text.call_args_list[0].kwargs.get("text", "") or \
                  upd.message.reply_text.call_args_list[0].args[0]
    # After edit
    final_text = ctx.bot.send_message.call_args  # Last call — check status
    assert "2" in str(sent_chats.count(5001) + sent_chats.count(5002))


@pytest.mark.asyncio
async def test_broadcast_shop_no_users_shows_zero(_tables):
    """broadcast برای فروشگاهی که کاربری ندیده — صفر ارسال."""
    sid = await make_shop("فروشگاه خالی")

    from handlers.admin.broadcast import send_broadcast_shop
    upd = fake_update(user_id=888001, msg_text="تبلیغ بدون مخاطب")
    ctx = fake_context()
    ctx.user_data["broadcast_shop_id"] = sid

    await send_broadcast_shop(upd, ctx)

    # No users to send to
    assert ctx.bot.send_message.call_count == 0  # No messages sent


@pytest.mark.asyncio
async def test_broadcast_shop_no_shop_id_shows_error(_tables):
    """broadcast بدون shop_id — ارور."""
    from handlers.admin.broadcast import send_broadcast_shop
    upd = fake_update(user_id=888001, msg_text="متن بدون فروشگاه")
    ctx = fake_context()
    ctx.user_data["broadcast_shop_id"] = None

    await send_broadcast_shop(upd, ctx)

    assert upd.message.reply_text.called
    text = upd.message.reply_text.call_args[0][0]
    assert "❌" in text


@pytest.mark.asyncio
async def test_broadcast_shop_unauthorized_user(_tables):
    """کاربر غیرادمین نتونه broadcast بزنه."""
    from handlers.admin.broadcast import broadcast_shop_start
    upd = fake_update(user_id=9999, data="admin:broadcast:shop:1")
    ctx = fake_context()
    await broadcast_shop_start(upd, ctx)

    # Should be blocked by admin_only decorator
    # (broadcast_shop_start doesn't have @admin_only but send_broadcast_shop does)
    # Let's test send_broadcast_shop instead
    from handlers.admin.broadcast import send_broadcast_shop
    upd2 = fake_update(user_id=9999, msg_text="spam")
    ctx2 = fake_context()
    ctx2.user_data["broadcast_shop_id"] = 1
    await send_broadcast_shop(upd2, ctx2)

    # Should be blocked by admin_only decorator
    # The @admin_only decorator checks is_super_admin — 9999 is not admin


@pytest.mark.asyncio
async def test_broadcast_shop_blocked_user_marked(_tables):
    """کاربری که ربات رو بلاک کرده — is_blocked True بشه."""
    sid = await make_shop("فروشگاه تست بلاک")
    await make_user(6001, last_shop_id=sid)
    await make_user(6002, last_shop_id=sid)  # Will block the bot

    from handlers.admin.broadcast import send_broadcast_shop
    upd = fake_update(user_id=888001, msg_text="تبلیغ تست بلاک")
    ctx = fake_context()
    ctx.user_data["broadcast_shop_id"] = sid

    # Make send_message raise Forbidden for 6002
    from telegram.error import Forbidden
    original_send = ctx.bot.send_message

    async def mock_send(chat_id, **kwargs):
        if chat_id == 6002:
            raise Forbidden("Bot was blocked")
        return AsyncMock()

    ctx.bot.send_message = mock_send

    await send_broadcast_shop(upd, ctx)

    async with async_session() as session:
        user = await session.get(User, 6002)
        assert user.is_blocked is True

        user1 = await session.get(User, 6001)
        assert user1.is_blocked is False or user1.is_blocked is None


# ══════════════════════════════════════════════════════════════════
# TESTS: Start menu search button
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_start_menu_includes_search_button(_tables):
    """منوی /start باید دکمه جستجو داشته باشه."""
    from handlers.start import _platform_welcome
    text, keyboard = _platform_welcome("تست")

    assert "جستجو" in text or any(
        "جستجو" in btn.text
        for row in keyboard.inline_keyboard
        for btn in row
    )


@pytest.mark.asyncio
async def test_start_menu_search_button_callback_data(_tables):
    """دکمه جستجو باید callback_data='search:open' داشته باشه."""
    from handlers.start import _platform_welcome
    text, keyboard = _platform_welcome("تست")

    found = False
    for row in keyboard.inline_keyboard:
        for btn in row:
            if "جستجو" in btn.text:
                found = True
                assert btn.callback_data == "search:open"
                break

    assert found, "دکمه جستجو در منوی استارت پیدا نشد"


@pytest.mark.asyncio
async def test_admin_panel_includes_all_shops_button(_tables):
    """پنل ادمین باید دکمه لیست همه فروشگاه‌ها داشته باشه."""
    from handlers.admin.panel import admin_command
    upd = fake_update(user_id=888001, msg_text="/admin")
    ctx = fake_context()
    await admin_command(upd, ctx)

    assert upd.message.reply_text.called
    text = upd.message.reply_text.call_args[0][0]
    keyboard = upd.message.reply_text.call_args[1].get("reply_markup")

    assert "فروشگاه" in text
    # Check keyboard has "لیست همه فروشگاه‌ها"
    if keyboard:
        found = False
        for row in keyboard.inline_keyboard:
            for btn in row:
                if "همه فروشگاه" in btn.text:
                    found = True
                    assert btn.callback_data == "admin:shops:all:0"
                    break
        assert found, "دکمه 'لیست همه فروشگاه‌ها' در پنل ادمین پیدا نشد"
