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
      default:
        return jsonResponse({ error: "Unknown action" }, 400);
    }
  } catch (error) {
    console.error("Memory operation failed:", error);
    return jsonResponse({ error: "Memory operation failed" }, 500);
  }
});
