import logging
from datetime import datetime, date
from config import BOT_TOKEN
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db

TOKEN = BOT_TOKEN
REMINDER_HOUR = 9
REMINDER_MINUTE = 0

CHOOSE_SUBJECT, NEW_SUBJECT, ENTER_DESCRIPTION, ENTER_DEADLINE = range(4)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)



async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " Привет! Я помогаю следить за домашними заданиями.\n\n"
        "Команды:\n"
        "/add — добавить задание\n"
        "/list — список активных заданий\n"
        "/done — отметить задание выполненным\n"
        "/delete — удалить задание\n"
        "/subjects — управление предметами\n"
        "/cancel — отменить текущее действие",
        parse_mode="Markdown",
    )



async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subjects = db.get_subjects(user_id)

    buttons = [
        [InlineKeyboardButton(f"{name}", callback_data=f"subj|{sid}")]
        for sid, name in subjects
    ]
    buttons.append([InlineKeyboardButton("➕ Новый предмет", callback_data="subj|new")])

    await update.message.reply_text(
        " Выбери предмет для задания:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return CHOOSE_SUBJECT


async def cb_choose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "subj|new":
        await query.edit_message_text("Введи название нового предмета:")
        return NEW_SUBJECT

    subject_id = int(query.data.split("|")[1])
    context.user_data["subject_id"] = subject_id
    await query.edit_message_text("Введи описание задания:")
    return ENTER_DESCRIPTION


async def step_new_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text("Название не может быть пустым. Попробуй ещё раз:")
        return NEW_SUBJECT

    subject_id = db.add_subject(user_id, name)
    context.user_data["subject_id"] = subject_id
    await update.message.reply_text(
        f" Предмет {name}  добавлен!\n\n Введи описание задания:",
        parse_mode="Markdown"
    )
    return ENTER_DESCRIPTION


async def step_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text.strip()
    await update.message.reply_text(
        "Введи дедлайн в формате ДД.ММ.ГГГГ:",
        parse_mode="Markdown"
    )
    return ENTER_DEADLINE


async def step_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    try:
        deadline = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await update.message.reply_text(
            " Неверный формат.",
            parse_mode="Markdown"
        )
        return ENTER_DEADLINE

    if deadline < date.today():
        await update.message.reply_text(" Эта дата уже прошла. Введи актуальный дедлайн:")
        return ENTER_DEADLINE

    db.add_homework(
        user_id,
        context.user_data["subject_id"],
        context.user_data["description"],
        deadline.isoformat(),
    )
    await update.message.reply_text(
        f" адание добавлено!\nДедлайн: *{deadline.strftime('%d.%m.%Y')}*",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(" Действие отменено.")
    return ConversationHandler.END



async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    homeworks = db.get_homeworks(user_id)

    if not homeworks:
        await update.message.reply_text(" Активных заданий нет. Используй /add чтобы добавить.")
        return

    today = date.today()
    lines = [" Активные задания:\n"]

    for hw_id, subject, description, deadline_str in homeworks:
        deadline = date.fromisoformat(deadline_str)
        days_left = (deadline - today).days

        if days_left < 0:
            emoji = "🔴"
            days_text = f"просрочено на {-days_left} дн."
        elif days_left == 0:
            emoji = "🔴"
            days_text = "сегодня!"
        elif days_left == 1:
            emoji = "🟠"
            days_text = "завтра!"
        elif days_left <= 3:
            emoji = "🟡"
            days_text = f"{days_left} дн."
        else:
            emoji = "🟢"
            days_text = f"{days_left} дн."

        lines.append(
            f"{emoji} *{subject}*\n"
            f"   {description}\n"
            f"   {deadline.strftime('%d.%m.%Y')} — {days_text}\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")



async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    homeworks = db.get_homeworks(user_id)

    if not homeworks:
        await update.message.reply_text("Нет активных заданий.")
        return

    buttons = [
        [InlineKeyboardButton(f" {subject} — {desc[:35]}", callback_data=f"done|{hw_id}")]
        for hw_id, subject, desc, _ in homeworks
    ]
    await update.message.reply_text(
        "Отметить какое задание выполненным?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hw_id = int(query.data.split("|")[1])
    db.mark_done(hw_id, query.from_user.id)
    await query.edit_message_text(" Задание отмечено как выполненное")


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    homeworks = db.get_homeworks(user_id)

    if not homeworks:
        await update.message.reply_text(" Нет активных заданий.")
        return

    buttons = [
        [InlineKeyboardButton(f" {subject} — {desc[:35]}", callback_data=f"del|{hw_id}")]
        for hw_id, subject, desc, _ in homeworks
    ]
    await update.message.reply_text(
        "Какое задание удалить?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hw_id = int(query.data.split("|")[1])
    db.delete_homework(hw_id, query.from_user.id)
    await query.edit_message_text(" Задание удалено.")



async def cmd_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subjects = db.get_subjects(user_id)

    if not subjects:
        await update.message.reply_text(" Предметов пока нет. Добавь первый через /add.")
        return

    text = " *Твои предметы:*\n\n" + "\n".join(f"  {name}" for _, name in subjects)
    text += "\n\nНажми на предмет, чтобы удалить:"
    buttons = [
        [InlineKeyboardButton(f" {name}", callback_data=f"delsubj|{sid}")]
        for sid, name in subjects
    ]
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cb_delete_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_id = int(query.data.split("|")[1])
    db.delete_subject(subject_id, query.from_user.id)
    await query.edit_message_text(" Предмет удалён.")



async def send_reminders(app: Application):
    homeworks = db.get_homeworks_due_tomorrow()
    for user_id, subject, description, deadline in homeworks:
        try:
            await app.bot.send_message(
                chat_id=user_id,
                text=(
                    f" *Напоминание!*\n\n"
                    f"Завтра дедлайн по *{subject}*:\n"
                    f"_{description}_\n\n"
                    f" {datetime.fromisoformat(deadline).strftime('%d.%m.%Y')}"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить напоминание пользователю {user_id}: {e}")



def main():
    db.init_db()
    logger.info(f"БД {db.DB_NAME}")

    app = Application.builder().token(TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", cmd_add)],
        states={
            CHOOSE_SUBJECT:    [CallbackQueryHandler(cb_choose_subject, pattern=r"^subj\|")],
            NEW_SUBJECT:       [MessageHandler(filters.TEXT & ~filters.COMMAND, step_new_subject)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_description)],
            ENTER_DEADLINE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, step_deadline)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(add_conv)
    app.add_handler(CommandHandler("list",     cmd_list))
    app.add_handler(CommandHandler("done",     cmd_done))
    app.add_handler(CommandHandler("delete",   cmd_delete))
    app.add_handler(CommandHandler("subjects", cmd_subjects))
    app.add_handler(CommandHandler("cancel",   cmd_cancel))

    app.add_handler(CallbackQueryHandler(cb_done,           pattern=r"^done\|"))
    app.add_handler(CallbackQueryHandler(cb_delete,         pattern=r"^del\|"))
    app.add_handler(CallbackQueryHandler(cb_delete_subject, pattern=r"^delsubj\|"))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_reminders,
        trigger="cron",
        hour=REMINDER_HOUR,
        minute=REMINDER_MINUTE,
        args=[app],
    )
    scheduler.start()

    logger.info("Бот запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
