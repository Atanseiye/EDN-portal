CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Preserve the existing PBKDF2-HMAC-SHA256 password format. Neon performs the
-- expensive derivation; the free Worker only sends a parameterized query.
CREATE OR REPLACE FUNCTION ednai_pbkdf2_sha256(password TEXT, salt BYTEA, iterations INTEGER)
RETURNS BYTEA LANGUAGE plpgsql STRICT AS $$
DECLARE
    key_bytes BYTEA := convert_to(password, 'UTF8');
    block BYTEA;
    accumulated BIT(256);
    round INTEGER;
    hex_result TEXT;
BEGIN
    IF iterations < 1 OR iterations > 1000000 THEN
        RAISE EXCEPTION 'Invalid password derivation iteration count';
    END IF;
    block := hmac(salt || decode('00000001', 'hex'), key_bytes, 'sha256');
    accumulated := ('x' || encode(block, 'hex'))::BIT(256);
    FOR round IN 2..iterations LOOP
        block := hmac(block, key_bytes, 'sha256');
        accumulated := accumulated # ('x' || encode(block, 'hex'))::BIT(256);
    END LOOP;
    SELECT string_agg(lpad(to_hex(substring(accumulated FROM position FOR 8)::BIT(8)::INTEGER), 2, '0'), '' ORDER BY position)
      INTO hex_result FROM generate_series(1, 256, 8) AS position;
    RETURN decode(hex_result, 'hex');
END;
$$;
