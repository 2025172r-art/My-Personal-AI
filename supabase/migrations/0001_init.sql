-- My Personal AI: private server-side tables.
-- Keep the Supabase secret/service-role key only in Streamlit server Secrets.

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id text not null,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists chat_messages_session_created_idx
  on public.chat_messages (session_id, created_at desc);

create table if not exists public.memories (
  id uuid primary key default gen_random_uuid(),
  category text not null default 'その他',
  content text not null,
  created_at timestamptz not null default now()
);

-- First version is for one owner. No anon/authenticated table access is granted.
-- The app server uses a server-side secret key. Never put it in browser code or GitHub.
alter table public.chat_messages enable row level security;
alter table public.memories enable row level security;

revoke all on table public.chat_messages from anon, authenticated;
revoke all on table public.memories from anon, authenticated;
grant select, insert, delete on public.chat_messages to service_role;
grant select, insert, delete on public.memories to service_role;
