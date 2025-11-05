import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Get variables from hosting environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Memory storage for admin reply mapping
reply_targets = {}
REPLY_TIMEOUT = 10  # in minutes


def get_name(user):
    name = user.first_name if user else "User"
    if user and user.last_name:
        name += f" {user.last_name}"
    return name


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - respond differently for admin/user"""
    if update.effective_user.id == ADMIN_CHAT_ID:
        await update.message.reply_text("✅ Bot is running!\nYou're the admin.")
    else:
        await update.message.reply_text("Hello! Send your message and the admin will reply.")


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward every user message to admin with Reply button"""
    if update.effective_chat.id == ADMIN_CHAT_ID:
        return

    user = update.effective_user
    msg = update.effective_message

    await msg.copy(chat_id=ADMIN_CHAT_ID)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text=f"Reply to {get_name(user)}", callback_data=f"reply:{user.id}")]
    ])

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"📩 Message from {get_name(user)} (ID: `{user.id}`)",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate reply mode for clicking button"""
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split(":")[1])
    reply_targets[ADMIN_CHAT_ID] = (
        user_id,
        datetime.utcnow() + timedelta(minutes=REPLY_TIMEOUT)
    )

    await query.edit_message_text(
        f"✅ Reply mode ON for User `{user_id}` (valid {REPLY_TIMEOUT} mins)",
        parse_mode="Markdown"
    )


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send admin's message back to the user if reply mode is active"""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return

    target = reply_targets.get(ADMIN_CHAT_ID)
    if not target:
        return

    user_id, expiry = target
    if datetime.utcnow() > expiry:
        await update.message.reply_text("⏰ Reply session expired.")
        reply_targets.pop(ADMIN_CHAT_ID, None)
        return

    await update.message.copy(chat_id=user_id)
    await update.message.reply_text(f"✅ Sent to user {user_id}")


def main():
    if not BOT_TOKEN:
        raise Exception("❌ BOT_TOKEN not found in environment!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_reply_button, pattern=r"^reply:\d+$"))
    app.add_handler(MessageHandler(~filters.Chat(ADMIN_CHAT_ID), forward_to_admin))
    app.add_handler(MessageHandler(filters.Chat(ADMIN_CHAT_ID), admin_reply))

    print("✅ Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
