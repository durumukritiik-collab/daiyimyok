"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import Link from "next/link";

type Ilan = {
  id: string;
  title: string;
  organization: string;
  city: string;
  employment_type: string;
  application_deadline: string;
  kontenjan: string;
  mezuniyet_seviyesi: string;
  kpss_puan: string;
  source: string;
  is_active: boolean;
};

const MEZUNIYET = ["Lise", "Önlisans", "Lisans", "Yüksek Lisans", "Doktora"];
const ISTIHDAM = ["Memur", "Sözleşmeli", "Sürekli İşçi", "Akademik"];

const sb = createClient();

export default function IlanlarPage() {
  const [ilanlar, setIlanlar] = useState<Ilan[]>([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);
  const [arama, setArama] = useState("");
  const [mezSeviye, setMezSeviye] = useState("");
  const [istihdam, setIstihdam] = useState("");

  useEffect(() => {
    const t = setTimeout(() => fetchIlanlar(), 300);
    return () => clearTimeout(t);
  }, [arama, mezSeviye, istihdam]); // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchIlanlar() {
    setYukleniyor(true);
    setHata(null);

    let sorgu = sb
      .from("jobs")
      .select("id,title,organization,city,employment_type,application_deadline,kontenjan,mezuniyet_seviyesi,kpss_puan,source,is_active")
      .eq("is_active", true)
      .order("created_at", { ascending: false })
      .limit(100);

    if (arama.trim()) {
      // Türkçe karakter normalize: İ→i, Ş→s, Ğ→g, Ç→c vb.
      const norm = arama.trim()
        .replace(/İ/g, "i").replace(/I/g, "i")
        .replace(/Ş/g, "ş").replace(/Ğ/g, "ğ")
        .replace(/Ç/g, "ç").replace(/Ö/g, "ö").replace(/Ü/g, "ü")
        .toLowerCase();
      const q = `%${norm}%`;
      // arama_etiketleri ve mezuniyet lowercase — ilike doğrudan çalışır
      // title ve organization için tr_lower() fonksiyonu gerekiyor ama
      // Supabase JS SDK rpc() çağrısı karmaşık olduğundan
      // arama_etiketleri öncelikli, title fallback olarak kalır
      sorgu = sorgu.or(
        `arama_etiketleri.ilike.${q},mezuniyet.ilike.${q},title.ilike.${q},organization.ilike.${q}`
      );
    }
    if (mezSeviye) sorgu = sorgu.eq("mezuniyet_seviyesi", mezSeviye);
    if (istihdam) sorgu = sorgu.ilike("employment_type", `%${istihdam}%`);

    const { data, error } = await sorgu;
    if (error) setHata(error.message);
    setIlanlar(data || []);
    setYukleniyor(false);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8">

        {/* Başlık */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Kamu İş İlanları</h1>
          <p className="text-sm text-gray-500">Günlük güncellenir · {!yukleniyor && `${ilanlar.length} ilan`}</p>
        </div>

        {/* Arama + Filtreler */}
        <div className="flex flex-col sm:flex-row gap-2 mb-6">
          <input
            type="text"
            placeholder="Bölüm, kurum veya pozisyon..."
            value={arama}
            onChange={(e) => setArama(e.target.value)}
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={mezSeviye}
            onChange={(e) => setMezSeviye(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="">Tüm mezuniyetler</option>
            {MEZUNIYET.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <select
            value={istihdam}
            onChange={(e) => setIstihdam(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="">Tüm türler</option>
            {ISTIHDAM.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>

        {/* İçerik */}
        {hata && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-4">
            Veri yüklenemedi: {hata}
          </div>
        )}

        {yukleniyor ? (
          <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-2/3 mb-2" />
                <div className="h-3 bg-gray-100 rounded w-1/3" />
              </div>
            ))}
          </div>
        ) : ilanlar.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <div className="text-4xl mb-3">🔍</div>
            <p className="font-medium">İlan bulunamadı</p>
            <p className="text-sm mt-1">Farklı arama terimleri deneyin</p>
          </div>
        ) : (
          <div className="space-y-3">
            {ilanlar.map((ilan) => (
              <Link
                key={ilan.id}
                href={`/ilanlar/${ilan.id}`}
                className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-400 hover:shadow-sm transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h2 className="font-semibold text-gray-900 truncate">{ilan.title}</h2>
                    <p className="text-sm text-gray-500 mt-0.5 truncate">{ilan.organization}</p>
                  </div>
                  <IstihlamBadge tip={ilan.employment_type} />
                </div>
                <div className="flex flex-wrap gap-3 mt-3 text-xs text-gray-400">
                  {ilan.city && <span>📍 {ilan.city}</span>}
                  {ilan.application_deadline && <span>📅 {ilan.application_deadline}</span>}
                  {ilan.kontenjan && <span>👥 {ilan.kontenjan} kişi</span>}
                  {ilan.mezuniyet_seviyesi && <span>🎓 {ilan.mezuniyet_seviyesi}</span>}
                  {ilan.kpss_puan && <span>📊 Min {ilan.kpss_puan}</span>}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function IstihlamBadge({ tip }: { tip: string }) {
  const renk = tip?.includes("Memur")
    ? "bg-blue-100 text-blue-700"
    : tip?.includes("Sözleşmeli")
    ? "bg-purple-100 text-purple-700"
    : tip?.includes("İşçi")
    ? "bg-orange-100 text-orange-700"
    : tip?.includes("Akademik")
    ? "bg-green-100 text-green-700"
    : "bg-gray-100 text-gray-600";

  return (
    <span className={`shrink-0 text-xs px-2 py-1 rounded-full font-medium ${renk}`}>
      {tip || "Kamu"}
    </span>
  );
}
