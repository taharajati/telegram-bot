"""
تست جامع هندلرهای اشتراک — نوتیف ادمین، جریان کامل خرید، تأیید/رد.
پوشش: handlers/subscription.py + services/subscription.py
"""
import pytest
import pytest_asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy import select

from database.db import async_session
from database.models import (
    Base,
    Shop,
    ShopOwner,
    ShopSubscription,
    SubscriptionPlan,
    User,
)
from services.subscription import (
    seed_subscription_plans,
    create_trial_subscription,
    create_paid_subscription,
    get_current_subscription,
    get_subscription_display,
    has_active_subscription,
    verify_subscription,
    reject_subscription,
)


# ─── Fixtures ───────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def _create_and_drop_tables():
    """Create tables before each test, drop after."""
    from database.db import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def _force_config(monkeypatch):
    """Force test config values."""
    monkeypatch.setattr("config.ADMIN_IDS", {888001, 888002})
    monkeypatch.setattr("config.ADMIN_CARD_NUMBER", "6219861937973138")
    monkeypatch.setattr("config.ADMIN_CARD_HOLDER", "طه رجعتی")
    monkeypatch.setattr("config.STORE_NAME", "فروشگرام")


@pytest.fixture
async def _seed_plans():
    async with async_session() as session:
        await seed_subscription_plans(session)
        await session.commit()


@pytest.fixture
async def make_shop():
    """Create a shop with owner. Returns (user_id, shop_id)."""
    async def _make(user_id=999999):
        async with async_session() as session:
            user = User(user_id=user_id, first_name="تستی", username="test_user")
            session.add(user)
            await session.flush()
            shop = Shop(
                name="فروشگاه تست",
                description="تست",
                phone="09120000000",
                is_active=True,
                status="active",
                shipping_cost=0,
            )
            session.add(shop)
            await session.flush()
            owner = ShopOwner(user_id=user_id, shop_id=shop.id)
            session.add(owner)
            await session.commit()
            return user_id, shop.id
    return _make


def _fake_update(query=None, message_text=None, user_id=999, photo=None):
    user = SimpleNamespace(id=user_id, first_name="تستی", last_name=None, username="test_user")
    update = SimpleNamespace()
    update.effective_user = user
    update.effective_chat = SimpleNamespace(id=9999)
    update.callback_query = query
    if message_text is not None or photo is not None:
        msg = SimpleNamespace()
        msg.text = message_text
        msg.photo = photo or []
        msg.caption = message_text or ""
        msg.reply_text = AsyncMock()
        msg.reply_html = AsyncMock()
        msg.delete = AsyncMock()
        update.message = msg
    else:
        update.message = None
    return update


def _fake_context():
    ctx = SimpleNamespace()
    ctx.user_data = {}
    ctx.bot = SimpleNamespace(
        send_message=AsyncMock(),
        send_photo=AsyncMock(),
        create_task=lambda c: None,
    )
    ctx.args = []
    ctx.match = None
    return ctx


def _fake_photo():
    """Create a fake photo object."""
    photo = SimpleNamespace()
    photo.file_id = "test_photo_file_id_001"
    return [photo]


async def _get_one_plan():
    async with async_session() as session:
        result = await session.execute(select(SubscriptionPlan))
        return result.scalars().first()


# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Admin Notification Tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_admin_notified_on_subscription_purchase(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    بعد از خرید اشتراک توسط فروشنده، باید به همه ادمین‌ها نوتیف بره.
    """
    from handlers.subscription import receive_receipt

    user_id, shop_id = await make_shop(user_id=777001)
    plan = await _get_one_plan()

    ctx = _fake_context()
    ctx.user_data["buy_plan_id"] = plan.id

    update = _fake_update(
        user_id=user_id,
        photo=_fake_photo(),
    )
    update.message.photo[-1] = update.message.photo[0]  # simulates photo[-1]

    await receive_receipt(update, ctx)

    # Admin should be notified
    admin_ids = {888001, 888002}
    notified = set()
    for call_args in ctx.bot.send_message.call_args_list:
        arg_user_id = call_args[0][0]
        if arg_user_id in admin_ids:
            notified.add(arg_user_id)

    assert notified == admin_ids, f"Admins {admin_ids - notified} were not notified"


@pytest.mark.asyncio
async def test_admin_notification_includes_detail_button(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    نوتیف ادمین باید دکمه 'مشاهده و تأیید' داشته باشه.
    """
    from handlers.subscription import receive_receipt

    user_id, shop_id = await make_shop(user_id=777002)
    plan = await _get_one_plan()

    ctx = _fake_context()
    ctx.user_data["buy_plan_id"] = plan.id

    update = _fake_update(user_id=user_id, photo=_fake_photo())

    await receive_receipt(update, ctx)

    # Check that admin notification has detail button
    admin_calls = [
        c for c in ctx.bot.send_message.call_args_list
        if c[0][0] in {888001, 888002}
    ]
    assert len(admin_calls) >= 1

    # Check button callback_data starts with admin:sub:detail:
    call_args = admin_calls[0]
    keyboard = call_args[1]["reply_markup"]  # InlineKeyboardMarkup
    found_detail_button = False
    for row in keyboard.inline_keyboard:
        for btn in row:
            if btn.callback_data.startswith("admin:sub:detail:"):
                found_detail_button = True
                break
    assert found_detail_button, "Admin notification missing detail button"


@pytest.mark.asyncio
async def test_admin_notification_includes_seller_info(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    نوتیف ادمین باید اطلاعات فروشنده و پلن رو داشته باشه.
    """
    from handlers.subscription import receive_receipt

    user_id, shop_id = await make_shop(user_id=777003)
    plan = await _get_one_plan()

    ctx = _fake_context()
    ctx.user_data["buy_plan_id"] = plan.id

    update = _fake_update(user_id=user_id, photo=_fake_photo())

    await receive_receipt(update, ctx)

    admin_calls = [
        c for c in ctx.bot.send_message.call_args_list
        if c[0][0] in {888001, 888002}
    ]
    assert len(admin_calls) >= 1

    text = admin_calls[0][0][1]  # message text
    assert "درخواست اشتراک جدید" in text
    assert plan.name in text


@pytest.mark.asyncio
async def test_seller_gets_confirmation_after_receipt(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    بعد از ارسال رسید، فروشنده باید پیام تأیید بگیره.
    """
    from handlers.subscription import receive_receipt

    user_id, shop_id = await make_shop(user_id=777004)
    plan = await _get_one_plan()

    ctx = _fake_context()
    ctx.user_data["buy_plan_id"] = plan.id

    update = _fake_update(user_id=user_id, photo=_fake_photo())

    await receive_receipt(update, ctx)

    # Check seller got confirmation
    update.message.reply_text.assert_called()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "درخواست اشتراک شما ثبت شد" in sent_text
    assert plan.name in sent_text


@pytest.mark.asyncio
async def test_seller_buy_flow_no_plan_id_shows_error(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    اگه plan_id تو user_data نباشه، خطا بده.
    """
    from handlers.subscription import receive_receipt

    user_id, shop_id = await make_shop(user_id=777005)

    ctx = _fake_context()
    ctx.user_data = {}  # no buy_plan_id

    update = _fake_update(user_id=user_id, photo=_fake_photo())

    await receive_receipt(update, ctx)

    sent_text = update.message.reply_text.call_args[0][0]
    assert "دوباره" in sent_text


@pytest.mark.asyncio
async def test_seller_buy_flow_non_photo_rejected(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    اگه فروشنده عکس نفرسته و متن بفرسته، reject بشه.
    """
    from handlers.subscription import receive_receipt

    user_id, shop_id = await make_shop(user_id=777006)
    plan = await _get_one_plan()

    ctx = _fake_context()
    ctx.user_data["buy_plan_id"] = plan.id

    update = _fake_update(user_id=user_id, message_text="این رسیدمه")
    # photo is empty list
    update.message.photo = []

    await receive_receipt(update, ctx)

    sent_text = update.message.reply_text.call_args[0][0]
    assert "عکس" in sent_text


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: Admin Verification Tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_admin_verify_sends_notification_to_seller(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    بعد از تأیید اشتراک توسط ادمین، فروشنده باید نوتیف بگیره.
    """
    from handlers.subscription import admin_verify_subscription

    seller_id, shop_id = await make_shop(user_id=777007)
    plan = await _get_one_plan()

    # Create subscription
    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="verify_seller_test", receipt_caption="",
        )
        await session.commit()

    ctx = _fake_context()
    admin_id = 888001

    query = SimpleNamespace()
    query.data = f"admin:sub:verify:{sub.id}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user = SimpleNamespace(id=admin_id)
    query.message = SimpleNamespace(
        chat_id=admin_id, message_id=1,
        delete=AsyncMock(), reply_text=AsyncMock(),
    )

    update = _fake_update(query=query, user_id=admin_id)

    await admin_verify_subscription(update, ctx)

    # Seller should be notified
    ctx.bot.send_message.assert_called()
    seller_notification = ctx.bot.send_message.call_args[0]
    assert seller_notification[0] == seller_id
    assert "تأیید شد" in seller_notification[1]


@pytest.mark.asyncio
async def test_admin_reject_seller_notified(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    بعد از رد اشتراک توسط ادمین، فروشنده نوتیف بگیره.
    """
    from handlers.subscription import admin_reject_subscription

    seller_id, shop_id = await make_shop(user_id=777008)
    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="reject_seller_test", receipt_caption="",
        )
        await session.commit()

    ctx = _fake_context()
    admin_id = 888001

    query = SimpleNamespace()
    query.data = f"admin:sub:reject:{sub.id}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user = SimpleNamespace(id=admin_id)
    query.message = SimpleNamespace(
        chat_id=admin_id, message_id=1,
        delete=AsyncMock(), reply_text=AsyncMock(),
    )

    update = _fake_update(query=query, user_id=admin_id)

    await admin_reject_subscription(update, ctx)

    # Seller should be notified about rejection
    ctx.bot.send_message.assert_called()
    seller_notification = ctx.bot.send_message.call_args[0]
    assert seller_notification[0] == seller_id
    assert "رد" in seller_notification[1]


@pytest.mark.asyncio
async def test_admin_list_pending_shows_subscriptions(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    لیست pending ادمین باید اشتراک‌های در انتظار رو نشون بده.
    """
    from handlers.subscription import admin_list_pending

    _, shop_id = await make_shop(user_id=777009)
    plan = await _get_one_plan()

    async with async_session() as session:
        await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="list_pending_test", receipt_caption="",
        )
        await session.commit()

    ctx = _fake_context()
    admin_id = 888001

    query = SimpleNamespace()
    query.data = "admin:subscription:pending"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user = SimpleNamespace(id=admin_id)
    query.message = SimpleNamespace(
        chat_id=admin_id, message_id=1,
        delete=AsyncMock(), reply_text=AsyncMock(),
    )

    update = _fake_update(query=query, user_id=admin_id)

    await admin_list_pending(update, ctx)

    text = query.edit_message_text.call_args[0][0]
    assert "درخواست" in text or "pending" in text.lower()


@pytest.mark.asyncio
async def test_admin_detail_shows_receipt_info(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    جزئیات درخواست اشتراک باید اطلاعات رسید و فروشنده رو نشون بده.
    """
    from handlers.subscription import admin_subscription_detail

    seller_id, shop_id = await make_shop(user_id=777010)
    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="detail_test", receipt_caption="",
        )
        await session.commit()

    ctx = _fake_context()
    admin_id = 888001

    query = SimpleNamespace()
    query.data = f"admin:sub:detail:{sub.id}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user = SimpleNamespace(id=admin_id)
    query.message = SimpleNamespace(
        chat_id=admin_id, message_id=1,
        delete=AsyncMock(), reply_text=AsyncMock(),
    )

    update = _fake_update(query=query, user_id=admin_id)

    await admin_subscription_detail(update, ctx)

    text = query.edit_message_text.call_args[0][0]
    assert plan.name in text
    assert "رسید" in text


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: Subscription Service Tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_trial_is_active(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """Trial باید فوراً active باشه."""
    user_id, shop_id = await make_shop(user_id=777011)

    async with async_session() as session:
        await create_trial_subscription(shop_id, admin_user_id=user_id, session=session)
        await session.commit()

    async with async_session() as session:
        active = await has_active_subscription(shop_id, session)
    assert active is True


@pytest.mark.asyncio
async def test_paid_pending_is_not_active(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """اشتراک پولی در حالت pending نباید active باشه."""
    _, shop_id = await make_shop(user_id=777012)
    plan = await _get_one_plan()

    async with async_session() as session:
        await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="pending_test", receipt_caption="",
        )
        await session.commit()

    async with async_session() as session:
        active = await has_active_subscription(shop_id, session)
    assert active is False


@pytest.mark.asyncio
async def test_paid_approved_is_active(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """اشتراک پولی بعد از تأیید ادمین باید active باشه."""
    _, shop_id = await make_shop(user_id=777013)
    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="approved_test", receipt_caption="",
        )
        await verify_subscription(sub.id, admin_user_id=888001, session=session)
        await session.commit()

    async with async_session() as session:
        active = await has_active_subscription(shop_id, session)
    assert active is True


@pytest.mark.asyncio
async def test_display_shows_pending_status(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """نمایش وضعیت اشتراک pending باید متن درست بده."""
    _, shop_id = await make_shop(user_id=777014)
    plan = await _get_one_plan()

    async with async_session() as session:
        await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="display_test", receipt_caption="",
        )
        await session.commit()

    async with async_session() as session:
        display = await get_subscription_display(shop_id, session)
    assert "انتظار" in display or "تأیید" in display


@pytest.mark.asyncio
async def test_display_shows_active_status(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """نمایش وضعیت اشتراک فعال باید متن درست بده."""
    _, shop_id = await make_shop(user_id=777015)
    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="active_display_test", receipt_caption="",
        )
        await verify_subscription(sub.id, admin_user_id=888001, session=session)
        await session.commit()

    async with async_session() as session:
        display = await get_subscription_display(shop_id, session)
    assert "باقی‌مانده" in display or "فعال" in display


@pytest.mark.asyncio
async def test_stack_same_plan_extends_end_date(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """خرید دوبار همون پلن باید end_date رو extend کنه (stack)."""
    _, shop_id = await make_shop(user_id=777016)
    plan = await _get_one_plan()

    async with async_session() as session:
        first = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="stack_first", receipt_caption="",
        )
        # Verify first subscription to make it active
        await verify_subscription(first.id, admin_user_id=888001, session=session)
        first_end = first.end_date
        await session.commit()

    async with async_session() as session:
        second = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="stack_second", receipt_caption="",
        )
        await session.commit()

    assert second.start_date >= first_end


@pytest.mark.asyncio
async def test_supersede_closes_old_record(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """خرید جدید باید ردیف قبلی رو supersede کنه."""
    _, shop_id = await make_shop(user_id=777017)
    plan = await _get_one_plan()

    async with async_session() as session:
        old = await create_trial_subscription(
            shop_id, admin_user_id=777017, session=session,
        )
        await session.commit()
        old_id = old.id

    async with async_session() as session:
        await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="supersede_test", receipt_caption="",
        )
        await session.commit()

    async with async_session() as session:
        current = await get_current_subscription(shop_id, session)
        old_row = await session.get(ShopSubscription, old_id)

    assert current is not None
    assert current.plan_id == plan.id
    assert old_row.superseded_at is not None


@pytest.mark.asyncio
async def test_reject_sets_rejection_reason(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """رد اشتراک باید rejection_reason ذخیره کنه."""
    _, shop_id = await make_shop(user_id=777018)
    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="reject_reason_test", receipt_caption="",
        )
        await reject_subscription(sub.id, admin_user_id=888001, reason="رسید مبهم", session=session)
        await session.commit()

    async with async_session() as session:
        updated = await session.get(ShopSubscription, sub.id)
    assert updated.rejection_reason == "رسید مبهم"
    assert updated.approval_status == "rejected"


@pytest.mark.asyncio
async def test_verify_idempotent(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """تأیید دوبار اشتراک نباید خطا بده (idempotent)."""
    _, shop_id = await make_shop(user_id=777019)
    plan = await _get_one_plan()

    async with async_session() as session:
        sub = await create_paid_subscription(
            shop_id=shop_id, plan_id=plan.id, session=session,
            receipt_file_id="idempotent_test", receipt_caption="",
        )
        await session.commit()

    async with async_session() as session:
        result1 = await verify_subscription(sub.id, admin_user_id=888001, session=session)
        await session.commit()
        assert result1 is not None

    async with async_session() as session:
        result2 = await verify_subscription(sub.id, admin_user_id=888001, session=session)
        await session.commit()
        # Idempotent: returns same sub but doesn't re-verify
        assert result2 is not None


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: show_subscription handler test
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_show_subscription_handler(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    show_subscription باید وضعیت اشتراک و دکمه‌های خرید رو نشون بده.
    """
    from handlers.subscription import show_subscription

    user_id, shop_id = await make_shop(user_id=777020)

    ctx = _fake_context()
    query = SimpleNamespace()
    query.data = "seller:subscription:show"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user = SimpleNamespace(id=user_id)
    query.message = SimpleNamespace(
        chat_id=user_id, message_id=1,
        delete=AsyncMock(), reply_text=AsyncMock(),
    )

    update = _fake_update(query=query, user_id=user_id)

    await show_subscription(update, ctx)

    query.edit_message_text.assert_called()
    text = query.edit_message_text.call_args[0][0]
    assert "اشتراک" in text


@pytest.mark.asyncio
async def test_buy_subscription_handler(
    _create_and_drop_tables, _seed_plans, make_shop
):
    """
    buy_subscription باید شماره کارت و اطلاعات پلن رو نشون بده.
    """
    from handlers.subscription import buy_subscription

    user_id, shop_id = await make_shop(user_id=777021)
    plan = await _get_one_plan()

    ctx = _fake_context()
    query = SimpleNamespace()
    query.data = f"seller:sub:buy:{plan.id}"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user = SimpleNamespace(id=user_id)
    query.message = SimpleNamespace(
        chat_id=user_id, message_id=1,
        delete=AsyncMock(), reply_text=AsyncMock(),
    )

    update = _fake_update(query=query, user_id=user_id)

    await buy_subscription(update, ctx)

    query.edit_message_text.assert_called()
    text = query.edit_message_text.call_args[0][0]
    assert plan.name in text
    assert "6219861937973138" in text  # ADMIN_CARD_NUMBER
