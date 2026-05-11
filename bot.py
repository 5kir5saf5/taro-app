import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

from tarot import draw_card

BOT_TOKEN = "ТВОЙ_ТОКЕН"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: types.Message):

    await message.answer(
        "🔮 Напиши вопрос для гадания"
    )


@dp.message()
async def reading(message: types.Message):

    card, status, meaning = draw_card()

    text = f"""
🃏 Карта: {card}
📌 Положение: {status}

✨ Значение:
{meaning}
"""

    await message.answer(text)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
