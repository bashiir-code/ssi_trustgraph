-- Run once in the Supabase Dashboard -> SQL Editor.
-- Pointer-pattern scratchpad (Chunk 3): raw research text lives here,
-- keyed by a doc_id the agent generates; only doc_id + sources + a
-- compressed summary travel in LangGraph state.

create table if not exists public.research_scratchpad (
  id uuid primary key,
  sub_query text not null,
  raw_content text not null,
  sources jsonb not null default '[]'::jsonb,
  agent text not null,
  created_at timestamptz not null default now()
);

alter table public.research_scratchpad enable row level security;

grant all privileges on public.research_scratchpad to service_role;
