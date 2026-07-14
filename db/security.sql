-- logs_security and limit_rate tables

CREATE TABLE IF NOT EXISTS logs_security (
    id           SERIAL PRIMARY KEY,
    endpoint     VARCHAR(255) NOT NULL,
    method       VARCHAR(10)  NOT NULL,
    attack_type  VARCHAR(50),
    blocked      BOOLEAN      NOT NULL DEFAULT FALSE,
    ip           VARCHAR(45)  NOT NULL,
    timestamp    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS limit_rate (
    id              SERIAL PRIMARY KEY,
    endpoint        VARCHAR(255) NOT NULL,
    ip              VARCHAR(45)  NOT NULL,
    request_count   INTEGER      NOT NULL DEFAULT 1,
    window_start    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    blocked_status  BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_limit_rate_ip_endpoint UNIQUE (ip, endpoint)
);
