import random

cards = {
    "Шут": {
        "upright": "Новые возможности, начало пути, свобода.",
        "reversed": "Необдуманные поступки, хаос, ошибки."
    },

    "Маг": {
        "upright": "Сила воли, контроль ситуации, уверенность.",
        "reversed": "Манипуляции, обман, сомнения."
    },

    "Смерть": {
        "upright": "Конец этапа, трансформация, обновление.",
        "reversed": "Страх перемен, застой."
    }
}


def draw_card():

    card = random.choice(list(cards.keys()))

    reversed_card = random.choice([True, False])

    if reversed_card:
        meaning = cards[card]["reversed"]
        status = "перевернутая"
    else:
        meaning = cards[card]["upright"]
        status = "прямая"

    return card, status, meaning
