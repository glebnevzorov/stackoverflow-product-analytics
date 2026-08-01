-- 1. Количество строк в таблицах

SELECT 'questions' AS table_name, COUNT(*) AS row_count
FROM staging.questions

UNION ALL

SELECT 'answers', COUNT(*)
FROM staging.answers

UNION ALL

SELECT 'question_answer_metrics', COUNT(*)
FROM staging.question_answer_metrics

UNION ALL

SELECT 'user_questions', COUNT(*)
FROM staging.user_questions;


-- Ожидаем:
-- questions                 746
-- answers                  1063
-- question_answer_metrics   746
-- user_questions            898


-- 2. Проверка дубликатов идентификаторов

SELECT
    COUNT(*) - COUNT(DISTINCT question_id)
        AS duplicate_question_ids
FROM staging.questions;

SELECT
    COUNT(*) - COUNT(DISTINCT answer_id)
        AS duplicate_answer_ids
FROM staging.answers;

SELECT
    COUNT(*) - COUNT(DISTINCT question_id)
        AS duplicate_metric_question_ids
FROM staging.question_answer_metrics;

SELECT
    COUNT(*) - COUNT(DISTINCT question_id)
        AS duplicate_user_question_ids
FROM staging.user_questions;

-- Везде ожидаем 0.


-- 3. Проверка обязательных значений

SELECT
    COUNT(*) FILTER (WHERE question_id IS NULL)
        AS missing_question_id,
    COUNT(*) FILTER (WHERE creation_date IS NULL)
        AS missing_creation_date,
    COUNT(*) FILTER (WHERE author_id IS NULL)
        AS missing_author_id
FROM staging.questions;

-- missing_question_id = 0
-- missing_creation_date = 0
-- missing_author_id = 7


SELECT
    COUNT(*) FILTER (WHERE answer_id IS NULL)
        AS missing_answer_id,
    COUNT(*) FILTER (WHERE question_id IS NULL)
        AS missing_question_id
FROM staging.answers;

-- Ожидаем 0 и 0.


SELECT
    COUNT(*) FILTER (WHERE question_id IS NULL)
        AS missing_question_id,
    COUNT(*) FILTER (WHERE author_id IS NULL)
        AS missing_author_id,
    COUNT(*) FILTER (WHERE creation_date IS NULL)
        AS missing_creation_date,
    COUNT(*) FILTER (WHERE post_state IS NULL)
        AS missing_post_state
FROM staging.user_questions;

-- Везде ожидаем 0.


-- 4. Проверка ответов без соответствующего вопроса

SELECT COUNT(*) AS answers_without_question
FROM staging.answers AS a
LEFT JOIN staging.questions AS q
    ON q.question_id = a.question_id
WHERE q.question_id IS NULL;

-- Ожидаем 0.


-- 5. Проверка метрик без соответствующего вопроса

SELECT COUNT(*) AS metrics_without_question
FROM staging.question_answer_metrics AS m
LEFT JOIN staging.questions AS q
    ON q.question_id = m.question_id
WHERE q.question_id IS NULL;

-- Ожидаем 0.


-- 6. Проверка состояний вопросов в истории авторов

SELECT
    post_state,
    COUNT(*) AS question_count
FROM staging.user_questions
GROUP BY post_state
ORDER BY question_count DESC;

-- Ожидаем только:
-- Published  898


-- 7. Проверка исходных вопросов в истории авторов

SELECT COUNT(*) AS cohort_questions_missing_from_history
FROM staging.questions AS q
LEFT JOIN staging.user_questions AS uq
    ON uq.question_id = q.question_id
WHERE q.author_id IS NOT NULL
  AND uq.question_id IS NULL;

-- Ожидаем 0.


-- 8. Проверка периодов данных

SELECT
    MIN(creation_date) AS minimum_date,
    MAX(creation_date) AS maximum_date
FROM staging.questions;

SELECT
    MIN(creation_date) AS minimum_date,
    MAX(creation_date) AS maximum_date
FROM staging.user_questions;