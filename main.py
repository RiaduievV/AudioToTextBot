import logging
import dotenv
import os
import subprocess
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

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
dotenv.load_dotenv(override=True)

# Функции для проверки и настройки FFmpeg
def get_ffmpeg_path():
    try:
        return subprocess.check_output(["which", "ffmpeg"]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_ffprobe_path():
    try:
        return subprocess.check_output(["which", "ffprobe"]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def check_ffmpeg():
    try:
        ffmpeg_version = subprocess.check_output(["ffmpeg", "-version"]).decode()
        return True
    except Exception as e:
        logger.error(f"Error checking FFmpeg: {e}")
        return False

# Настройка путей FFmpeg
ffmpeg_path = os.getenv("FFMPEG_PATH") or get_ffmpeg_path() or "/usr/bin/ffmpeg"
ffprobe_path = os.getenv("FFPROBE_PATH") or get_ffprobe_path() or "/usr/bin/ffprobe"

logger.debug(f"FFMPEG_PATH: {ffmpeg_path}")
logger.debug(f"FFPROBE_PATH: {ffprobe_path}")

AudioSegment.converter = ffmpeg_path
AudioSegment.ffmpeg = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

# Словарь для хранения языковых настроек пользователей
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

    try:
        audio = AudioSegment.from_ogg("voice.ogg")
        audio.export("voice.wav", format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile("voice.wav") as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(
            audio, language="en-US" if lang == "en" else "ru-RU"
        )
        await update.message.reply_text(f"{text}")
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await update.message.reply_text(
            "Sorry, an error occurred while processing your voice message."
            if lang == "en"
            else "Извините, произошла ошибка при обработке вашего голосового сообщения."
        )
    finally:
        # Очистка временных файлов
        for file in ["voice.ogg", "voice.wav"]:
            if os.path.exists(file):
                os.remove(file)

async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start - Start the bot and choose language",
        "/language - Change the language",
        "/help - Show available commands",
    ]
    await update.message.reply_text("\n".join(commands))

def main():
    # Проверка FFmpeg перед запуском бота
    if not check_ffmpeg():
        logger.error("FFmpeg is not installed or not accessible. Exiting.")
        return

    token = os.getenv("TOKEN")
    if not token:
        logger.error("Bot token not found in environment variables. Exiting.")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("help", list_commands))
    application.add_handler(CallbackQueryHandler(language_callback))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Starting bot...")
    application.run_polling()

if __name__ == "__main__":
    main()