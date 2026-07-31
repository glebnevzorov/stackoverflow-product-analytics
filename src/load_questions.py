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

OUTPUT_DIRECTORY = Path(
    "data/raw/questions"
)

OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


current_date = START_DATE

total_questions = 0
request_count = 0


while current_date <= END_DATE:
    next_date = current_date + timedelta(days=1)

    from_date = current_date
    to_date = next_date - timedelta(seconds=1)

    page = 1

    while True:
        params = {
            "site": "stackoverflow",
            "page": page,
            "pagesize": 100,
            "sort": "creation",
            "order": "asc",
            "fromdate": int(from_date.timestamp()),
            "todate": int(to_date.timestamp()),
        }

        response = requests.get(
            API_URL,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()
        questions = data.get("items", [])

        date_string = current_date.date().isoformat()

        output_path = (
            OUTPUT_DIRECTORY
            / f"questions_{date_string}_page_{page}.json"
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
            f"{date_string}, страница {page}: "
            f"получено вопросов {len(questions)}"
        )

        print(f"Файл сохранён: {output_path}")

        backoff = data.get("backoff")

        if backoff is not None:
            print(
                f"API попросил подождать "
                f"{backoff} секунд"
            )

            time.sleep(backoff)

        if not data.get("has_more", False):
            break

        page += 1

    current_date = next_date


print("\nЗагрузка завершена")
print(f"Всего запросов: {request_count}")
print(f"Всего получено вопросов: {total_questions}")
print(
    "Осталось запросов: "
    f"{data.get('quota_remaining')}"
)