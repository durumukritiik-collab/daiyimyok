import { NextRequest, NextResponse } from "next/server";
import { groq, MODEL } from "@/lib/groq";
import { createClient } from "@/lib/supabase/server";
import fs from "fs";
import path from "path";

const SISTEM_PROMPT = fs.readFileSync(
  path.join(process.cwd(), "..", "groq_basvuru_prompt.txt"),
  "utf-8"
);

export async function POST(req: NextRequest) {
  const { job_id, profil } = await req.json();

  if (!job_id || !profil) {
    return NextResponse.json({ error: "job_id ve profil zorunlu" }, { status: 400 });
  }

  const sb = await createClient();
  const { data: ilan, error } = await sb
    .from("jobs")
    .select("title,organization,mezuniyet,kpss_sart,kpss_puan,yas_siniri,kontenjan,mezuniyet_seviyesi,tecrube,pozisyonlar_json,basvuru_sekli,application_deadline,arama_etiketleri")
    .eq("id", job_id)
    .single();

  if (error || !ilan) {
    return NextResponse.json({ error: "İlan bulunamadı" }, { status: 404 });
  }

  const kullanici_mesaj = `
KULLANICI PROFİLİ:
- Bölüm/Alan: ${profil.bolum || "belirtilmemiş"}
- Meslek: ${profil.meslek || "belirtilmemiş"}
- KPSS Puan Türü: ${profil.kpss_turu || "belirtilmemiş"}
- KPSS Puanı: ${profil.kpss_puan || "belirtilmemiş"}
- Yaş: ${profil.yas || "belirtilmemiş"}
- Mezuniyet Seviyesi: ${profil.mezuniyet_seviyesi || "belirtilmemiş"}
- Tecrübe (yıl): ${profil.tecrube_yil ?? "belirtilmemiş"}

İLAN BİLGİSİ:
- Başlık: ${ilan.title}
- Kurum: ${ilan.organization}
- Aranan Bölümler: ${ilan.mezuniyet || "belirtilmemiş"}
- KPSS Şartı: ${ilan.kpss_sart || "yok"}
- Min KPSS Puanı: ${ilan.kpss_puan || "belirtilmemiş"}
- Yaş Sınırı: ${ilan.yas_siniri || "yok"}
- Kontenjan: ${ilan.kontenjan || "belirtilmemiş"}
- Mezuniyet Seviyesi: ${ilan.mezuniyet_seviyesi || "belirtilmemiş"}
- Tecrübe Şartı: ${ilan.tecrube || "yok"}
- Başvuru Şekli: ${ilan.basvuru_sekli || "belirtilmemiş"}
- Son Başvuru: ${ilan.application_deadline || "belirtilmemiş"}
- Pozisyonlar (JSON): ${ilan.pozisyonlar_json || "yok"}
`;

  try {
    const tamamlama = await groq.chat.completions.create({
      model: MODEL,
      messages: [
        { role: "system", content: SISTEM_PROMPT },
        { role: "user", content: kullanici_mesaj },
      ],
      temperature: 0,
      max_tokens: 800,
    });

    const yanit = tamamlama.choices[0].message.content?.trim() || "";
    const jsonMatch = yanit.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json({ error: "Groq geçersiz yanıt döndürdü" }, { status: 500 });
    }

    const sonuc = JSON.parse(jsonMatch[0]);
    return NextResponse.json(sonuc);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Bilinmeyen hata";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
