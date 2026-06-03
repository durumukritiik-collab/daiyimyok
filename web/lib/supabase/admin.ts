import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_KEY;

if (!url || !key) {
  throw new Error("SUPABASE_SERVICE_KEY veya NEXT_PUBLIC_SUPABASE_URL eksik. Vercel env vars kontrol edin.");
}

// Server-side only — API route'larda kullan, client'a sızdırma
export const supabaseAdmin = createClient(url, key);
