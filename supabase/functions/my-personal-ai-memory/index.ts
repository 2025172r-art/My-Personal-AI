import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const secretKeyMap = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}");
const SUPABASE_SECRET =
  secretKeyMap.default ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

const supabase = createClient(SUPABASE_URL, SUPABASE_SECRET, {
  auth: { persistSession: false, autoRefreshToken: false },
});

const EXPECTED_TOKEN_SHA256 = "3f779a7ddcc8bd2bd10bcc2fb5d741971fcf055579ff5f1cc4b3ceb34f111f8d";
const encoder = new TextEncoder();

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, apikey, x-app-token",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" },
  });
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}



function makeWikipediaSearchTerms(rawTerms: unknown): string[] {
  if (!Array.isArray(rawTerms)) return [];
  const terms: string[] = [];
  for (const raw of rawTerms.slice(0, 40)) {
    const term = String(raw ?? "").toLowerCase().replace(/[^a-z0-9ぁ-んァ-ン一-龥_-]/g, "");
    if (term.length >= 2 && term.length <= 40) terms.push(term);
  }
  return [...new Set(terms)].slice(0, 24);
}

function isUuid(value: unknown): value is string {
  return typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (request.method !== "POST") return jsonResponse({ error: "Method not allowed" }, 405);

  if (!SUPABASE_URL || !SUPABASE_SECRET) {
    console.error("Supabase server credentials are unavailable in Edge Function secrets.");
    return jsonResponse({ error: "Memory service is not configured" }, 503);
  }

  const suppliedToken = request.headers.get("x-app-token") ?? "";
  const suppliedHash = await sha256Hex(suppliedToken);
  if (!suppliedToken || suppliedHash !== EXPECTED_TOKEN_SHA256) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON" }, 400);
  }

  try {
    switch (body.action) {
      case "add_message": {
        if (body.session_id !== "personal-owner-default") return jsonResponse({ error: "Invalid session" }, 400);
        if (!["user", "assistant"].includes(String(body.role))) return jsonResponse({ error: "Invalid role" }, 400);
        const content = String(body.content ?? "");
        if (!content.trim() || content.length > 30000) return jsonResponse({ error: "Invalid message length" }, 400);
        const { error } = await supabase.from("chat_messages").insert({
          session_id: body.session_id, role: body.role, content,
        });
        if (error) throw error;
        return jsonResponse({ ok: true });
      }
      case "get_messages": {
        if (body.session_id !== "personal-owner-default") return jsonResponse({ error: "Invalid session" }, 400);
        const limit = Math.max(1, Math.min(Number(body.limit ?? 60), 60));
        const { data, error } = await supabase.from("chat_messages")
          .select("id,session_id,role,content,created_at")
          .eq("session_id", body.session_id)
          .order("created_at", { ascending: false })
          .limit(limit);
        if (error) throw error;
        return jsonResponse({ data: (data ?? []).reverse() });
      }
      case "add_memory": {
        const category = String(body.category ?? "その他").slice(0, 40);
        const content = String(body.content ?? "");
        if (!content.trim() || content.length > 5000) return jsonResponse({ error: "Invalid memory length" }, 400);
        const { error } = await supabase.from("memories").insert({ category, content });
        if (error) throw error;
        return jsonResponse({ ok: true });
      }
      case "get_memories": {
        const limit = Math.max(1, Math.min(Number(body.limit ?? 100), 100));
        const { data, error } = await supabase.from("memories")
          .select("id,category,content,created_at")
          .order("created_at", { ascending: false })
          .limit(limit);
        if (error) throw error;
        return jsonResponse({ data: data ?? [] });
      }
      case "delete_memory": {
        if (!isUuid(body.id)) return jsonResponse({ error: "Invalid memory ID" }, 400);
        const { error } = await supabase.from("memories").delete().eq("id", body.id);
        if (error) throw error;
        return jsonResponse({ ok: true });
      }

      case "upsert_wikipedia_pages": {
        if (!Array.isArray(body.pages) || body.pages.length < 1 || body.pages.length > 25) {
          return jsonResponse({ error: "Provide between 1 and 25 Wikipedia pages." }, 400);
        }
        const rows: Record<string, unknown>[] = [];
        for (const raw of body.pages as unknown[]) {
          if (!raw || typeof raw !== "object") continue;
          const page = raw as Record<string, unknown>;
          const language = String(page.language ?? "ja");
          const pageId = Number(page.page_id);
          const title = String(page.title ?? "").trim().slice(0, 300);
          const url = String(page.url ?? "").trim();
          const articleText = String(page.article_text ?? page.extract ?? "").trim().slice(0, 18000);
          if (!["ja", "en"].includes(language) || !Number.isSafeInteger(pageId) || pageId <= 0 ||
              !title || !articleText || !url.startsWith("https://" + language + ".wikipedia.org/")) {
            continue;
          }
          const revisionId = page.revision_id == null ? null : Number(page.revision_id);
          rows.push({
            language,
            page_id: pageId,
            title,
            url,
            article_text: articleText,
            revision_id: Number.isSafeInteger(revisionId) && (revisionId as number) > 0 ? revisionId : null,
            source_updated_at: page.source_updated_at ? String(page.source_updated_at) : null,
            license: String(page.license ?? "CC BY-SA 4.0").slice(0, 80),
            license_url: String(page.license_url ?? "https://creativecommons.org/licenses/by-sa/4.0/").slice(0, 300),
          });
        }

        if (rows.length === 0) return jsonResponse({ saved: 0 });
        const { data, error } = await supabase.from("wiki_knowledge")
          .upsert(rows, { onConflict: "language,page_id" })
          .select("page_id");
        if (error) throw error;
        return jsonResponse({ saved: data?.length ?? rows.length });
      }

      case "search_wikipedia_pages": {
        const terms = makeWikipediaSearchTerms(body.search_terms);
        if (terms.length === 0) return jsonResponse({ data: [] });
        const limit = Math.max(1, Math.min(Number(body.limit ?? 5), 10));
        const { data, error } = await supabase.rpc("search_wikipedia_knowledge", {
          search_terms: terms,
          result_limit: limit,
        });
        if (error) throw error;
        return jsonResponse({ data: data ?? [] });
      }

      case "get_wikipedia_stats": {
        const { count, error } = await supabase.from("wiki_knowledge")
          .select("page_id", { count: "exact", head: true });
        if (error) throw error;
        const { data: recent, error: recentError } = await supabase.from("wiki_knowledge")
          .select("fetched_at")
          .order("fetched_at", { ascending: false })
          .limit(1);
        if (recentError) throw recentError;
        return jsonResponse({
          count: count ?? 0,
          latest_fetched_at: recent?.[0]?.fetched_at ?? null,
        });
      }
      default:
        return jsonResponse({ error: "Unknown action" }, 400);
    }
  } catch (error) {
    console.error("Memory operation failed:", error);
    return jsonResponse({ error: "Memory operation failed" }, 500);
  }
});
