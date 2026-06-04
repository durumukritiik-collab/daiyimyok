import { NextRequest, NextResponse } from "next/server";
import { tavily } from "@tavily/core";
import { groq } from "@/lib/groq";

const MODEL = "llama-3.3-70b-versatile";

const tv = tavily({ apiKey: process.env.TAVILY_API_KEY ?? "" });

// ─── Types ────────────────────────────────────────────────────────────────────

export interface UserProfile {
  job_title: string;
  location: string;
  skills: string[];
  experience_level: string;
  preferences: string[];
  salary_expectation?: string;
  work_type?: string;
  sector?: string;
}

export interface JobResult {
  url: string;
  title: string;
  company: string;
  location: string;
  salary?: string;
  work_type?: string;
  deadline?: string;
  apply_link: string;
  score: number;
  reason: string;
  missing_skills: string[];
  risk_flags: string[];
}

export interface ResearchResponse {
  jobs: JobResult[];
  profile: UserProfile;
  total_found: number;
  queries_used: string[];
  error?: string;
}

// ─── Step 1: Profile Extraction ───────────────────────────────────────────────

async function extractProfile(message: string): Promise<UserProfile> {
  const res = await groq.chat.completions.create({
    model: MODEL,
    temperature: 0,
    max_tokens: 400,
    messages: [
      {
        role: "system",
        content: `Kullanıcının iş arama mesajından profil çıkar. Sadece JSON döndür, başka hiçbir şey yazma.

{
  "job_title": "istenen meslek/pozisyon",
  "location": "şehir tercihi, yoksa 'Türkiye'",
  "skills": ["beceri1", "beceri2"],
  "experience_level": "junior/mid/senior",
  "preferences": ["kpss'siz", "uzaktan", "özel sektör" vb.],
  "salary_expectation": "belirtilmişse, yoksa boş string",
  "work_type": "remote/hybrid/onsite/any",
  "sector": "public/private/both"
}`,
      },
      { role: "user", content: message },
    ],
  });

  const text = res.choices[0].message.content ?? "{}";
  const match = text.match(/\{[\s\S]*\}/);
  if (!match) return { job_title: "", location: "Türkiye", skills: [], experience_level: "mid", preferences: [] };
  try { return JSON.parse(match[0]); } catch { return { job_title: "", location: "Türkiye", skills: [], experience_level: "mid", preferences: [] }; }
}

// ─── Step 2: Query Generation ─────────────────────────────────────────────────

async function generateQueries(profile: UserProfile): Promise<string[]> {
  const res = await groq.chat.completions.create({
    model: MODEL,
    temperature: 0.3,
    max_tokens: 300,
    messages: [
      {
        role: "system",
        content: `Türkiye iş piyasası için 5 farklı arama sorgusu üret. Sadece JSON array döndür.

Farklı kaynakları hedefle: kariyer.net, eleman.net, linkedin, iskur, şirket siteleri, genel arama.
Güncel sonuçlar için "2026" veya "iş ilanı" ekle.

Örnek: ["psikolog iş ilanı Antalya 2026", "klinik psikolog kariyer.net Antalya", ...]`,
      },
      {
        role: "user",
        content: `Profil: ${JSON.stringify(profile)}`,
      },
    ],
  });

  const text = res.choices[0].message.content ?? "[]";
  const match = text.match(/\[[\s\S]*?\]/);
  if (!match) return [`${profile.job_title} iş ilanı ${profile.location}`];
  try { return JSON.parse(match[0]).slice(0, 5); } catch { return [`${profile.job_title} iş ilanı ${profile.location}`]; }
}

// ─── Step 3: Parallel Search ──────────────────────────────────────────────────

interface RawResult {
  url: string;
  title: string;
  content: string;
}

async function searchAll(queries: string[]): Promise<RawResult[]> {
  const results = await Promise.allSettled(
    queries.map((q) =>
      tv.search(q, {
        maxResults: 5,
        searchDepth: "advanced",
      })
    )
  );

  return results
    .flatMap((r) => (r.status === "fulfilled" ? r.value.results ?? [] : []))
    .filter((r) => r.url && r.title && r.content)
    .map((r) => ({ url: r.url, title: r.title, content: r.content }));
}

// ─── Step 4: Deduplication ────────────────────────────────────────────────────

function deduplicate(results: RawResult[]): RawResult[] {
  const seen = new Set<string>();
  return results.filter((r) => {
    const key = r.url.split("?")[0].replace(/\/$/, "").toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

// ─── Step 5: Batch Scoring ────────────────────────────────────────────────────

async function scoreJobs(results: RawResult[], profile: UserProfile): Promise<JobResult[]> {
  if (!results.length) return [];

  const listText = results
    .map(
      (r, i) => `[${i + 1}]
Başlık: ${r.title}
URL: ${r.url}
İçerik: ${r.content.slice(0, 600)}`
    )
    .join("\n\n---\n\n");

  const res = await groq.chat.completions.create({
    model: MODEL,
    temperature: 0,
    max_tokens: 2500,
    messages: [
      {
        role: "system",
        content: `Sen kıdemli bir kariyer danışmanısın. Kullanıcı profiline göre iş ilanlarını değerlendir.

KURALLAR:
- Sadece gerçek iş ilanı olan sonuçları dahil et
- Haber, blog, forum, genel bilgi sayfalarını çıkar
- Kullanıcının şehriyle veya uzaktan uyuşmayanları çıkar
- 50 puan altındaki ilanları çıkar
- Maksimum 8 ilan döndür

Her ilan için JSON üret:
{
  "url": "string",
  "title": "pozisyon adı",
  "company": "şirket/kurum adı",
  "location": "şehir",
  "salary": "maaş bilgisi veya boş string",
  "work_type": "tam zamanlı/yarı zamanlı/uzaktan/hibrit",
  "deadline": "son başvuru tarihi veya boş string",
  "apply_link": "başvuru URL'i",
  "score": 0-100,
  "reason": "2-3 cümle neden uygun, kullanıcıya Sen diye hitap et",
  "missing_skills": ["eksik beceri listesi"],
  "risk_flags": ["dikkat edilmesi gereken nokta"]
}

Sonucu JSON array olarak döndür: [{ ... }, { ... }]
Başka hiçbir şey yazma.`,
      },
      {
        role: "user",
        content: `Kullanıcı profili:
${JSON.stringify(profile, null, 2)}

İlanlar:
${listText}`,
      },
    ],
  });

  const text = res.choices[0].message.content ?? "[]";
  const match = text.match(/\[[\s\S]*\]/);
  if (!match) return [];
  try {
    const parsed: JobResult[] = JSON.parse(match[0]);
    return parsed
      .filter((j) => j.score >= 50 && j.url && j.title)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8);
  } catch { return []; }
}

// ─── Main Handler ─────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  let message: string;
  try {
    const body = await req.json();
    message = body.message ?? "";
  } catch {
    return NextResponse.json({ error: "Geçersiz istek" }, { status: 400 });
  }

  if (!message.trim()) {
    return NextResponse.json({ error: "Mesaj boş olamaz" }, { status: 400 });
  }

  try {
    // 1. Profile
    const profile = await extractProfile(message);

    // 2. Queries
    const queries = await generateQueries(profile);

    // 3. Search (parallel)
    const raw = await searchAll(queries);

    // 4. Deduplicate
    const unique = deduplicate(raw);

    if (!unique.length) {
      return NextResponse.json<ResearchResponse>({
        jobs: [],
        profile,
        total_found: 0,
        queries_used: queries,
        error: "Sonuç bulunamadı. Farklı bir tanım deneyin.",
      });
    }

    // 5. Score top 15
    const toScore = unique.slice(0, 15);
    const jobs = await scoreJobs(toScore, profile);

    return NextResponse.json<ResearchResponse>({
      jobs,
      profile,
      total_found: unique.length,
      queries_used: queries,
    });

  } catch (e) {
    const msg = e instanceof Error ? e.message : "Bilinmeyen hata";

    if (msg.includes("429") || msg.toLowerCase().includes("rate limit")) {
      return NextResponse.json({ error: "AI servisi şu an yoğun. 1 dakika sonra tekrar deneyin." }, { status: 429 });
    }

    return NextResponse.json({ error: "Araştırma başarısız oldu. Lütfen tekrar deneyin." }, { status: 500 });
  }
}
