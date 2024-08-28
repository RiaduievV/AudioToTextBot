import logging
import dotenv
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
import speech_recognition as sr
from pydub import AudioSegment

dotenv.load_dotenv(override=True)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

user_language = {}


def get_language_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Русский", callback_data="lang_ru"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_language_menu(update, context)


async def show_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_language_keyboard()
    await update.message.reply_text(
        "Please choose your language / Пожалуйста, выберите ваш язык:",
        reply_markup=reply_markup,
    )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_language_menu(update, context)


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user_language[user_id] = query.data.split("_")[1]

    if user_language[user_id] == "en":
        message = "Language set to English. Say something or forward the voice message."
    else:
        message = "Язык установлен на русский. Скажите что-нибудь или перешлите голосовое сообщение."

    await query.edit_message_text(message)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, "en")

    voice = await update.message.voice.get_file()
    await update.message.reply_text(
        "One moment..." if lang == "en" else "Одну минуту..."
    )

    voice_ogg = await voice.download_as_bytearray()
    with open("voice.ogg", "wb") as f:
        f.write(voice_ogg)

    audio = AudioSegment.from_ogg("voice.ogg")
    audio.export("voice.wav", format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile("voice.wav") as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(
            audio, language="en-US" if lang == "en" else "ru-RU"
        )
        await update.message.reply_text(f"{text}")
    except sr.UnknownValueError:
        await update.message.reply_text(
            "Sorry, speech recognition failed"
            if lang == "en"
            else "Извините, распознавание речи не удалось"
        )
    except sr.RequestError as e:
        await update.message.reply_text(
            f"Speech recognition service error: {e}"
            if lang == "en"
            else f"Ошибка сервиса распознавания речи: {e}"
        )

    os.remove("voice.ogg")
    os.remove("voice.wav")


async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start - Start the bot and choose language",
        "/language - Change the language",
        "/help - Show available commands",
    ]
    await update.message.reply_text("\n".join(commands))


def main():
    application = Application.builder().token(os.getenv("TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("help", list_commands))
    application.add_handler(CallbackQueryHandler(language_callback))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    application.run_polling()


if __name__ == "__main__":
    main()
