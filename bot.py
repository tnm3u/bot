import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Bot token & admin ID taken from Render environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Keep track of reply targets
reply_targets = {}

REPLY_TIMEOUT = 10  # minutes


def get_name(user):
    name = user.first_name if user else "User"
    if user and user.last_name:
        name += f" {user.last_name}"
    return name


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_CHAT_ID:
        await update.message.reply_text("✅ Bot is running on Render!\nYou're the admin.")
    else:
        await update.message.reply_text("Hello! Send your message and the admin will reply.")


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split(":")[1])
    reply_targets[ADMIN_CHAT_ID] = (
        user_id,
        datetime.utcnow() + timedelta(minutes=REPLY_TIMEOUT)
    )

    await query.edit_message_text(
        f"✅ Reply mode activated for User ID `{user_id}` (valid {REPLY_TIMEOUT} mins)",
        parse_mode="Markdown"
    )


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    print("✅ Bot is running on Render...")
    app.run_polling()


if __name__ == "__main__":
    main()
      
