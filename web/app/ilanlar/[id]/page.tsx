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
};

type Analiz = {
  uygun: boolean;
  skor: number;
  etiket: string;
  eksikler: string[];
  artilar: string[];
  tavsiyeler: string[];
  ozet: string;
  en_uygun_pozisyon?: string;
};

type Profil = {
  bolum?: string;
  meslek?: string;
  kpss_puan?: string;
  kpss_turu?: string;
  yas?: string;
  mezuniyet_seviyesi?: string;
  tecrube_yil?: string;
};

export default function IlanDetayPage() {
  const { id } = useParams<{ id: string }>();
  const [ilan, setIlan] = useState<Ilan | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [analiz, setAnaliz] = useState<Analiz | null>(null);
  const [analizYukleniyor, setAnalizYukleniyor] = useState(false);
  const [profil, setProfil] = useState<Profil>({});
  const [profilAcik, setProfilAcik] = useState(false);
  const sb = createClient();

  useEffect(() => {
    sb.from("jobs")
      .select("*")
      .eq("id", id)
      .single()
      .then(({ data }) => {
        setIlan(data);
        setYukleniyor(false);
      });

    // Kayıtlı profili localStorage'dan yükle
    const kayitli = localStorage.getItem("daiyimyok_profil");
    if (kayitli) setProfil(JSON.parse(kayitli));
  }, [id, sb]);

  const profilKaydet = (p: Profil) => {
    setProfil(p);
    localStorage.setItem("daiyimyok_profil", JSON.stringify(p));
  };

  const analizYap = async () => {
    if (!profil.bolum && !profil.meslek) {
      setProfilAcik(true);
      return;
    }
    setAnalizYukleniyor(true);
    try {
      const r = await fetch("/api/analiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: id, profil }),
      });
      const sonuc = await r.json();
      setAnaliz(sonuc);
    } catch {
      alert("Analiz sırasında bir hata oluştu.");
    }
    setAnalizYukleniyor(false);
  };

  if (yukleniyor) return <div className="p-8 text-center text-gray-500">Yükleniyor...</div>;
  if (!ilan) return <div className="p-8 text-center text-gray-500">İlan bulunamadı</div>;

  const pozisyonlar = ilan.pozisyonlar_json ? JSON.parse(ilan.pozisyonlar_json) : [];
  const etiketler = ilan.arama_etiketleri?.split(",").map((e) => e.trim()).filter(Boolean) || [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <Link href="/ilanlar" className="text-sm text-blue-600 hover:underline mb-4 inline-block">
          ← Tüm ilanlar
        </Link>

        {/* Başlık */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
          <h1 className="text-xl font-bold text-gray-900">{ilan.title}</h1>
          <p className="text-gray-600 mt-1">{ilan.organization}</p>
          {ilan.city && <p className="text-sm text-gray-500 mt-0.5">📍 {ilan.city}</p>}

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
            {ilan.application_deadline && (
              <div className="bg-red-50 rounded-lg p-3">
                <div className="text-xs text-red-500 font-medium">Son Başvuru</div>
                <div className="text-sm font-semibold text-red-700 mt-0.5">{ilan.application_deadline}</div>
              </div>
            )}
            {ilan.kontenjan && (
              <div className="bg-blue-50 rounded-lg p-3">
                <div className="text-xs text-blue-500 font-medium">Kontenjan</div>
                <div className="text-sm font-semibold text-blue-700 mt-0.5">{ilan.kontenjan} kişi</div>
              </div>
            )}
            {ilan.mezuniyet_seviyesi && (
              <div className="bg-green-50 rounded-lg p-3">
                <div className="text-xs text-green-500 font-medium">Mezuniyet</div>
                <div className="text-sm font-semibold text-green-700 mt-0.5">{ilan.mezuniyet_seviyesi}</div>
              </div>
            )}
            {ilan.kpss_puan && (
              <div className="bg-purple-50 rounded-lg p-3">
                <div className="text-xs text-purple-500 font-medium">Min KPSS</div>
                <div className="text-sm font-semibold text-purple-700 mt-0.5">{ilan.kpss_puan}</div>
              </div>
            )}
            {ilan.yas_siniri && (
              <div className="bg-orange-50 rounded-lg p-3">
                <div className="text-xs text-orange-500 font-medium">Yaş Sınırı</div>
                <div className="text-sm font-semibold text-orange-700 mt-0.5">Max {ilan.yas_siniri}</div>
              </div>
            )}
            {ilan.sinav_tarihi && (
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xs text-gray-500 font-medium">Sınav Tarihi</div>
                <div className="text-sm font-semibold text-gray-700 mt-0.5">{ilan.sinav_tarihi}</div>
              </div>
            )}
          </div>

          {ilan.mezuniyet && (
            <div className="mt-4">
              <div className="text-xs text-gray-500 font-medium mb-1">Aranan Bölümler</div>
              <p className="text-sm text-gray-700">{ilan.mezuniyet}</p>
            </div>
          )}
          {ilan.kpss_sart && (
            <div className="mt-3">
              <div className="text-xs text-gray-500 font-medium mb-1">KPSS Şartı</div>
              <p className="text-sm text-gray-700">{ilan.kpss_sart}</p>
            </div>
          )}
          {ilan.basvuru_sekli && (
            <div className="mt-3">
              <div className="text-xs text-gray-500 font-medium mb-1">Başvuru Şekli</div>
              <p className="text-sm text-gray-700">{ilan.basvuru_sekli}</p>
            </div>
          )}

          {etiketler.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-4">
              {etiketler.map((e) => (
                <span key={e} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{e}</span>
              ))}
            </div>
          )}

          <a
            href={ilan.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-block text-sm text-blue-600 hover:underline"
          >
            Resmi ilana git →
          </a>
        </div>

        {/* Pozisyonlar */}
        {pozisyonlar.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
            <h2 className="font-semibold text-gray-900 mb-3">Pozisyonlar ({pozisyonlar.length})</h2>
            <div className="space-y-2">
              {pozisyonlar.map((poz: Record<string, string | boolean>, i: number) => (
                <div key={i} className="bg-gray-50 rounded-lg p-3">
                  <div className="font-medium text-sm text-gray-800">{String(poz.unvan || "")}</div>
                  {poz.bolum && <div className="text-xs text-gray-500 mt-0.5">{String(poz.bolum)}</div>}
                  <div className="flex flex-wrap gap-2 mt-1.5">
                    {poz.kontenjan && <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">{String(poz.kontenjan)} kişi</span>}
                    {poz.kpss_turu && <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">{String(poz.kpss_turu)} min {String(poz.kpss_min || "")}</span>}
                    {poz.yas_max && <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">Max {String(poz.yas_max)} yaş</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Başvuru Analizi */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3">Başvurabilir miyim?</h2>

          {profilAcik && (
            <ProfilFormu
              profil={profil}
              onChange={profilKaydet}
              onKapat={() => setProfilAcik(false)}
            />
          )}

          {!profilAcik && (
            <div className="mb-4">
              {profil.bolum ? (
                <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                  <div className="text-sm text-gray-700">
                    <span className="font-medium">{profil.bolum}</span>
                    {profil.kpss_puan && ` • ${profil.kpss_turu || "KPSS"} ${profil.kpss_puan}`}
                    {profil.yas && ` • ${profil.yas} yaş`}
                  </div>
                  <button
                    onClick={() => setProfilAcik(true)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Değiştir
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setProfilAcik(true)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  + Profilini gir
                </button>
              )}
            </div>
          )}

          <button
            onClick={analizYap}
            disabled={analizYukleniyor}
            className="w-full bg-blue-600 text-white rounded-lg py-2.5 font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {analizYukleniyor ? "Analiz yapılıyor..." : "Analiz Et"}
          </button>

          {analiz && (
            <div className="mt-4">
              <div className={`rounded-lg p-4 ${analiz.uygun ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`font-semibold ${analiz.uygun ? "text-green-700" : "text-red-700"}`}>
                    {analiz.uygun ? "✅" : "❌"} {analiz.etiket}
                  </span>
                  <span className="text-2xl font-bold text-gray-800">{analiz.skor}/100</span>
                </div>
                <p className="text-sm text-gray-700">{analiz.ozet}</p>
                {analiz.en_uygun_pozisyon && (
                  <p className="text-sm text-gray-600 mt-1">⭐ En uygun pozisyon: <strong>{analiz.en_uygun_pozisyon}</strong></p>
                )}
              </div>

              {analiz.artilar?.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs font-medium text-green-700 mb-1">Artılar</div>
                  <ul className="space-y-1">
                    {analiz.artilar.map((a, i) => (
                      <li key={i} className="text-sm text-gray-700 flex gap-2"><span>✓</span>{a}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analiz.eksikler?.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs font-medium text-red-700 mb-1">Eksikler</div>
                  <ul className="space-y-1">
                    {analiz.eksikler.map((e, i) => (
                      <li key={i} className="text-sm text-gray-700 flex gap-2"><span>✗</span>{e}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analiz.tavsiyeler?.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs font-medium text-blue-700 mb-1">Tavsiyeler</div>
                  <ul className="space-y-1">
                    {analiz.tavsiyeler.map((t, i) => (
                      <li key={i} className="text-sm text-gray-700 flex gap-2"><span>→</span>{t}</li>
                    ))}
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

function ProfilFormu({
  profil,
  onChange,
  onKapat,
}: {
  profil: Profil;
  onChange: (p: Profil) => void;
  onKapat: () => void;
}) {
  const [form, setForm] = useState(profil);
  const guncelle = (k: keyof Profil, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <h3 className="text-sm font-semibold text-blue-800 mb-3">Profilini Gir</h3>
      <div className="grid grid-cols-2 gap-2">
        <input placeholder="Bölüm (ör: Psikoloji)" value={form.bolum || ""} onChange={(e) => guncelle("bolum", e.target.value)}
          className="border rounded px-2 py-1.5 text-sm" />
        <input placeholder="Meslek (ör: Psikolog)" value={form.meslek || ""} onChange={(e) => guncelle("meslek", e.target.value)}
          className="border rounded px-2 py-1.5 text-sm" />
        <input placeholder="KPSS türü (P3, P93...)" value={form.kpss_turu || ""} onChange={(e) => guncelle("kpss_turu", e.target.value)}
          className="border rounded px-2 py-1.5 text-sm" />
        <input placeholder="KPSS puanı (ör: 78.5)" type="number" value={form.kpss_puan || ""} onChange={(e) => guncelle("kpss_puan", e.target.value)}
          className="border rounded px-2 py-1.5 text-sm" />
        <input placeholder="Yaş" type="number" value={form.yas || ""} onChange={(e) => guncelle("yas", e.target.value)}
          className="border rounded px-2 py-1.5 text-sm" />
        <select value={form.mezuniyet_seviyesi || ""} onChange={(e) => guncelle("mezuniyet_seviyesi", e.target.value)}
          className="border rounded px-2 py-1.5 text-sm bg-white">
          <option value="">Mezuniyet seviyesi</option>
          {["Lise", "Önlisans", "Lisans", "Yüksek Lisans", "Doktora"].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <input placeholder="Tecrübe (yıl)" type="number" value={form.tecrube_yil || ""} onChange={(e) => guncelle("tecrube_yil", e.target.value)}
          className="border rounded px-2 py-1.5 text-sm" />
      </div>
      <div className="flex gap-2 mt-3">
        <button onClick={() => { onChange(form); onKapat(); }}
          className="bg-blue-600 text-white text-sm rounded px-3 py-1.5 hover:bg-blue-700">
          Kaydet
        </button>
        <button onClick={onKapat} className="text-sm text-gray-500 hover:text-gray-700">İptal</button>
      </div>
    </div>
  );
}
