import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


API_URL = "https://api.stackexchange.com/2.3/questions"

START_DATE = datetime(
    2026,
    1,
    1,
    tzinfo=timezone.utc,
)

END_DATE = datetime(
    2026,
    1,
    7,
    tzinfo=timezone.utc,
)

PAGE_SIZE = 100

OUTPUT_DIRECTORY = Path(
    "data/raw/questions"
)


# Создаём папку для сырых вопросов,
# если её ещё нет
OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


# Удаляем старые страницы перед новой загрузкой,
# чтобы старые и новые результаты не смешивались
old_file_paths = list(
    OUTPUT_DIRECTORY.glob(
        "questions_*.json"
    )
)

for old_file_path in old_file_paths:
    old_file_path.unlink()


print(
    "Удалено старых файлов: "
    f"{len(old_file_paths)}"
)


current_date = START_DATE

total_questions = 0
request_count = 0
quota_remaining = None


# Последовательно проходим каждый день
# с 1 по 7 января включительно
while current_date <= END_DATE:
    next_date = (
        current_date
        + timedelta(days=1)
    )

    # Начало текущего дня
    from_date = current_date

    # Конец текущего дня:
    # следующая дата минус одна секунда
    to_date = (
        next_date
        - timedelta(seconds=1)
    )

    page = 1

    # Загружаем все страницы текущего дня
    while True:
        params = {
            "site": "stackoverflow",
            "page": page,
            "pagesize": PAGE_SIZE,
            "sort": "creation",
            "order": "asc",
            "fromdate": int(
                from_date.timestamp()
            ),
            "todate": int(
                to_date.timestamp()
            ),
        }

        response = requests.get(
            API_URL,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        questions = data.get(
            "items",
            [],
        )

        quota_remaining = data.get(
            "quota_remaining"
        )

        date_string = (
            current_date
            .date()
            .isoformat()
        )

        output_path = (
            OUTPUT_DIRECTORY
            / (
                f"questions_{date_string}"
                f"_page_{page}.json"
            )
        )

        with output_path.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        total_questions += len(questions)
        request_count += 1

        print(
            f"{date_string}, "
            f"страница {page}: "
            f"получено вопросов "
            f"{len(questions)}"
        )

        print(
            f"Файл сохранён: "
            f"{output_path}"
        )

        # Иногда API просит сделать паузу
        backoff = data.get("backoff")

        if backoff is not None:
            print(
                "API попросил подождать "
                f"{backoff} секунд"
            )

            time.sleep(backoff)

        # Если следующей страницы нет,
        # заканчиваем текущий день
        if not data.get(
            "has_more",
            False,
        ):
            break

        page += 1

    # Переходим к следующему дню
    current_date = next_date


print("\nЗагрузка завершена")

print(
    f"Всего запросов: "
    f"{request_count}"
)

print(
    "Всего получено вопросов: "
    f"{total_questions}"
)

print(
    "Осталось запросов: "
    f"{quota_remaining}"
)