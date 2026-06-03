"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useParams } from "next/navigation";
import Link from "next/link";

type Ilan = {
  id: string;
  title: string;
  organization: string;
  city: string;
  employment_type: string;
  application_deadline: string;
  kontenjan: string;
  mezuniyet: string;
  mezuniyet_seviyesi: string;
  kpss_sart: string;
  kpss_puan: string;
  yas_siniri: string;
  tecrube: string;
  basvuru_sekli: string;
  sinav_tarihi: string;
  url: string;
  arama_etiketleri: string;
  pozisyonlar_json: string;
  source: string;
};

type Profil = {
  bolum: string;
  kpss_turu: string;
  kpss_puan: string;
  yas: string;
  mezuniyet_seviyesi: string;
  tecrube_yil: string;
};

type Analiz = {
  uygun: boolean;
  skor: number;
  etiket: string;
  eksikler: string[];
  artilar: string[];
  tavsiyeler: string[];
  ozet: string;
};

const PROFIL_KEY = "daiyimyok_profil";
const BOSH_PROFIL: Profil = { bolum: "", kpss_turu: "", kpss_puan: "", yas: "", mezuniyet_seviyesi: "", tecrube_yil: "" };
const MEZ_SEVIYELERI = ["Lise", "Önlisans", "Lisans", "Yüksek Lisans", "Doktora"];

const sb = createClient();

export default function IlanDetayPage() {
  const { id } = useParams<{ id: string }>();
  const [ilan, setIlan] = useState<Ilan | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [profil, setProfil] = useState<Profil>(BOSH_PROFIL);
  const [analiz, setAnaliz] = useState<Analiz | null>(null);
  const [analizYukleniyor, setAnalizYukleniyor] = useState(false);
  const [analizHata, setAnalizHata] = useState<string | null>(null);

  useEffect(() => {
    sb.from("jobs")
      .select("id,title,organization,city,employment_type,application_deadline,kontenjan,mezuniyet,mezuniyet_seviyesi,kpss_sart,kpss_puan,yas_siniri,tecrube,basvuru_sekli,sinav_tarihi,url,arama_etiketleri,pozisyonlar_json,source")
      .eq("id", id)
      .single()
      .then(({ data }) => { setIlan(data); setYukleniyor(false); });

    const kayitli = localStorage.getItem(PROFIL_KEY);
    if (kayitli) setProfil(JSON.parse(kayitli));
  }, [id]);

  function profilGuncelle(alan: keyof Profil, deger: string) {
    const yeni = { ...profil, [alan]: deger };
    setProfil(yeni);
    localStorage.setItem(PROFIL_KEY, JSON.stringify(yeni));
  }

  async function analizYap() {
    if (!profil.bolum.trim()) {
      setAnalizHata("Bölüm alanını doldurun");
      return;
    }
    setAnalizYukleniyor(true);
    setAnalizHata(null);
    setAnaliz(null);

    try {
      const r = await fetch("/api/analiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: id, profil }),
      });
      const sonuc = await r.json();
      if (!r.ok) {
        // 429 için özel mesaj
        if (r.status === 429) {
          setAnalizHata("AI analiz servisi şu an yoğun. Birkaç dakika sonra tekrar deneyin.");
        } else {
          setAnalizHata(sonuc.error || "Analiz sırasında bir hata oluştu. Tekrar deneyin.");
        }
      } else {
        setAnaliz(sonuc);
      }
    } catch {
      setAnalizHata("Bağlantı hatası. İnternet bağlantınızı kontrol edip tekrar deneyin.");
    }
    setAnalizYukleniyor(false);
  }

  if (yukleniyor) return <Yukleniyor />;
  if (!ilan) return <Bulunamadi />;

  const etiketler = ilan.arama_etiketleri?.split(",").map(e => e.trim()).filter(Boolean) ?? [];
  let pozisyonlar: Record<string, string>[] = [];
  try { pozisyonlar = ilan.pozisyonlar_json ? JSON.parse(ilan.pozisyonlar_json) : []; } catch { /* */ }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-8">

        <Link href="/ilanlar" className="text-sm text-blue-600 hover:underline mb-5 inline-block">
          ← Tüm ilanlar
        </Link>

        {/* İlan Başlığı */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900">{ilan.title}</h1>
              <p className="text-gray-600 mt-1">{ilan.organization}</p>
              {ilan.city && <p className="text-sm text-gray-400 mt-0.5">📍 {ilan.city}</p>}
            </div>
            <a
              href={ilan.url}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Başvur →
            </a>
          </div>

          {/* Şart Kartları */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <SartKarti etiket="Son Başvuru" deger={ilan.application_deadline} renk="red" />
            <SartKarti etiket="Kontenjan" deger={ilan.kontenjan ? `${ilan.kontenjan} kişi` : ""} renk="blue" />
            <SartKarti etiket="Mezuniyet" deger={ilan.mezuniyet_seviyesi} renk="green" />
            <SartKarti etiket="Min KPSS" deger={ilan.kpss_puan} renk="purple" />
            <SartKarti etiket="Yaş Sınırı" deger={ilan.yas_siniri ? `Max ${ilan.yas_siniri}` : ""} renk="orange" />
            <SartKarti etiket="Sınav" deger={ilan.sinav_tarihi} renk="gray" />
          </div>

          {ilan.mezuniyet && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs text-gray-400 font-medium mb-1">ARANAN BÖLÜMLER</p>
              <p className="text-sm text-gray-700">{ilan.mezuniyet}</p>
            </div>
          )}
          {ilan.kpss_sart && (
            <div className="mt-3">
              <p className="text-xs text-gray-400 font-medium mb-1">KPSS ŞARTI</p>
              <p className="text-sm text-gray-700">{ilan.kpss_sart}</p>
            </div>
          )}
          {ilan.basvuru_sekli && (
            <div className="mt-3">
              <p className="text-xs text-gray-400 font-medium mb-1">BAŞVURU ŞEKLİ</p>
              <p className="text-sm text-gray-700">{ilan.basvuru_sekli}</p>
            </div>
          )}

          {etiketler.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-gray-100">
              {etiketler.map(e => (
                <span key={e} className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{e}</span>
              ))}
            </div>
          )}
        </div>

        {/* Pozisyonlar */}
        {pozisyonlar.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
            <h2 className="font-semibold text-gray-900 mb-3">Pozisyonlar ({pozisyonlar.length})</h2>
            <div className="space-y-2">
              {pozisyonlar.map((poz, i) => (
                <div key={i} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-sm font-medium text-gray-800">{String(poz.unvan ?? "")}</p>
                  {poz.bolum && <p className="text-xs text-gray-500 mt-0.5">{String(poz.bolum)}</p>}
                  <div className="flex flex-wrap gap-2 mt-1.5">
                    {poz.kontenjan && <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">{String(poz.kontenjan)} kişi</span>}
                    {poz.kpss_turu && <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">{String(poz.kpss_turu)} {poz.kpss_min ? `min ${String(poz.kpss_min)}` : ""}</span>}
                    {poz.yas_max && <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">max {String(poz.yas_max)} yaş</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Uygunluk Analizi */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Bu ilana uygun musun?</h2>

          {/* Mini Profil Formu */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            <div className="col-span-2 sm:col-span-1">
              <label className="text-xs text-gray-500 mb-1 block">Bölümünüz *</label>
              <input
                placeholder="ör: Psikoloji"
                value={profil.bolum}
                onChange={e => profilGuncelle("bolum", e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="col-span-2 sm:col-span-1">
              <label className="text-xs text-gray-500 mb-1 block">Mezuniyet seviyesi</label>
              <select
                value={profil.mezuniyet_seviyesi}
                onChange={e => profilGuncelle("mezuniyet_seviyesi", e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Seçin</option>
                {MEZ_SEVIYELERI.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">KPSS türü</label>
              <input
                placeholder="ör: P3"
                value={profil.kpss_turu}
                onChange={e => profilGuncelle("kpss_turu", e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">KPSS puanı</label>
              <input
                type="number"
                placeholder="ör: 78"
                value={profil.kpss_puan}
                onChange={e => profilGuncelle("kpss_puan", e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Yaş</label>
              <input
                type="number"
                placeholder="ör: 29"
                value={profil.yas}
                onChange={e => profilGuncelle("yas", e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Tecrübe (yıl)</label>
              <input
                type="number"
                placeholder="ör: 2"
                value={profil.tecrube_yil}
                onChange={e => profilGuncelle("tecrube_yil", e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {analizHata && (
            <p className="text-sm text-red-600 mb-3">{analizHata}</p>
          )}

          <button
            onClick={analizYap}
            disabled={analizYukleniyor}
            className="w-full bg-blue-600 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {analizYukleniyor ? "Analiz yapılıyor..." : "Analiz Et"}
          </button>

          {/* Analiz Sonucu */}
          {analiz && (
            <div className="mt-5 pt-5 border-t border-gray-100">
              <div className={`rounded-xl p-4 mb-4 ${analiz.uygun ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm font-semibold ${analiz.uygun ? "text-green-700" : "text-red-700"}`}>
                    {analiz.uygun ? "✅" : "❌"} {analiz.etiket}
                  </span>
                  <span className="text-2xl font-bold text-gray-800">{analiz.skor}<span className="text-sm text-gray-400">/100</span></span>
                </div>
                <p className="text-sm text-gray-700">{analiz.ozet}</p>
              </div>

              {analiz.artilar?.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-semibold text-green-700 mb-1.5">ARTILARIN</p>
                  <ul className="space-y-1">
                    {analiz.artilar.map((a, i) => <li key={i} className="text-sm text-gray-700 flex gap-2"><span className="text-green-500 shrink-0">✓</span>{a}</li>)}
                  </ul>
                </div>
              )}
              {analiz.eksikler?.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-semibold text-red-700 mb-1.5">EKSİKLERİN</p>
                  <ul className="space-y-1">
                    {analiz.eksikler.map((e, i) => <li key={i} className="text-sm text-gray-700 flex gap-2"><span className="text-red-500 shrink-0">✗</span>{e}</li>)}
                  </ul>
                </div>
              )}
              {analiz.tavsiyeler?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-blue-700 mb-1.5">TAVSİYELER</p>
                  <ul className="space-y-1">
                    {analiz.tavsiyeler.map((t, i) => <li key={i} className="text-sm text-gray-700 flex gap-2"><span className="text-blue-500 shrink-0">→</span>{t}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SartKarti({ etiket, deger, renk }: { etiket: string; deger: string; renk: string }) {
  if (!deger) return null;
  const renkler: Record<string, string> = {
    red: "bg-red-50 text-red-700",
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    purple: "bg-purple-50 text-purple-700",
    orange: "bg-orange-50 text-orange-700",
    gray: "bg-gray-50 text-gray-700",
  };
  return (
    <div className={`rounded-lg p-3 ${renkler[renk] ?? renkler.gray}`}>
      <p className="text-xs opacity-70 font-medium">{etiket}</p>
      <p className="text-sm font-semibold mt-0.5">{deger}</p>
    </div>
  );
}

function Yukleniyor() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="h-4 bg-gray-200 rounded w-24 mb-6 animate-pulse" />
      <div className="bg-white rounded-xl border p-6 animate-pulse space-y-3">
        <div className="h-6 bg-gray-200 rounded w-2/3" />
        <div className="h-4 bg-gray-100 rounded w-1/3" />
      </div>
    </div>
  );
}

function Bulunamadi() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-16 text-center">
      <p className="text-4xl mb-3">🔍</p>
      <p className="font-medium text-gray-700">İlan bulunamadı</p>
      <Link href="/ilanlar" className="text-sm text-blue-600 hover:underline mt-2 inline-block">← Tüm ilanlar</Link>
    </div>
  );
}
