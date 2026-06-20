-- Run this once in the Supabase Dashboard -> SQL Editor for this project.
-- Creates the two tables Chunk 0 needs. RLS is enabled with no public
-- policies, so only the service_role key (used by the agent) can read/write;
-- anon/authenticated clients are denied by default.

create table if not exists public.questions (
  id uuid primary key default gen_random_uuid(),
  text text not null,
  votes integer not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  content_md text not null,
  created_at timestamptz not null default now()
);

alter table public.questions enable row level security;
alter table public.reports enable row level security;
