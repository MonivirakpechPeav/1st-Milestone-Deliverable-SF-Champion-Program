-- =============================================================================
-- Column-Level Security via Dynamic Data Masking
-- Edition required: Enterprise+
-- Layout: GOVERNANCE_DB.SECURITY (policies) | HR_DB.HR | FINANCE_DB.FIN (data)
-- Approach: Hybrid management (POLICY_ADMIN owns policies; object owners APPLY)
-- Sharing: Not applicable (no Secure Data Sharing -> no CURRENT_ACCOUNT() guard)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Pre-flight: confirm edition (must be Enterprise or higher)
-- -----------------------------------------------------------------------------
-- SHOW PARAMETERS LIKE 'EDITION' IN ACCOUNT;  -- run as ACCOUNTADMIN, expect ENTERPRISE/BUSINESS_CRITICAL/VPS

USE ROLE ACCOUNTADMIN;

-- -----------------------------------------------------------------------------
-- 1. Roles
--    POLICY_ADMIN: creates and owns all masking policies (single source of truth).
--    HR_ADMIN    : owner of HR data; receives APPLY on HR-relevant policies only.
--    FINANCE_ADMIN: owner of finance data; receives APPLY on finance-relevant policies only.
--    DATA_ANALYST: default analyst that should see MASKED output.
-- -----------------------------------------------------------------------------
CREATE ROLE IF NOT EXISTS POLICY_ADMIN
    COMMENT = 'Owns all masking policies; gates apply/unset via APPLY grants.';
CREATE ROLE IF NOT EXISTS HR_ADMIN;
CREATE ROLE IF NOT EXISTS FINANCE_ADMIN;
CREATE ROLE IF NOT EXISTS DATA_ANALYST;

GRANT ROLE POLICY_ADMIN  TO ROLE SECURITYADMIN;
GRANT ROLE HR_ADMIN      TO ROLE SECURITYADMIN;
GRANT ROLE FINANCE_ADMIN TO ROLE SECURITYADMIN;

-- -----------------------------------------------------------------------------
-- 2. Databases / schemas. Policies live in GOVERNANCE_DB.SECURITY.
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS GOVERNANCE_DB;
CREATE SCHEMA   IF NOT EXISTS GOVERNANCE_DB.SECURITY
    COMMENT = 'Central home for masking, row-access, projection policies.';

CREATE DATABASE IF NOT EXISTS HR_DB;
CREATE SCHEMA   IF NOT EXISTS HR_DB.HR;

CREATE DATABASE IF NOT EXISTS FINANCE_DB;
CREATE SCHEMA   IF NOT EXISTS FINANCE_DB.FIN;

-- -----------------------------------------------------------------------------
-- 3. Privilege model (hybrid)
--    - POLICY_ADMIN: OWNERSHIP on the policy schema -> creates/alters/drops policies.
--    - HR_ADMIN / FINANCE_ADMIN: USAGE only + APPLY on the specific policies they need.
--    - APPLY MASKING POLICY on ACCOUNT is NOT granted to object owners; this prevents
--      them from unsetting policies without POLICY_ADMIN's consent.
-- -----------------------------------------------------------------------------
GRANT USAGE ON DATABASE GOVERNANCE_DB                 TO ROLE POLICY_ADMIN;
GRANT USAGE ON SCHEMA   GOVERNANCE_DB.SECURITY        TO ROLE POLICY_ADMIN;
GRANT CREATE MASKING POLICY ON SCHEMA GOVERNANCE_DB.SECURITY TO ROLE POLICY_ADMIN;
GRANT OWNERSHIP ON SCHEMA GOVERNANCE_DB.SECURITY      TO ROLE POLICY_ADMIN COPY CURRENT GRANTS;

-- Object owners need to *reference* the policy schema to apply policies stored there.
GRANT USAGE ON DATABASE GOVERNANCE_DB          TO ROLE HR_ADMIN;
GRANT USAGE ON SCHEMA   GOVERNANCE_DB.SECURITY TO ROLE HR_ADMIN;
GRANT USAGE ON DATABASE GOVERNANCE_DB          TO ROLE FINANCE_ADMIN;
GRANT USAGE ON SCHEMA   GOVERNANCE_DB.SECURITY TO ROLE FINANCE_ADMIN;

-- Data ownership.
GRANT OWNERSHIP ON DATABASE HR_DB           TO ROLE HR_ADMIN      COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA   HR_DB.HR        TO ROLE HR_ADMIN      COPY CURRENT GRANTS;
GRANT OWNERSHIP ON DATABASE FINANCE_DB      TO ROLE FINANCE_ADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA   FINANCE_DB.FIN  TO ROLE FINANCE_ADMIN COPY CURRENT GRANTS;

-- Read role.
GRANT USAGE ON DATABASE HR_DB              TO ROLE DATA_ANALYST;
GRANT USAGE ON SCHEMA   HR_DB.HR           TO ROLE DATA_ANALYST;
GRANT USAGE ON DATABASE FINANCE_DB         TO ROLE DATA_ANALYST;
GRANT USAGE ON SCHEMA   FINANCE_DB.FIN     TO ROLE DATA_ANALYST;

-- -----------------------------------------------------------------------------
-- 4. Create masking policies (POLICY_ADMIN).
--    Format = fixed-string redaction. Authorized: ACCOUNTADMIN, SECURITYADMIN,
--    plus HR_ADMIN for HR-scoped data. Everyone else gets the literal mask.
--    Use OR REPLACE carefully -- it preserves existing applications but resets
--    the body. Do NOT use FORCE unless you intend to overwrite a different
--    return type, since it can drop existing column references.
-- -----------------------------------------------------------------------------
USE ROLE POLICY_ADMIN;
USE SCHEMA GOVERNANCE_DB.SECURITY;

-- 4a. STRING PII (name, address, phone) - HR-scope visible to HR_ADMIN.
CREATE OR REPLACE MASKING POLICY MP_PII_STRING_HR AS
    (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN','SECURITYADMIN','HR_ADMIN') THEN val
        ELSE '***MASKED***'
    END
    COMMENT = 'Fixed-string redaction for HR PII strings.';

-- 4b. EMAIL (HR scope).
CREATE OR REPLACE MASKING POLICY MP_EMAIL_HR AS
    (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN','SECURITYADMIN','HR_ADMIN') THEN val
        ELSE '***MASKED***'
    END
    COMMENT = 'Fixed-string redaction for HR email addresses.';

-- 4c. SSN / national ID (HR scope).
CREATE OR REPLACE MASKING POLICY MP_SSN_HR AS
    (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN','SECURITYADMIN','HR_ADMIN') THEN val
        ELSE '***MASKED***'
    END
    COMMENT = 'Fixed-string redaction for SSN.';

-- 4d. SALARY / numeric financial (HR scope - HR.EMPLOYEES.SALARY).
--     NOTE: data type of policy must match column. Fixed-string redaction
--     of a NUMBER must use NULL or 0; we return NULL for non-authorized roles.
CREATE OR REPLACE MASKING POLICY MP_SALARY_HR AS
    (val NUMBER) RETURNS NUMBER ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN','SECURITYADMIN','HR_ADMIN') THEN val
        ELSE NULL  -- numeric fixed-string equivalent
    END
    COMMENT = 'Salary masking; NULL for unauthorized (numeric "fixed string" equivalent).';

-- 4e. CREDIT CARD / PAN (Finance scope - admins only here since FINANCE_ADMIN
--     was not selected as unmasked; tighten/loosen by editing role list).
CREATE OR REPLACE MASKING POLICY MP_PAN_FIN AS
    (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN','SECURITYADMIN') THEN val
        ELSE '***MASKED***'
    END
    COMMENT = 'Fixed-string redaction for PAN/credit card.';

-- 4f. PHI (HR scope).
CREATE OR REPLACE MASKING POLICY MP_PHI_HR AS
    (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN','SECURITYADMIN','HR_ADMIN') THEN val
        ELSE '***MASKED***'
    END
    COMMENT = 'Fixed-string redaction for PHI fields.';

-- -----------------------------------------------------------------------------
-- 5. Grant APPLY on each policy to the relevant object owner.
--    Object owner can SET/UNSET *this specific policy* on columns they own,
--    but cannot CREATE / ALTER / DROP the policy itself.
-- -----------------------------------------------------------------------------
GRANT APPLY ON MASKING POLICY GOVERNANCE_DB.SECURITY.MP_PII_STRING_HR TO ROLE HR_ADMIN;
GRANT APPLY ON MASKING POLICY GOVERNANCE_DB.SECURITY.MP_EMAIL_HR      TO ROLE HR_ADMIN;
GRANT APPLY ON MASKING POLICY GOVERNANCE_DB.SECURITY.MP_SSN_HR        TO ROLE HR_ADMIN;
GRANT APPLY ON MASKING POLICY GOVERNANCE_DB.SECURITY.MP_SALARY_HR     TO ROLE HR_ADMIN;
GRANT APPLY ON MASKING POLICY GOVERNANCE_DB.SECURITY.MP_PHI_HR        TO ROLE HR_ADMIN;
GRANT APPLY ON MASKING POLICY GOVERNANCE_DB.SECURITY.MP_PAN_FIN       TO ROLE FINANCE_ADMIN;

-- -----------------------------------------------------------------------------
-- 6. Apply policies to existing tables.
--    Object owner runs this; they can only succeed for policies they hold APPLY on.
-- -----------------------------------------------------------------------------
USE ROLE HR_ADMIN;

-- Example HR.EMPLOYEES table (create or skip if exists).
CREATE TABLE IF NOT EXISTS HR_DB.HR.EMPLOYEES (
    EMP_ID        NUMBER,
    FULL_NAME     STRING,
    EMAIL         STRING,
    PHONE         STRING,
    ADDRESS       STRING,
    SSN           STRING,
    SALARY        NUMBER(12,2),
    DIAGNOSIS     STRING        -- PHI
);

ALTER TABLE HR_DB.HR.EMPLOYEES MODIFY COLUMN
    FULL_NAME  SET MASKING POLICY GOVERNANCE_DB.SECURITY.MP_PII_STRING_HR,
    PHONE      SET MASKING POLICY GOVERNANCE_DB.SECURITY.MP_PII_STRING_HR,
    ADDRESS    SET MASKING POLICY GOVERNANCE_DB.SECURITY.MP_PII_STRING_HR,
    EMAIL      SET MASKING POLICY GOVERNANCE_DB.SECURITY.MP_EMAIL_HR,
    SSN        SET MASKING POLICY GOVERNANCE_DB.SECURITY.MP_SSN_HR,
    SALARY     SET MASKING POLICY GOVERNANCE_DB.SECURITY.MP_SALARY_HR,
    DIAGNOSIS  SET MASKING POLICY GOVERNANCE_DB.SECURITY.MP_PHI_HR;

USE ROLE FINANCE_ADMIN;

CREATE TABLE IF NOT EXISTS FINANCE_DB.FIN.PAYMENTS (
    PAYMENT_ID  NUMBER,
    CARD_PAN    STRING,
    AMOUNT      NUMBER(12,2)
);

ALTER TABLE FINANCE_DB.FIN.PAYMENTS MODIFY COLUMN
    CARD_PAN SET MASKING POLICY GOVERNANCE_DB.SECURITY.MP_PAN_FIN;

-- 6b. Apply at CREATE time (preferred for new tables) -- syntax sample:
-- CREATE TABLE HR_DB.HR.NEW_T (
--     EMAIL STRING WITH MASKING POLICY GOVERNANCE_DB.SECURITY.MP_EMAIL_HR
-- );

-- -----------------------------------------------------------------------------
-- 7. Views, materialized views, dynamic tables -- caveats
-- -----------------------------------------------------------------------------
-- VIEW: A masking policy on a base column is enforced when the view is queried.
--       You may also apply masking policies directly on view columns.
-- MATERIALIZED VIEW: You CANNOT create a materialized view on a column that has
--       a masking policy. Workaround: build the MV on non-sensitive columns, or
--       expose plain text via a secure view restricted by row access policies.
-- DYNAMIC TABLE: Same restriction -- a dynamic table refresh fails if a source
--       column carries a masking policy. Workaround: reference only non-masked
--       columns, or use a secure view downstream and apply masking to the
--       dynamic table's output columns.
--
-- Example secure view:
-- CREATE OR REPLACE SECURE VIEW HR_DB.HR.V_EMPLOYEES AS
--     SELECT EMP_ID, FULL_NAME, EMAIL FROM HR_DB.HR.EMPLOYEES;

-- -----------------------------------------------------------------------------
-- 8. Anti-patterns to avoid
-- -----------------------------------------------------------------------------
-- * Do NOT JOIN or filter on a masked column expecting predicate pushdown:
--     SELECT * FROM A JOIN B ON A.SSN = B.SSN     -- masked->masked compares masks
--     SELECT * FROM HR.EMPLOYEES WHERE EMAIL = 'a@b.com'  -- masked role gets 0 rows
--   Mask is applied BEFORE comparison for the running role.
-- * Do NOT grant APPLY MASKING POLICY ON ACCOUNT to object owners -- it lets
--   them unset policies on any column.
-- * Do NOT use ALTER MASKING POLICY ... SET BODY with FORCE unless the column
--   data type / signature of the policy matches; FORCE can re-attach to
--   incompatible columns and break queries.
-- * Always CREATE OR REPLACE in a deploy pipeline; never DROP+CREATE because
--   DROP fails if the policy is in use, and re-create loses APPLY grants.

-- -----------------------------------------------------------------------------
-- 9. Monitoring queries
-- -----------------------------------------------------------------------------
-- 9a. Account-wide policy references (latency up to 2h):
SELECT POLICY_DB, POLICY_SCHEMA, POLICY_NAME, POLICY_KIND,
       REF_DATABASE_NAME, REF_SCHEMA_NAME, REF_ENTITY_NAME,
       REF_COLUMN_NAME, REF_ARG_COLUMN_NAMES
FROM   SNOWFLAKE.ACCOUNT_USAGE.POLICY_REFERENCES
WHERE  POLICY_KIND = 'MASKING_POLICY'
ORDER  BY POLICY_NAME;

-- 9b. Real-time per-database policy coverage (matches the governance_agent
--     query in app/services/policies.py):
SELECT REF_SCHEMA_NAME AS TABLE_SCHEMA,
       REF_ENTITY_NAME AS TABLE_NAME,
       REF_COLUMN_NAME AS COLUMN_NAME,
       POLICY_NAME, POLICY_KIND
FROM   HR_DB.INFORMATION_SCHEMA.POLICY_REFERENCES
WHERE  POLICY_KIND = 'MASKING_POLICY'
ORDER  BY TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME;

-- 9c. Find sensitive columns NOT covered (gap analysis):
SELECT c.TABLE_CATALOG, c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE
FROM   HR_DB.INFORMATION_SCHEMA.COLUMNS c
LEFT   JOIN HR_DB.INFORMATION_SCHEMA.POLICY_REFERENCES p
       ON p.REF_ENTITY_NAME = c.TABLE_NAME
      AND p.REF_COLUMN_NAME = c.COLUMN_NAME
      AND p.POLICY_KIND     = 'MASKING_POLICY'
WHERE  c.COLUMN_NAME ILIKE ANY ('%SSN%','%EMAIL%','%PHONE%','%SALARY%','%PAN%','%CARD%')
  AND  p.POLICY_NAME IS NULL;

-- 9d. Who owns / can apply each policy:
SHOW GRANTS ON MASKING POLICY GOVERNANCE_DB.SECURITY.MP_EMAIL_HR;

-- -----------------------------------------------------------------------------
-- 10. Verification: prove masking works end-to-end
-- -----------------------------------------------------------------------------
-- Insert sample data (HR_ADMIN owns the table).
USE ROLE HR_ADMIN;
INSERT INTO HR_DB.HR.EMPLOYEES VALUES
    (1,'Jane Doe','jane@acme.com','555-0101','1 Main St','123-45-6789',125000.00,'HTN'),
    (2,'John Roe','john@acme.com','555-0102','2 Elm St','987-65-4321', 98000.00,'NONE');

-- Authorized: HR_ADMIN should see plaintext.
USE ROLE HR_ADMIN;
SELECT FULL_NAME, EMAIL, SSN, SALARY, DIAGNOSIS FROM HR_DB.HR.EMPLOYEES;
-- Expect: Jane Doe | jane@acme.com | 123-45-6789 | 125000.00 | HTN

-- Unauthorized: DATA_ANALYST should see fixed-string masks (and NULL salary).
GRANT SELECT ON TABLE HR_DB.HR.EMPLOYEES TO ROLE DATA_ANALYST;
USE ROLE DATA_ANALYST;
SELECT FULL_NAME, EMAIL, SSN, SALARY, DIAGNOSIS FROM HR_DB.HR.EMPLOYEES;
-- Expect: ***MASKED*** | ***MASKED*** | ***MASKED*** | NULL | ***MASKED***

-- -----------------------------------------------------------------------------
-- 11. Safe replace pattern (for evolving policy bodies)
-- -----------------------------------------------------------------------------
-- Preferred: CREATE OR REPLACE keeps existing column attachments AS LONG AS the
-- signature (input/return data types) is unchanged. Changing the signature
-- requires UNSET on all columns first; consider FORCE only after auditing
-- POLICY_REFERENCES for every dependent column.
--
-- USE ROLE POLICY_ADMIN;
-- CREATE OR REPLACE MASKING POLICY GOVERNANCE_DB.SECURITY.MP_EMAIL_HR AS
--     (val STRING) RETURNS STRING -> CASE ... END;
-- =============================================================================
