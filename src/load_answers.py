import json
import time
from pathlib import Path

import pandas as pd
import requests


QUESTIONS_INPUT_PATH = Path(
    "data/processed/questions.parquet"
)

OUTPUT_DIRECTORY = Path(
    "data/raw/answers"
)

BATCH_SIZE = 100
PAGE_SIZE = 100


# Загружаем ID вопросов и количество ответов
questions_df = pd.read_parquet(
    QUESTIONS_INPUT_PATH,
    columns=[
        "question_id",
        "answer_count",
    ],
)


# Оставляем только вопросы, у которых есть ответы
question_ids = (
    questions_df.loc[
        questions_df["answer_count"]
        .fillna(0)
        .gt(0),
        "question_id",
    ]
    .dropna()
    .sort_values()
    .astype("int64")
    .astype(str)
    .tolist()
)


if not question_ids:
    raise ValueError(
        "Не найдено вопросов с ответами"
    )


OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


# Удаляем результаты предыдущего запуска,
# чтобы старые страницы не смешались с новыми
old_output_paths = list(
    OUTPUT_DIRECTORY.glob(
        "answers_batch_*.json"
    )
)

for old_output_path in old_output_paths:
    old_output_path.unlink()


total_batches = (
    len(question_ids) + BATCH_SIZE - 1
) // BATCH_SIZE

total_answers = 0
request_count = 0


# Делим question_id на пачки по 100
for batch_number, start_index in enumerate(
    range(
        0,
        len(question_ids),
        BATCH_SIZE,
    ),
    start=1,
):
    batch_question_ids = question_ids[
        start_index:start_index + BATCH_SIZE
    ]

    question_ids_string = ";".join(
        batch_question_ids
    )

    api_url = (
        "https://api.stackexchange.com/2.3/questions/"
        f"{question_ids_string}/answers"
    )

    page = 1

    # Загружаем все страницы текущей пачки
    while True:
        params = {
            "site": "stackoverflow",
            "page": page,
            "pagesize": PAGE_SIZE,
            "sort": "creation",
            "order": "asc",
        }

        response = requests.get(
            api_url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()
        answers = data.get("items", [])

        output_path = (
            OUTPUT_DIRECTORY
            / (
                f"answers_batch_{batch_number:03d}"
                f"_page_{page:03d}.json"
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

        total_answers += len(answers)
        request_count += 1

        print(
            f"Пачка {batch_number}/{total_batches}, "
            f"страница {page}: "
            f"получено ответов {len(answers)}"
        )

        print(
            f"Файл сохранён: {output_path}"
        )

        backoff = data.get("backoff")

        if backoff is not None:
            print(
                "API попросил подождать "
                f"{backoff} секунд"
            )

            time.sleep(backoff)

        if not data.get("has_more", False):
            break

        page += 1


print("\nЗагрузка завершена")
print(
    "Вопросов с ответами: "
    f"{len(question_ids)}"
)
print(f"Количество пачек: {total_batches}")
print(f"Всего запросов: {request_count}")
print(f"Всего получено ответов: {total_answers}")
print(
    "Осталось запросов: "
    f"{data.get('quota_remaining')}"
)