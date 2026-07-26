-- ============================================================
-- WebHawk Database Schema
-- Backend Registry Table
-- ============================================================

-- backend_registration: the control plane for the product.
-- A developer who wants WebHawk to protect their app registers it here,
-- gets back a unique api_key, and the middleware uses that key to look up
-- which real backend (target_url) an allowed request should be forwarded to.
CREATE TABLE IF NOT EXISTS backend_registration (
    id           SERIAL PRIMARY KEY,
    service_name VARCHAR(255)  NOT NULL,
    target_url   VARCHAR(500)  NOT NULL,
    -- 'whk_live_' prefix (9 chars) + 32 hex chars = 41; 64 leaves headroom.
    api_key      VARCHAR(64)   UNIQUE NOT NULL,
    -- Lets a developer pause protection without deleting the registration.
    active       BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- No separate index on api_key is needed: the UNIQUE constraint above
-- already creates one automatically in Postgres, and api_key lookup is the
-- only read path the middleware uses on this table.