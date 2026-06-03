import { createClient } from "@supabase/supabase-js";

// Server-side only — API route'larda kullan
// Service key ile RLS bypass eder
export const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);
