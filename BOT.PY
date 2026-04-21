 import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, CallbackQueryHandler, ConversationHandler
)

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7302311275  # yahan apni admin id daalo

ACCOUNT_NUMBER = "03286058052"
ACCOUNT_NAME = "MUHAMMAD HASNAIN"

# ===== DATA =====
users = {}
orders = []
pending_payments = {}

# ===== STATES =====
SERVICE, QUANTITY, LINK, PAYMENT_SS, PAYMENT_TXID = range(5)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.setdefault(user_id, {"balance": 0, "orders": []})

    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("🛒 Order", callback_data="order")],
        [InlineKeyboardButton("📊 Balance", callback_data="balance")],
        [InlineKeyboardButton("📜 Order History", callback_data="history")]
    ]
    await update.message.reply_text("Welcome to SMM Bot", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== MENU =====
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "deposit":
        await query.message.reply_text(
            f"Send Payment:\nAccount: {ACCOUNT_NUMBER}\nName: {ACCOUNT_NAME}\n\nMinimum Deposit: Rs.1000\n\nSend screenshot after payment"
        )
        return PAYMENT_SS

    elif query.data == "balance":
        bal = users[user_id]["balance"]
        await query.message.reply_text(f"Balance: Rs.{bal}")

    elif query.data == "history":
        if not users[user_id]["orders"]:
            await query.message.reply_text("No orders yet")
        else:
            await query.message.reply_text("\n".join(users[user_id]["orders"]))

    elif query.data == "order":
        keyboard = [
            [InlineKeyboardButton("Followers", callback_data="followers")],
            [InlineKeyboardButton("Likes", callback_data="likes")],
            [InlineKeyboardButton("Views", callback_data="views")]
        ]
        await query.message.reply_text("Select Service:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SERVICE

# ===== PAYMENT =====
async def payment_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pending_payments[user_id] = {"screenshot": update.message.photo[-1].file_id}
    await update.message.reply_text("Send Transaction ID:")
    return PAYMENT_TXID

async def payment_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    txid = update.message.text

    pending_payments[user.id]["txid"] = txid

    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}")
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=pending_payments[user.id]["screenshot"],
        caption=f"Payment Request\nUser: {user.username}\nID: {user.id}\nTXID: {txid}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("Payment submitted for approval")
    return ConversationHandler.END

# ===== ADMIN PAYMENT =====
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("_")
    user_id = int(user_id)

    if action == "approve":
        users[user_id]["balance"] += 1000
        await context.bot.send_message(user_id, "Deposit Approved ✅ Rs.1000 added")
        await query.message.edit_text("Approved")

    elif action == "reject":
        await context.bot.send_message(user_id, "Deposit Rejected ❌")
        await query.message.edit_text("Rejected")

# ===== ORDER =====
async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["service"] = query.data
    await query.message.reply_text("Enter Quantity:")
    return QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quantity"] = int(update.message.text)
    await update.message.reply_text("Send TikTok Link:")
    return LINK

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    service = context.user_data["service"]
    qty = context.user_data["quantity"]
    link = update.message.text

    # PRICE
    price = 0
    if service == "followers":
        price = (qty / 1000) * 5
    elif service == "likes":
        price = (qty / 10000) * 50

    if users[user_id]["balance"] < price:
        await update.message.reply_text("Insufficient balance")
        return ConversationHandler.END

    users[user_id]["balance"] -= price

    order_id = len(orders)
    users[user_id]["orders"].append(f"{service} | {qty} | Pending")

    keyboard = [
        [
            InlineKeyboardButton("✅ Complete", callback_data=f"done_{user_id}_{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}_{order_id}")
        ]
    ]

    await context.bot.send_message(
        ADMIN_ID,
        f"New Order\nUser: {user_id}\nService: {service}\nQty: {qty}\nLink: {link}\nPrice: {price}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    orders.append({"user": user_id, "status": "Pending"})

    await update.message.reply_text("Order placed successfully")
    return ConversationHandler.END

# ===== ADMIN ORDER =====
async def order_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id, order_id = query.data.split("_")
    user_id = int(user_id)
    order_id = int(order_id)

    if action == "done":
        orders[order_id]["status"] = "Completed"
        await context.bot.send_message(user_id, "Order Completed ✅")
        await query.message.edit_text("Completed")

    elif action == "cancel":
        await context.bot.send_message(user_id, "Order Cancelled ❌")
        await query.message.edit_text("Cancelled")

# ===== MAIN =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(menu))
app.add_handler(CallbackQueryHandler(admin_action, pattern="approve_|reject_"))
app.add_handler(CallbackQueryHandler(select_service, pattern="followers|likes|views"))
app.add_handler(CallbackQueryHandler(order_admin, pattern="done_|cancel_"))

conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(menu)],
    states={
        PAYMENT_SS: [MessageHandler(filters.PHOTO, payment_ss)],
        PAYMENT_TXID: [MessageHandler(filters.TEXT, payment_txid)],
        SERVICE: [CallbackQueryHandler(select_service)],
        QUANTITY: [MessageHandler(filters.TEXT, get_quantity)],
        LINK: [MessageHandler(filters.TEXT, get_link)],
    },
    fallbacks=[]
)

app.add_handler(conv)

app.run_polling()