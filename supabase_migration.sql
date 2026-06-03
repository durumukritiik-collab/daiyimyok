-- =========================================
-- DayımYok — Supabase Migration
-- Supabase Dashboard > SQL Editor'da çalıştır
-- =========================================

-- 1. deadline_date alanı ekle (pg_cron temizliği için)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS deadline_date DATE;

-- 2. Türkçe full-text search kolonu
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- GIN index (hızlı arama için şart)
CREATE INDEX IF NOT EXISTS jobs_search_idx ON jobs USING GIN(search_vector);

-- Arama vektörünü güncelleyen trigger fonksiyonu
CREATE OR REPLACE FUNCTION jobs_search_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('turkish',
        coalesce(NEW.title, '') || ' ' ||
        coalesce(NEW.organization, '') || ' ' ||
        coalesce(NEW.mezuniyet, '') || ' ' ||
        coalesce(NEW.arama_etiketleri, '') || ' ' ||
        coalesce(NEW.positions, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: INSERT veya UPDATE'te otomatik çalışır
DROP TRIGGER IF EXISTS jobs_search_trigger ON jobs;
CREATE TRIGGER jobs_search_trigger
    BEFORE INSERT OR UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION jobs_search_update();

-- Mevcut 132 ilanın search_vector'ını doldur
UPDATE jobs SET search_vector = to_tsvector('turkish',
    coalesce(title, '') || ' ' ||
    coalesce(organization, '') || ' ' ||
    coalesce(mezuniyet, '') || ' ' ||
    coalesce(arama_etiketleri, '') || ' ' ||
    coalesce(positions, '')
);

-- 3. Kullanıcı profil tablosu
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
    bolum TEXT,
    meslek TEXT,
    kpss_puan NUMERIC(5,2),
    kpss_turu TEXT,
    yas INTEGER,
    mezuniyet_seviyesi TEXT,
    tecrube_yil INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS (Row Level Security) — her kullanıcı sadece kendi profilini görür/düzenler
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Kullanici kendi profilini yonetir" ON profiles;
CREATE POLICY "Kullanici kendi profilini yonetir"
    ON profiles FOR ALL
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- jobs tablosu herkese okunabilir (anonim dahil)
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Jobs herkese acik" ON jobs;
CREATE POLICY "Jobs herkese acik"
    ON jobs FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Jobs service role yazabilir" ON jobs;
CREATE POLICY "Jobs service role yazabilir"
    ON jobs FOR ALL
    USING (auth.role() = 'service_role');

-- 4. pg_cron: Her gece süresi dolan ilanları pasife çek
-- (pg_cron extension Supabase'de zaten aktif)
SELECT cron.schedule(
    'cleanup-expired-jobs',
    '0 21 * * *',
    $$
    UPDATE jobs
    SET is_active = false
    WHERE is_active = true
      AND deadline_date IS NOT NULL
      AND deadline_date < CURRENT_DATE;
    $$
);

-- Kontrol: cron job'ın oluştuğunu doğrula
SELECT jobname, schedule, command FROM cron.job WHERE jobname = 'cleanup-expired-jobs';
