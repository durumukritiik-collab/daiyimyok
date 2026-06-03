"use client";

import { useEffect, useState, useCallback } from "react";
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
  url: string;
  is_active: boolean;
};

const MEZUNIYET_SECENEKLER = ["Lise", "Önlisans", "Lisans", "Yüksek Lisans", "Doktora"];
const ISTIHDAM_SECENEKLER = ["Memur", "Sözleşmeli", "Sürekli İşçi", "Akademik"];

export default function IlanlarPage() {
  const [ilanlar, setIlanlar] = useState<Ilan[]>([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [arama, setArama] = useState("");
  const [mezSeviye, setMezSeviye] = useState("");
  const [istihdam, setIstihdam] = useState("");
  const sb = createClient();

  const getIlanlar = useCallback(async () => {
    setYukleniyor(true);
    let sorgu = sb
      .from("jobs")
      .select("id,title,organization,city,employment_type,application_deadline,kontenjan,mezuniyet_seviyesi,kpss_puan,source,url,is_active")
      .eq("is_active", true)
      .order("created_at", { ascending: false })
      .limit(100);

    if (arama.trim()) {
      sorgu = sorgu.textSearch("search_vector", arama.trim(), { config: "turkish" });
    }
    if (mezSeviye) {
      sorgu = sorgu.eq("mezuniyet_seviyesi", mezSeviye);
    }
    if (istihdam) {
      sorgu = sorgu.ilike("employment_type", `%${istihdam}%`);
    }

    const { data } = await sorgu;
    setIlanlar(data || []);
    setYukleniyor(false);
  }, [arama, mezSeviye, istihdam, sb]);

  useEffect(() => {
    const t = setTimeout(getIlanlar, 300);
    return () => clearTimeout(t);
  }, [getIlanlar]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Güncel Kamu İlanları</h1>

          {/* Arama + Filtreler */}
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Bölüm, kurum veya pozisyon ara..."
              value={arama}
              onChange={(e) => setArama(e.target.value)}
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={mezSeviye}
              onChange={(e) => setMezSeviye(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white"
            >
              <option value="">Tüm mezuniyetler</option>
              {MEZUNIYET_SECENEKLER.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <select
              value={istihdam}
              onChange={(e) => setIstihdam(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white"
            >
              <option value="">Tüm türler</option>
              {ISTIHDAM_SECENEKLER.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        {yukleniyor ? (
          <div className="text-center py-12 text-gray-500">Yükleniyor...</div>
        ) : ilanlar.length === 0 ? (
          <div className="text-center py-12 text-gray-500">İlan bulunamadı</div>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-4">{ilanlar.length} ilan listeleniyor</p>
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
                      <p className="text-sm text-gray-600 mt-0.5">{ilan.organization}</p>
                    </div>
                    <span className={`shrink-0 text-xs px-2 py-1 rounded-full font-medium ${
                      ilan.employment_type?.includes("Memur")
                        ? "bg-blue-100 text-blue-700"
                        : ilan.employment_type?.includes("Sözleşmeli")
                        ? "bg-purple-100 text-purple-700"
                        : ilan.employment_type?.includes("İşçi")
                        ? "bg-orange-100 text-orange-700"
                        : "bg-gray-100 text-gray-600"
                    }`}>
                      {ilan.employment_type || "Kamu"}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-3 mt-3 text-xs text-gray-500">
                    {ilan.application_deadline && (
                      <span>📅 {ilan.application_deadline}</span>
                    )}
                    {ilan.kontenjan && (
                      <span>👥 {ilan.kontenjan} kişi</span>
                    )}
                    {ilan.mezuniyet_seviyesi && (
                      <span>🎓 {ilan.mezuniyet_seviyesi}</span>
                    )}
                    {ilan.kpss_puan && (
                      <span>📊 KPSS min {ilan.kpss_puan}</span>
                    )}
                    {ilan.city && (
                      <span>📍 {ilan.city}</span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
