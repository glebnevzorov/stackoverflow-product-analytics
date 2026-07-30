import requests

API_URL = "https://api.stackexchange.com/2.3/questions"

params = {
    "site": "stackoverflow",
    "page": 1,
    "pagesize": 5,
    "sort": "creation",
    "order": "desc",
}

response = requests.get(
    API_URL,
    params=params,
    timeout=30,
)

response.raise_for_status()

data = response.json()
questions = data["items"]

print(f"Получено вопросов: {len(questions)}")
print(f"Максимальная квота: {data.get('quota_max')}")
print(f"Осталось запросов: {data.get('quota_remaining')}")
print(f"Есть следующая страница: {data.get('has_more')}")

print("\nПоследние вопросы:")

for question in questions:
    print(
        question["question_id"],
        question["title"],
    )




