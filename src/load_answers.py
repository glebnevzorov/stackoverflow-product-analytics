import json
from pathlib import Path

import pandas as pd
import requests


QUESTIONS_PATH = Path(
    "data/processed/questions.parquet"
)

OUTPUT_DIRECTORY = Path("data/raw")


questions_df = pd.read_parquet(
    QUESTIONS_PATH
)

question_ids = (
    questions_df["question_id"]
    .dropna()
    .astype("int64")
    .astype(str)
    .tolist()
)

question_ids_string = ";".join(question_ids)

API_URL = (
    "https://api.stackexchange.com/2.3/questions/"
    f"{question_ids_string}/answers"
)

params = {
    "site": "stackoverflow",
    "page": 1,
    "pagesize": 100,
    "sort": "creation",
    "order": "asc",
}

response = requests.get(
    API_URL,
    params=params,
    timeout=30,
)

response.raise_for_status()

data = response.json()
answers = data["items"]

OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

output_path = (
    OUTPUT_DIRECTORY
    / "answers_2026-01-01_page_1.json"
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

print(f"Вопросов в запросе: {len(question_ids)}")
print(f"Получено ответов: {len(answers)}")
print(f"Файл сохранён: {output_path}")
print(f"Есть следующая страница: {data.get('has_more')}")
print(f"Осталось запросов: {data.get('quota_remaining')}")