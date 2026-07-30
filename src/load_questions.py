import json
from datetime import datetime, timezone
from pathlib import Path

import requests


API_URL = "https://api.stackexchange.com/2.3/questions"

from_date = datetime(
    2026,
    1,
    1,
    0,
    0,
    0,
    tzinfo=timezone.utc,
)

to_date = datetime(
    2026,
    1,
    1,
    23,
    59,
    59,
    tzinfo=timezone.utc,
)

params = {
    "site": "stackoverflow",
    "page": 1,
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
questions = data["items"]

output_directory = Path("data/raw")

output_directory.mkdir(
    parents=True,
    exist_ok=True,
)

output_path = (
    output_directory
    / "questions_2026-01-01_page_1.json"
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

print(f"Получено вопросов: {len(questions)}")
print(f"Файл сохранён: {output_path}")
print(f"Есть следующая страница: {data.get('has_more')}")
print(f"Осталось запросов: {data.get('quota_remaining')}")