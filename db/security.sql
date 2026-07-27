-- security_logs and rate_limit tables

CREATE TABLE IF NOT EXISTS security_logs (
    id           SERIAL PRIMARY KEY,
    endpoint     VARCHAR(255) NOT NULL,
    method       VARCHAR(10)  NOT NULL,
    attack_type  VARCHAR(50),
    blocked      BOOLEAN      NOT NULL DEFAULT FALSE,
    ip           VARCHAR(45)  NOT NULL,
    timestamp    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rate_limit (
    id              SERIAL PRIMARY KEY,
    endpoint        VARCHAR(255) NOT NULL,
    ip              VARCHAR(45)  NOT NULL,
    request_count   INTEGER      NOT NULL DEFAULT 1,
    window_start    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    blocked_status  BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_rate_limit_ip_endpoint UNIQUE (ip, endpoint)
);