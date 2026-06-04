"use client";

import { useState, useRef, useEffect } from "react";
import type { ResearchResponse, JobResult } from "./api/research/route";

const ORNEKLER = [
  "Psikoloğum, Antalya'da iş arıyorum. Çocuk ve ergen alanında deneyimim var.",
  "Yazılım geliştirici, uzaktan çalışmak istiyorum, React ve TypeScript biliyorum.",
  "Hemşireyim, İstanbul'da tam zamanlı iş arıyorum, yoğun bakım deneyimim var.",
  "İnsan kaynakları uzmanıyım, Ankara'da iş arıyorum, KPSS'siz de olabilir.",
];

const ADIMLAR = [
  "Profilinizi analiz ediyorum...",
  "Arama sorguları oluşturuluyor...",
  "Kariyer.net, Eleman.net ve diğer siteler taranıyor...",
  "Bulunan ilanlar değerlendiriliyor...",
  "En uygun ilanlar seçiliyor...",
];

export default function Home() {
  const [mesaj, setMesaj] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);
  const [adim, setAdim] = useState(0);
  const [sonuc, setSonuc] = useState<ResearchResponse | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sonucRef = useRef<HTMLDivElement>(null);
  const adimRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (yukleniyor) {
      setAdim(0);
      let i = 0;
      adimRef.current = setInterval(() => {
        i = Math.min(i + 1, ADIMLAR.length - 1);
        setAdim(i);
      }, 5000);
    } else {
      if (adimRef.current) clearInterval(adimRef.current);
    }
    return () => { if (adimRef.current) clearInterval(adimRef.current); };
  }, [yukleniyor]);

  useEffect(() => {
    if (sonuc && sonucRef.current) {
      sonucRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [sonuc]);

  async function arastir() {
    if (!mesaj.trim() || yukleniyor) return;
    setYukleniyor(true);
    setSonuc(null);
    setHata(null);

    try {
      const res = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: mesaj }),
      });
      const data: ResearchResponse = await res.json();
      if (!res.ok || data.error) {
        setHata(data.error ?? "Bir hata oluştu.");
      } else {
        setSonuc(data);
      }
    } catch {
      setHata("Bağlantı hatası. İnternet bağlantınızı kontrol edin.");
    } finally {
      setYukleniyor(false);
    }
  }

  function ornekSec(ornek: string) {
    setMesaj(ornek);
    textareaRef.current?.focus();
  }

  function yeniArama() {
    setSonuc(null);
    setHata(null);
    setMesaj("");
    textareaRef.current?.focus();
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-white">DayımYok</h1>
            <p className="text-xs text-gray-500">AI İş Araştırma Asistanı</p>
          </div>
          {sonuc && (
            <button onClick={yeniArama} className="text-xs text-gray-400 hover:text-white transition-colors">
              ← Yeni arama
            </button>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">

        {/* Giriş ekranı */}
        {!sonuc && !yukleniyor && (
          <div className="space-y-8">
            <div className="text-center space-y-3">
              <h2 className="text-3xl font-bold text-white">
                Benim yerime araştır.
              </h2>
              <p className="text-gray-400 max-w-md mx-auto">
                Durumunu anlat. 30 saniye içinde sana en uygun işleri bulayım.
              </p>
            </div>

            {/* Textarea */}
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={mesaj}
                onChange={(e) => setMesaj(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); arastir(); } }}
                placeholder="Örnek: Psikoloğum, Antalya'da iş arıyorum. Çocuk ve ergen alanında deneyimim var..."
                rows={4}
                className="w-full bg-gray-900 border border-gray-700 rounded-2xl px-5 py-4 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-blue-500 resize-none text-sm leading-relaxed"
              />
              <button
                onClick={arastir}
                disabled={!mesaj.trim()}
                className="absolute bottom-4 right-4 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-xl transition-colors"
              >
                Araştır →
              </button>
            </div>

            {/* Örnekler */}
            <div>
              <p className="text-xs text-gray-600 mb-3">Örnek aramalar</p>
              <div className="space-y-2">
                {ORNEKLER.map((ornek, i) => (
                  <button
                    key={i}
                    onClick={() => ornekSec(ornek)}
                    className="w-full text-left text-sm text-gray-400 hover:text-gray-200 bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 rounded-xl px-4 py-3 transition-all"
                  >
                    {ornek}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Yükleniyor */}
        {yukleniyor && (
          <div className="flex flex-col items-center justify-center py-24 space-y-6">
            <div className="relative">
              <div className="w-16 h-16 border-2 border-gray-800 rounded-full" />
              <div className="absolute inset-0 w-16 h-16 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-white font-medium">{ADIMLAR[adim]}</p>
              <p className="text-xs text-gray-600">Bu işlem 20-30 saniye sürebilir</p>
            </div>
            <div className="flex gap-1.5 mt-2">
              {ADIMLAR.map((_, i) => (
                <div
                  key={i}
                  className={`h-1 w-8 rounded-full transition-all duration-500 ${i <= adim ? "bg-blue-500" : "bg-gray-800"}`}
                />
              ))}
            </div>
          </div>
        )}

        {/* Hata */}
        {hata && !yukleniyor && (
          <div className="text-center py-16 space-y-4">
            <div className="text-4xl">⚠️</div>
            <p className="text-gray-300">{hata}</p>
            <button onClick={yeniArama} className="text-sm text-blue-400 hover:text-blue-300">
              Tekrar dene
            </button>
          </div>
        )}

        {/* Sonuçlar */}
        {sonuc && !yukleniyor && (
          <div ref={sonucRef} className="space-y-6">
            {/* Özet */}
            <div className="space-y-1">
              <h2 className="text-xl font-bold text-white">
                {sonuc.jobs.length > 0
                  ? `${sonuc.total_found} ilan arasından ${sonuc.jobs.length} tanesini seçtim`
                  : "Uygun ilan bulunamadı"}
              </h2>
              {sonuc.profile.job_title && (
                <p className="text-sm text-gray-500">
                  {sonuc.profile.job_title} · {sonuc.profile.location}
                </p>
              )}
            </div>

            {/* İlan listesi */}
            {sonuc.jobs.length === 0 ? (
              <div className="text-center py-10 space-y-3">
                <p className="text-gray-400">Kriterlere uyan ilan bulunamadı.</p>
                <button onClick={yeniArama} className="text-sm text-blue-400 hover:text-blue-300">
                  Farklı bir arama dene
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {sonuc.jobs.map((job, i) => (
                  <JobKart key={i} job={job} index={i} />
                ))}
              </div>
            )}

            {/* Yeni arama */}
            <div className="pt-4 border-t border-gray-800 text-center">
              <button
                onClick={yeniArama}
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                ← Yeni arama yap
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function JobKart({ job, index }: { job: JobResult; index: number }) {
  const [acik, setAcik] = useState(index === 0);

  const skorRenk =
    job.score >= 85 ? "text-green-400 bg-green-400/10 border-green-400/30" :
    job.score >= 70 ? "text-blue-400 bg-blue-400/10 border-blue-400/30" :
    "text-yellow-400 bg-yellow-400/10 border-yellow-400/30";

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden hover:border-gray-700 transition-all">
      {/* Header — her zaman görünür */}
      <button
        onClick={() => setAcik(!acik)}
        className="w-full text-left px-5 py-4 flex items-start gap-4"
      >
        <div className={`shrink-0 text-sm font-bold px-2.5 py-1 rounded-lg border ${skorRenk}`}>
          %{job.score}
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-semibold text-white leading-tight">{job.title}</p>
          <p className="text-sm text-gray-400 mt-0.5">
            {job.company}{job.location ? ` · ${job.location}` : ""}
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            {job.work_type && (
              <span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full">{job.work_type}</span>
            )}
            {job.salary && (
              <span className="text-xs bg-green-900/40 text-green-400 px-2 py-0.5 rounded-full">💰 {job.salary}</span>
            )}
            {job.deadline && (
              <span className="text-xs bg-orange-900/30 text-orange-400 px-2 py-0.5 rounded-full">📅 {job.deadline}</span>
            )}
            {job.posted_date && (
              <span className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full">{job.posted_date}</span>
            )}
          </div>
        </div>

        <span className="shrink-0 text-gray-600 text-xs mt-1">{acik ? "▲" : "▼"}</span>
      </button>

      {/* Detay — açılınca görünür */}
      {acik && (
        <div className="border-t border-gray-800 divide-y divide-gray-800/60">

          {/* Neden uygun */}
          <div className="px-5 py-4">
            <p className="text-xs text-gray-500 font-medium mb-1.5 uppercase tracking-wide">Neden uygun</p>
            <p className="text-sm text-gray-300 leading-relaxed">{job.reason}</p>
          </div>

          {/* Aranan nitelikler */}
          {job.requirements && job.requirements.length > 0 && (
            <div className="px-5 py-4">
              <p className="text-xs text-gray-500 font-medium mb-2 uppercase tracking-wide">Aranan nitelikler</p>
              <ul className="space-y-1.5">
                {job.requirements.map((r, i) => (
                  <li key={i} className="text-sm text-gray-300 flex gap-2">
                    <span className="text-gray-600 shrink-0">·</span>{r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Şirket hakkında */}
          {job.company_info && (
            <div className="px-5 py-4">
              <p className="text-xs text-gray-500 font-medium mb-1.5 uppercase tracking-wide">Şirket</p>
              <p className="text-sm text-gray-400">{job.company_info}</p>
            </div>
          )}

          {/* Başvuru yöntemi */}
          {job.apply_method && (
            <div className="px-5 py-4">
              <p className="text-xs text-gray-500 font-medium mb-1.5 uppercase tracking-wide">Nasıl başvurulur</p>
              <p className="text-sm text-blue-400">{job.apply_method}</p>
            </div>
          )}

          {/* Dikkat et */}
          {job.missing_skills && job.missing_skills.length > 0 && (
            <div className="px-5 py-4">
              <p className="text-xs text-gray-500 font-medium mb-1.5 uppercase tracking-wide">Dikkat et</p>
              <ul className="space-y-1">
                {job.missing_skills.map((s, i) => (
                  <li key={i} className="text-sm text-yellow-400/80 flex gap-2">
                    <span>⚠</span>{s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Başvur butonu */}
          <div className="px-5 py-4">
            <a
              href={job.apply_link || job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-colors"
            >
              İlana Git →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
