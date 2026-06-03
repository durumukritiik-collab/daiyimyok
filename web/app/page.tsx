import Link from "next/link";

export default function AnaSayfa() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-white flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">
          DayımYok 🏛️
        </h1>
        <p className="text-lg text-gray-600 mb-2">
          Güncel kamu iş ilanları — Groq destekli akıllı analiz
        </p>
        <p className="text-sm text-gray-400 mb-8">
          Bölümünü yaz, sana uygun açık ilanlar saniyeler içinde karşında.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-12">
          <Link
            href="/ilanlar"
            className="bg-blue-600 text-white rounded-xl px-6 py-3 font-semibold hover:bg-blue-700 transition-colors"
          >
            İlanları Gör
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl mb-2">🔍</div>
            <h3 className="font-semibold text-gray-800 mb-1">Akıllı Arama</h3>
            <p className="text-sm text-gray-500">Bölüm, kurum veya pozisyon adıyla Türkçe arama yap</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl mb-2">🤖</div>
            <h3 className="font-semibold text-gray-800 mb-1">Groq Analizi</h3>
            <p className="text-sm text-gray-500">Profilini gir, &quot;Başvurabilir miyim?&quot; sorusunun cevabını al</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl mb-2">⚡</div>
            <h3 className="font-semibold text-gray-800 mb-1">Günlük Güncelleme</h3>
            <p className="text-sm text-gray-500">4 farklı kaynak her sabah otomatik taranır</p>
          </div>
        </div>
      </div>
    </main>
  );
}
