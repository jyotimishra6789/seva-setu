-- Sewa Setu Old Age Pension Portal - schema
-- NOTE: seed.sql (shipped separately) loads after this and contains the
-- production data. Do not re-run against a live database.

CREATE TABLE IF NOT EXISTS applications (
    id              SERIAL PRIMARY KEY,
    application_no  VARCHAR(20),
    applicant_name  VARCHAR(100),
    mobile          VARCHAR(15),
    dob             DATE,
    gender          VARCHAR(10),
    marital_status  VARCHAR(20),
    husband_name    VARCHAR(100),
    husband_employer VARCHAR(100),
    village         VARCHAR(100),
    block           VARCHAR(50),
    bank_account    VARCHAR(30),
    ifsc            VARCHAR(15),
    doc_path        VARCHAR(200),
    status          VARCHAR(20) DEFAULT 'PENDING',
    submitted_at    TIMESTAMP,
    decided_at      TIMESTAMP,
    decided_by      VARCHAR(50)
);

ALTER TABLE applications ALTER COLUMN applicant_name TYPE TEXT;
ALTER TABLE applications ALTER COLUMN village TYPE TEXT;
ALTER TABLE applications ALTER COLUMN husband_name TYPE TEXT;
ALTER TABLE applications ALTER COLUMN husband_employer TYPE TEXT;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS applications_mobile_status_idx
    ON applications (mobile, status);
CREATE UNIQUE INDEX IF NOT EXISTS applications_active_mobile_uidx
    ON applications (mobile)
    WHERE status <> 'WITHDRAWN';
CREATE INDEX IF NOT EXISTS applications_status_submitted_idx
    ON applications (status, submitted_at);
CREATE INDEX IF NOT EXISTS applications_mobile_submitted_idx
    ON applications (mobile, submitted_at DESC);
CREATE INDEX IF NOT EXISTS applications_decided_at_idx
    ON applications (decided_at);

-- Status portal accounts (created at submission time)
CREATE TABLE IF NOT EXISTS portal_users (
    mobile        VARCHAR(15) PRIMARY KEY,
    password_hash TEXT
);

ALTER TABLE portal_users ALTER COLUMN password_hash TYPE TEXT;

CREATE TABLE IF NOT EXISTS otps (
    id         SERIAL PRIMARY KEY,
    mobile     VARCHAR(15),
    code       VARCHAR(6),
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS otps_mobile_created_idx
    ON otps (mobile, created_at DESC);

CREATE TABLE IF NOT EXISTS job_runs (
    id              BIGSERIAL PRIMARY KEY,
    job_name        VARCHAR(100) NOT NULL,
    started_at      TIMESTAMP NOT NULL,
    completed_at    TIMESTAMP,
    success         BOOLEAN NOT NULL DEFAULT FALSE,
    approved_count  INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS job_runs_name_started_idx
    ON job_runs (job_name, started_at DESC);
