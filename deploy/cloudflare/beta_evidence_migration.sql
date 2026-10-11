-- Apply once to Neon before deploying the expanded feedback form.
ALTER TABLE beta_feedback ADD COLUMN IF NOT EXISTS test_details JSONB NOT NULL DEFAULT '{}';
