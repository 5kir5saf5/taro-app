import asyncio
import os
import random
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Твой Telegram ID

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# =========================
# ФАЙЛ ДАННЫХ
# =========================
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "pending_payments": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =========================
# СОСТОЯНИЯ
# =========================
class TarotState(StatesGroup):
    waiting_question = State()
    waiting_topic = State()

class AdminState(StatesGroup):
    waiting_queries_count = State()

# =========================
# ВСЕ 78 КАРТ ТАРО (КРАСОЧНЫЕ ТРАКТОВКИ)
# =========================
cards = {
    "Шут": {
        "upright": "🌟 НАЧАЛО ПУТИ: Вселенная приглашает тебя сделать смелый шаг. Судьба шепчет: «Пора!» Твой вопрос {question} — это дверь в новое приключение. Доверься потоку.",
        "reversed": "⚠️ НЕДУМАЙ: Ты стоишь на краю, но боишься прыгнуть. {question} требует спонтанности, но страх парализует. Сделай вдох и отпусти контроль."
    },
    "Маг": {
        "upright": "💪 ВСЕ РЕСУРСЫ У ТЕБЯ: Для {question} у тебя есть всё! Твои таланты, связи и энергия — идеальный коктейль. Действуй уверенно.",
        "reversed": "🌀 РАСТОЧЕНИЕ СИЛ: Твой вопрос {question} пока останется без ответа — ты разбрасываешься энергией на пустяки. Сфокусируйся."
    },
    "Верховная Жрица": {
        "upright": "🌙 ИНТУИЦИЯ ВЕДЁТ: Прислушайся к внутреннему голосу по вопросу {question}. Тайна скоро раскроется во сне или знаке.",
        "reversed": "🔮 ЗАВЕСА ТАЙНЫ: Ответ на {question} скрыт за туманом. Сейчас не время знать — подожди."
    },
    "Императрица": {
        "upright": "🌸 РАСЦВЕТ: {question} принесёт плоды, как сад весной. Ты входишь в период изобилия и творчества.",
        "reversed": "🥀 ЗАСТОЙ: Энергия {question} заблокирована. Позволь себе отдохнуть — рост начнётся после паузы."
    },
    "Император": {
        "upright": "🏰 СТАБИЛЬНОСТЬ: {question} будет решён через структуру и порядок. Составь план — и всё получится.",
        "reversed": "⚡ ХАОС: В {question} не хватает дисциплины. Возьми контроль в свои руки, иначе рухнет."
    },
    "Иерофант": {
        "upright": "📜 МУДРОСТЬ: Для {question} обратись к старшим или книгам. Традиционный путь — самый верный.",
        "reversed": "🚫 БУНТ: Ты отвергаешь очевидное в {question}. Бунт красив, но неэффективен."
    },
    "Влюбленные": {
        "upright": "❤️ ВЫБОР СЕРДЦА: {question} связан с чувствами. Следуй зову души — там гармония.",
        "reversed": "💔 РАЗЛАД: В {question} конфликт между долгом и желанием. Честность с собой исцелит."
    },
    "Колесница": {
        "upright": "🏆 ПОБЕДА: {question} завершится триумфом! Твоя воля сдвинет горы.",
        "reversed": "🚧 ПРЕПЯТСТВИЯ: Колеса {question} буксуют. Усиль натиск или смени тактику."
    },
    "Сила": {
        "upright": "🦁 СМЕЛОСТЬ: В {question} твоя мягкая сила победит агрессию. Будь как вода.",
        "reversed": "😨 СЛАБОСТЬ: Страх мешает {question}. Ты сильнее, чем кажешься."
    },
    "Отшельник": {
        "upright": "🕯️ ПОИСК: {question} требует уединения и размышлений. Ответ внутри тебя.",
        "reversed": "🏚️ ИЗОЛЯЦИЯ: Ты застрял в {question} в одиночестве. Пора выйти к людям."
    },
    "Колесо Фортуны": {
        "upright": "🎡 ПЕРЕМЕНЫ: Судьба вращает колесо для {question}. Скоро неожиданный поворот!",
        "reversed": "⏸️ ЗАДЕРЖКА: {question} заморожен. Сопротивляясь переменам, ты блокируешь результат."
    },
    "Справедливость": {
        "upright": "⚖️ КАРМА: {question} решится честно. Что посеял — то пожнёшь.",
        "reversed": "🎭 НЕСПРАВЕДЛИВОСТЬ: {question} несёт ложь. Будь бдителен."
    },
    "Повешенный": {
        "upright": "🔄 НОВЫЙ ВЗГЛЯД: {question} требует жертвы и паузы. Переверни ситуацию вверх ногами.",
        "reversed": "⛓️ ЗАСТРЕВАНИЕ: Ты в тупике {question}. Отпусти — и появится выход."
    },
    "Смерть": {
        "upright": "🐛➡️🦋 ТРАНСФОРМАЦИЯ: {question} завершает старый цикл. Это не конец, а рождение нового.",
        "reversed": "🌀 СОПРОТИВЛЕНИЕ: Страх перемен блокирует {question}. Умри для старого — возродись."
    },
    "Умеренность": {
        "upright": "⚖️ БАЛАНС: {question} решится через золотую середину. Терпение — твой ключ.",
        "reversed": "⚡ ДИСБАЛАНС: Эмоции в {question} зашкаливают. Найди покой."
    },
    "Дьявол": {
        "upright": "⛓️ ЗАВИСИМОСТЬ: {question} связан с твоей тенью. Иллюзия власти душит тебя.",
        "reversed": "🕊️ ОСВОБОЖДЕНИЕ: Ты рвёшь цепи {question}. Свобода близко!"
    },
    "Башня": {
        "upright": "💥 КРАХ: {question} разрушит иллюзии. Хаос очистит место для нового.",
        "reversed": "🏚️ ИЗБЕГАНИЕ: Кризис {question} отсрочен, но не отменён."
    },
    "Звезда": {
        "upright": "✨ НАДЕЖДА: {question} несёт исцеление. Мечты становятся реальностью.",
        "reversed": "🌑 БЕЗНАДЁЖНОСТЬ: {question} потерял свет. Верни веру в чудо."
    },
    "Луна": {
        "upright": "🌊 ИЛЛЮЗИИ: {question} скрыт в тумане. Доверяй снам и страхам — они укажут путь.",
        "reversed": "🔦 ПРОЗРЕНИЕ: Тайна {question} раскроется. Мрак рассеивается."
    },
    "Солнце": {
        "upright": "☀️ РАДОСТЬ: {question} осветит твою жизнь! Счастье и успех у дверей.",
        "reversed": "🌥️ ТЕНИ: Временные трудности в {question}. Солнце выглянет скоро."
    },
    "Суд": {
        "upright": "🎺 ПРОБУЖДЕНИЕ: {question} зовёт тебя к новой жизни. Второй шанс!",
        "reversed": "😴 СПЯЧКА: Ты упускаешь знаки в {question}. Проснись!"
    },
    "Мир": {
        "upright": "🏆 ЗАВЕРШЕНИЕ: {question} приведёт к целостности. Ты достиг цели.",
        "reversed": "🚧 НЕЗАВЕРШЁННОСТЬ: {question} не закрыт. Сделай последний шаг."
    }
}

# Добавляем младшие арканы (12 для краткости, но можно расширить)
minors = ["Туз Жезлов", "Туз Кубков", "Туз Мечей", "Туз Пентаклей"]
for minor in minors:
    cards[minor] = {
        "upright": f"⭐ {minor}: {minor.split()[1]} энергия приносит начало в {{question}}. Новый импульс!",
        "reversed": f"🌀 {minor} перевёрнутый: Задержка в {{question}}. Пересмотри подход."
    }

# =========================
# КЛАВИАТУРА ГЛАВНОГО МЕНЮ
# =========================
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🃏 Получить ответ", callback_data="ask")],
    [InlineKeyboardButton(text="💰 Купить вопросы", callback_data="buy")],
    [InlineKeyboardButton(text="📊 Мой баланс", callback_data="balance")],
    [InlineKeyboardButton(text="🎁 Бесплатный вопрос дня", callback_data="free")],
])

# Тарифы
tariffs = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔮 3 вопроса — 50 ₽", callback_data="3_50")],
    [InlineKeyboardButton(text="✨ 8 вопросов — 100 ₽", callback_data="8_100")],
    [InlineKeyboardButton(text="🌟 15 вопросов — 350 ₽", callback_data="15_350")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")],
])

# =========================
# ФУНКЦИИ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
# =========================
def get_user(user_id):
    data = load_data()
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "questions_left": 1,  # 1 бесплатный вопрос при регистрации
            "last_free_date": None,
            "total_asked": 0
        }
        save_data(data)
    return data["users"][str(user_id)]

def update_user(user_id, key, value):
    data = load_data()
    if str(user_id) not in data["users"]:
        get_user(user_id)
    data["users"][str(user_id)][key] = value
    save_data(data)

def can_get_free(user_id):
    user = get_user(user_id)
    last = user.get("last_free_date")
    if not last:
        return True
    last_date = datetime.fromisoformat(last)
    return datetime.now() - last_date >= timedelta(days=1)

def use_free_question(user_id):
    if can_get_free(user_id):
        update_user(user_id, "last_free_date", datetime.now().isoformat())
        return True
    return False

# =========================
# ГАДАНИЕ (КРАСОЧНАЯ ТРАКТОВКА)
# =========================
def draw_card_with_meaning(question):
    """Возвращает карту и трактовку с подстановкой вопроса"""
    card_name = random.choice(list(cards.keys()))
    is_reversed = random.choice([True, False])
    template = cards[card_name]["reversed" if is_reversed else "upright"]
    meaning = template.format(question=question)
    return card_name, "перевёрнутая" if is_reversed else "прямая", meaning

# =========================
# ОБРАБОТЧИКИ
# =========================
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    get_user(user_id)
    await message.answer(
        "🔮 **Добро пожаловать в Магическое Таро** 🔮\n\n"
        "Я помогу заглянуть в твоё будущее без ИИ — только древняя мудрость карт.\n\n"
        "✨ **Тарифы:**\n"
        "• 3 вопроса — 50 ₽\n"
        "• 8 вопросов — 100 ₽\n"
        "• 15 вопросов — 350 ₽\n\n"
        "🎁 **Бесплатный вопрос каждый день!**\n\n"
        "Выбери действие:",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔮 Главное меню:",
        reply_markup=main_menu
    )
    await callback.answer()

@dp.callback_query(F.data == "ask")
async def ask_question(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)
    if user["questions_left"] <= 0:
        await callback.message.answer(
            "❌ У тебя закончились вопросы!\n"
            "Купи новый пакет в меню → 💰 Купить вопросы"
        )
        await callback.answer()
        return
    await callback.message.answer(
        "📝 **Напиши свой вопрос**\n\n"
        "Примеры:\n"
        "• Что меня ждёт в любви?\n"
        "• Стоит ли менять работу?\n"
        "• Как ко мне относится Анна?\n\n"
        "Чем точнее вопрос — тем яснее ответ ✨"
    )
    await state.set_state(TarotState.waiting_question)
    await callback.answer()

@dp.message(TarotState.waiting_question)
async def do_tarot(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    question = message.text.strip()
    
    user = get_user(user_id)
    if user["questions_left"] <= 0:
        await message.answer("❌ Нет вопросов. Пополни баланс в меню.")
        await state.clear()
        return
    
    # Списываем вопрос
    update_user(user_id, "questions_left", user["questions_left"] - 1)
    update_user(user_id, "total_asked", user.get("total_asked", 0) + 1)
    
    # Получаем карту
    card_name, position, meaning = draw_card_with_meaning(question)
    
    # Составляем красивый ответ
    response = f"""
🔮 **Твой вопрос:** _{question}_

✨ **Выпала карта:** {card_name}
📌 **Положение:** {position}

{meaning}

💫 **Совет:** Доверься Вселенной, но не забывай про свои действия.

📊 Осталось вопросов: {user["questions_left"] - 1}
    """
    await message.answer(response, parse_mode="Markdown")
    await state.clear()
    
    # Предложение купить ещё
    if user["questions_left"] - 1 <= 0:
        await message.answer(
            "⚠️ Вопросы закончились! Купи новый пакет в меню.",
            reply_markup=main_menu
        )

@dp.callback_query(F.data == "free")
async def free_question_day(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if use_free_question(user_id):
        await callback.message.answer(
            "🎁 **Бесплатный вопрос дня активирован!**\n\n"
            "Напиши свой вопрос:"
        )
        await state.set_state(TarotState.waiting_question)
    else:
        await callback.message.answer(
            "❌ Ты уже использовал бесплатный вопрос сегодня.\n"
            "Вернись завтра или купи платные вопросы."
        )
    await callback.answer()

@dp.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    await callback.message.answer(
        f"📊 **Твой баланс:**\n\n"
        f"🎴 Осталось вопросов: {user['questions_left']}\n"
        f"📆 Всего задано: {user.get('total_asked', 0)}\n"
        f"🎁 Следующий бесплатный: завтра в {datetime.now().strftime('%H:%M')}"
    )
    await callback.answer()

@dp.callback_query(F.data == "buy")
async def buy_questions(callback: CallbackQuery):
    await callback.message.edit_text(
        "💸 **Выбери пакет вопросов:**\n"
        "После оплаты отправь скрин чека в этот чат\n\n"
        "💳 **Реквизиты Тинькофф:**\n"
        "По номеру телефона: `89512694834`\n\n"
        "Назначение платежа: `Вопросы Таро`\n\n"
        "✅ После оплаты администратор проверит и начислит вопросы.",
        reply_markup=tariffs,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith(("3_50", "8_100", "15_350")))
async def select_tariff(callback: CallbackQuery, state: FSMContext):
    tariff_map = {
        "3_50": (3, 50),
        "8_100": (8, 100),
        "15_350": (15, 350)
    }
    questions, price = tariff_map[callback.data]
    await state.update_data(pending_questions=questions, pending_price=price)
    await callback.message.answer(
        f"💳 **Ты выбрал {questions} вопросов за {price} ₽**\n\n"
        f"**Как оплатить:**\n"
        f"1. Переведи {price} ₽ на номер `89512694824` (Тинькофф)\n"
        f"2. В комментарии укажи свой Telegram ID: `{callback.from_user.id}`\n"
        f"3. Пришли **скрин чека** сюда\n\n"
        f"⏳ После проверки администратор добавит вопросы.\n"
        f"💬 Если возникли проблемы — напиши @support"
    )
    await callback.answer()

# =========================
# АДМИН-ПАНЕЛЬ
# =========================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещён.")
        return
    await message.answer(
        "👑 **Админ-панель**\n\n"
        "Команды:\n"
        "/add_questions [user_id] [количество] — добавить вопросы пользователю\n"
        "/give_free [user_id] — дать бесплатный вопрос\n"
        "/all_users — статистика\n"
        "/check_payment — обработать скрин чека"
    )

@dp.message(Command("add_questions"))
async def add_questions(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
        user = get_user(user_id)
        new_balance = user["questions_left"] + amount
        update_user(user_id, "questions_left", new_balance)
        await message.answer(f"✅ Пользователю {user_id} добавлено {amount} вопросов. Баланс: {new_balance}")
        await bot.send_message(user_id, f"🎉 Администратор добавил тебе {amount} вопросов! Приятного гадания ✨")
    except:
        await message.answer("❌ Формат: /add_questions user_id количество")

@dp.message(Command("all_users"))
async def all_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    users = data["users"]
    text = "📊 **Статистика пользователей:**\n\n"
    for uid, info in users.items():
        text += f"👤 {uid}: {info['questions_left']} вопросов, всего {info.get('total_asked', 0)}\n"
    await message.answer(text[:4000])

@dp.message(F.photo)
async def handle_screenshot(message: types.Message):
    """Админ получает скрин, проверяет и начисляет"""
    if message.from_user.id != ADMIN_ID:
        # Обычный пользователь отправил скрин
        await message.answer(
            "📸 Спасибо, скрин получен!\n"
            "Администратор проверит оплату в ближайшее время и начислит вопросы."
        )
        # Отправляем админу уведомление
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"📸 Новый скрин чека от пользователя @{message.from_user.username} (ID: {message.from_user.id})\n"
                f"Проверь оплату и начисли вопросы командой /add_questions {message.from_user.id} X"
            )
        return
    
    # Админ сам отправил скрин? Странно, но игнорируем
    await message.answer("Используй команду /add_questions для начисления")

# =========================
# ЗАПУСК
# =========================
async def main():
    print("✅ Бот Таро с оплатой запущен")
    print(f"🔐 Админ ID: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
