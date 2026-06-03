import { NextRequest, NextResponse } from "next/server";
import { groq, MODEL } from "@/lib/groq";
import { supabaseAdmin } from "@/lib/supabase/admin";

const SISTEM_PROMPT = `Sen Türkiye kamu iş ilanları konusunda uzman bir kariyer danışmanısın.
Adın DayımYok. Görevin: kullanıcının profiline bakarak belirli bir ilana başvurup başvuramayacağını analiz etmek.

Sana iki şey verilecek:
1. KULLANICI PROFİLİ: bölüm, KPSS puan türü ve puanı, yaş, mezuniyet seviyesi
2. İLAN BİLGİSİ: başlık, kurum, şartlar

100 puan üzerinden değerlendir:
- Bölüm/mezuniyet uyumu: 40 puan
- KPSS uyumu: 30 puan
- Yaş uyumu: 15 puan
- Mezuniyet seviyesi: 10 puan
- Tecrübe: 5 puan

Akademik unvan (Profesör, Doçent, Dr. Öğr. Üyesi) gereken pozisyonlar için uygun: false yaz.

Sadece geçerli JSON döndür, başka hiçbir şey yazma:
{
  "uygun": true/false,
  "skor": 0-100,
  "etiket": "Mükemmel Uyum" | "Uygun" | "Kısmi Uyum" | "Uyumsuz",
  "eksikler": ["eksik 1"],
  "artilar": ["artı 1"],
  "tavsiyeler": ["tavsiye 1"],
  "ozet": "Kullanıcıya 2-3 cümle. 'Sen' diye hitap et. Net ve samimi ol."
}`;

function kullanicıHataMesaji(hata: unknown): { mesaj: string; kod: number } {
  const msg = hata instanceof Error ? hata.message : String(hata);

  if (msg.includes("429") || msg.toLowerCase().includes("rate limit")) {
    return {
      mesaj: "AI analiz servisi şu an yoğun. Birkaç dakika sonra tekrar deneyin.",
      kod: 429,
    };
  }
  if (msg.includes("timeout") || msg.includes("ETIMEDOUT") || msg.includes("ECONNRESET")) {
    return {
      mesaj: "Analiz zaman aşımına uğradı. İnternet bağlantınızı kontrol edip tekrar deneyin.",
      kod: 504,
    };
  }
  if (msg.includes("401") || msg.includes("403") || msg.includes("Unauthorized")) {
    return {
      mesaj: "AI servisi yapılandırma hatası. Lütfen daha sonra tekrar deneyin.",
      kod: 503,
    };
  }
  return {
    mesaj: "Analiz sırasında bir hata oluştu. Lütfen tekrar deneyin.",
    kod: 500,
  };
}

export async function POST(req: NextRequest) {
  let body: { job_id?: string; profil?: Record<string, string> };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Geçersiz istek formatı" }, { status: 400 });
  }

  const { job_id, profil } = body;

  if (!job_id) {
    return NextResponse.json({ error: "job_id zorunlu" }, { status: 400 });
  }
  if (!profil?.bolum?.trim()) {
    return NextResponse.json({ error: "Bölüm bilgisi zorunlu" }, { status: 400 });
  }

  const { data: ilan, error: dbError } = await supabaseAdmin
    .from("jobs")
    .select("title,organization,mezuniyet,kpss_sart,kpss_puan,yas_siniri,kontenjan,mezuniyet_seviyesi,tecrube,pozisyonlar_json,application_deadline,basvuru_sekli")
    .eq("id", job_id)
    .single();

  if (dbError || !ilan) {
    return NextResponse.json({ error: "İlan bulunamadı" }, { status: 404 });
  }

  const kullanici_mesaji = `KULLANICI PROFİLİ:
- Bölüm: ${profil.bolum}
- KPSS Türü: ${profil.kpss_turu || "belirtilmemiş"}
- KPSS Puanı: ${profil.kpss_puan || "belirtilmemiş"}
- Yaş: ${profil.yas || "belirtilmemiş"}
- Mezuniyet Seviyesi: ${profil.mezuniyet_seviyesi || "belirtilmemiş"}
- Tecrübe (yıl): ${profil.tecrube_yil || "belirtilmemiş"}

İLAN BİLGİSİ:
- Başlık: ${ilan.title}
- Kurum: ${ilan.organization}
- Aranan Bölümler: ${ilan.mezuniyet || "belirtilmemiş"}
- KPSS Şartı: ${ilan.kpss_sart || "yok"}
- Min KPSS: ${ilan.kpss_puan || "belirtilmemiş"}
- Yaş Sınırı: ${ilan.yas_siniri || "yok"}
- Kontenjan: ${ilan.kontenjan || "belirtilmemiş"}
- Mezuniyet: ${ilan.mezuniyet_seviyesi || "belirtilmemiş"}
- Tecrübe Şartı: ${ilan.tecrube || "yok"}
- Son Başvuru: ${ilan.application_deadline || "belirtilmemiş"}`;

  try {
    const completion = await groq.chat.completions.create({
      model: MODEL,
      messages: [
        { role: "system", content: SISTEM_PROMPT },
        { role: "user", content: kullanici_mesaji },
      ],
      temperature: 0,
      max_tokens: 600,
    });

    const yanit = completion.choices[0].message.content?.trim() ?? "";
    const match = yanit.match(/\{[\s\S]*\}/);

    if (!match) {
      return NextResponse.json(
        { error: "Analiz sonucu alınamadı. Lütfen tekrar deneyin." },
        { status: 500 }
      );
    }

    const sonuc = JSON.parse(match[0]);
    return NextResponse.json(sonuc);

  } catch (e) {
    const { mesaj, kod } = kullanicıHataMesaji(e);
    return NextResponse.json({ error: mesaj }, { status: kod });
  }
}
