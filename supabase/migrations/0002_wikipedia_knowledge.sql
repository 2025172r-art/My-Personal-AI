-- Persistent, private cache of attributed Wikipedia article excerpts.
create table if not exists public.wiki_knowledge (
  language text not null check (language in ('ja', 'en')),
  page_id bigint not null check (page_id > 0),
  title text not null check (char_length(title) between 1 and 300),
  url text not null check (url like 'https://%wikipedia.org/%'),
  article_text text not null check (char_length(article_text) between 1 and 18000),
  revision_id bigint,
  source_updated_at timestamptz,
  license text not null default 'CC BY-SA 4.0',
  license_url text not null default 'https://creativecommons.org/licenses/by-sa/4.0/',
  fetched_at timestamptz not null default now(),
  primary key (language, page_id)
);

create index if not exists wiki_knowledge_language_fetched_idx
  on public.wiki_knowledge (language, fetched_at desc);
create index if not exists wiki_knowledge_title_idx
  on public.wiki_knowledge (lower(title));

alter table public.wiki_knowledge enable row level security;
revoke all on table public.wiki_knowledge from anon, authenticated;
grant select, insert, update, delete on table public.wiki_knowledge to service_role;

create or replace function public.search_wikipedia_knowledge(
  search_terms text[],
  result_limit integer default 5
)
returns table (
  language text,
  page_id bigint,
  title text,
  url text,
  article_text text,
  revision_id bigint,
  source_updated_at timestamptz,
  license text,
  license_url text,
  fetched_at timestamptz
)
language sql
stable
security invoker
set search_path = public
as $$
  with matches as (
    select
      w.*,
      (
        select count(*)
        from unnest(coalesce(search_terms, array[]::text[])) as terms(term)
        where length(terms.term) >= 2
          and strpos(lower(w.title), lower(terms.term)) > 0
      ) as title_score,
      (
        select count(*)
        from unnest(coalesce(search_terms, array[]::text[])) as terms(term)
        where length(terms.term) >= 2
          and strpos(lower(w.article_text), lower(terms.term)) > 0
      ) as body_score
    from public.wiki_knowledge as w
  )
  select
    m.language, m.page_id, m.title, m.url, m.article_text, m.revision_id,
    m.source_updated_at, m.license, m.license_url, m.fetched_at
  from matches as m
  where m.title_score + m.body_score > 0
  order by m.title_score desc, m.body_score desc, m.fetched_at desc
  limit greatest(1, least(coalesce(result_limit, 5), 10));
$$;

revoke all on function public.search_wikipedia_knowledge(text[], integer) from public, anon, authenticated;
grant execute on function public.search_wikipedia_knowledge(text[], integer) to service_role;
