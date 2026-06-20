-- Run this in the Supabase SQL Editor right after chunk0_create_tables.sql.
-- Fixes "permission denied for table ..." errors from the service_role key:
-- Supabase's automatic default-privilege grants didn't apply to these
-- tables, so service_role has no SELECT/INSERT rights yet despite bypassing
-- RLS. This grants access explicitly and sets default privileges so future
-- tables in the public schema (e.g. the Layer 3 research scratchpad) grant
-- to service_role automatically too.

grant usage on schema public to service_role;

grant all privileges on public.questions to service_role;
grant all privileges on public.reports to service_role;

alter default privileges in schema public
  grant all privileges on tables to service_role;
