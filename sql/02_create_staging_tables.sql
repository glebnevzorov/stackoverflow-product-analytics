CREATE TABLE IF NOT EXISTS staging.questions (
    question_id BIGINT PRIMARY KEY,
    author_id BIGINT,
    author_reputation BIGINT,
    author_type TEXT,
    creation_date TIMESTAMPTZ,
    last_activity_date TIMESTAMPTZ,
    last_edit_date TIMESTAMPTZ,
    score BIGINT,
    view_count BIGINT,
    answer_count BIGINT,
    is_answered BOOLEAN,
    accepted_answer_id BIGINT,
    title TEXT,
    link TEXT,
    content_license TEXT,
    has_any_answer BOOLEAN,
    has_accepted_answer BOOLEAN
);


CREATE TABLE IF NOT EXISTS staging.answers (
    answer_id BIGINT PRIMARY KEY,
    question_id BIGINT NOT NULL,
    answer_author_id BIGINT,
    answer_author_reputation BIGINT,
    answer_author_type TEXT,
    answer_created_at TIMESTAMPTZ,
    answer_last_activity_at TIMESTAMPTZ,
    answer_last_edit_at TIMESTAMPTZ,
    answer_score BIGINT,
    is_accepted BOOLEAN,
    content_license TEXT,
    question_author_id BIGINT,
    question_created_at TIMESTAMPTZ,
    is_self_answer BOOLEAN,

    CONSTRAINT fk_answers_question
        FOREIGN KEY (question_id)
        REFERENCES staging.questions (question_id)
);


CREATE TABLE IF NOT EXISTS staging.question_answer_metrics (
    question_id BIGINT PRIMARY KEY,
    question_author_id BIGINT,
    question_created_at TIMESTAMPTZ,
    first_any_answer_id BIGINT,
    first_any_answer_at TIMESTAMPTZ,
    first_external_answer_id BIGINT,
    first_external_answer_at TIMESTAMPTZ,
    hours_to_first_any_answer DOUBLE PRECISION,
    hours_to_first_external_answer DOUBLE PRECISION,
    received_any_answer_24h BOOLEAN,
    received_external_answer_24h BOOLEAN,

    CONSTRAINT fk_metrics_question
        FOREIGN KEY (question_id)
        REFERENCES staging.questions (question_id)
);


CREATE TABLE IF NOT EXISTS staging.user_questions (
    question_id BIGINT PRIMARY KEY,
    author_id BIGINT NOT NULL,
    creation_date TIMESTAMPTZ NOT NULL,
    post_state TEXT,
    title TEXT,
    tags JSONB,
    score BIGINT,
    answer_count BIGINT,
    is_answered BOOLEAN,
    link TEXT
);