"""
Organization adından şehir çıkarma.
Kamu kurumları genelde adında şehri içerir:
  "ANKARA ÜNİVERSİTESİ" → Ankara
  "İSTANBUL BÜYÜKŞEHİR BELEDİYESİ" → İstanbul
  "SAĞLIK BAKANLIĞI" → Ankara (merkezi kurum)
"""

# 81 il — hem resmi hem kısaltma/varyant
ILLER = {
    "ADANA": "Adana", "ADIYAMAN": "Adıyaman", "AFYONKARAHİSAR": "Afyonkarahisar",
    "AFYON": "Afyonkarahisar", "AĞRI": "Ağrı", "AGRI": "Ağrı",
    "AKSARAY": "Aksaray", "AMASYA": "Amasya", "ANKARA": "Ankara",
    "ANTALYA": "Antalya", "ARDAHAN": "Ardahan", "ARTVİN": "Artvin",
    "ARTVIN": "Artvin", "AYDIN": "Aydın", "AYDIN": "Aydın",
    "BALIKESİR": "Balıkesir", "BALIKESIR": "Balıkesir",
    "BARTIN": "Bartın", "BATMAN": "Batman", "BAYBURT": "Bayburt",
    "BİLECİK": "Bilecik", "BILECIK": "Bilecik",
    "BİNGÖL": "Bingöl", "BINGOL": "Bingöl",
    "BİTLİS": "Bitlis", "BITLIS": "Bitlis",
    "BOLU": "Bolu", "BURDUR": "Burdur",
    "BURSA": "Bursa", "ÇANAKKALE": "Çanakkale", "CANAKKALE": "Çanakkale",
    "ÇANKIRI": "Çankırı", "CANKIRI": "Çankırı",
    "ÇORUM": "Çorum", "CORUM": "Çorum",
    "DENİZLİ": "Denizli", "DENIZLI": "Denizli",
    "DİYARBAKIR": "Diyarbakır", "DIYARBAKIR": "Diyarbakır",
    "DÜZCE": "Düzce", "DUZCE": "Düzce",
    "EDİRNE": "Edirne", "EDIRNE": "Edirne",
    "ELAZIĞ": "Elazığ", "ELAZIG": "Elazığ",
    "ERZİNCAN": "Erzincan", "ERZINCAN": "Erzincan",
    "ERZURUM": "Erzurum", "ESKİŞEHİR": "Eskişehir", "ESKISEHIR": "Eskişehir",
    "GAZİANTEP": "Gaziantep", "GAZIANTEP": "Gaziantep",
    "GİRESUN": "Giresun", "GIRESUN": "Giresun",
    "GÜMÜŞHANE": "Gümüşhane", "GUMUSHANE": "Gümüşhane",
    "HAKKARİ": "Hakkari", "HAKKARI": "Hakkari",
    "HATAY": "Hatay", "IĞDIR": "Iğdır", "IGDIR": "Iğdır",
    "ISPARTA": "Isparta",
    "İSTANBUL": "İstanbul", "ISTANBUL": "İstanbul",
    "İZMİR": "İzmir", "IZMIR": "İzmir",
    "KAHRAMANMARAŞ": "Kahramanmaraş", "KAHRAMANMARAS": "Kahramanmaraş",
    "KARABÜK": "Karabük", "KARABUK": "Karabük",
    "KARAMAN": "Karaman", "KARS": "Kars",
    "KASTAMONU": "Kastamonu", "KAYSERİ": "Kayseri", "KAYSERI": "Kayseri",
    "KIRIKKALE": "Kırıkkale", "KIRIKKALE": "Kırıkkale",
    "KIRKLARELİ": "Kırklareli", "KIRKLARELI": "Kırklareli",
    "KIRŞEHİR": "Kırşehir", "KIRSEHIR": "Kırşehir",
    "KİLİS": "Kilis", "KILIS": "Kilis",
    "KOCAELİ": "Kocaeli", "KOCAELI": "Kocaeli",
    "KONYA": "Konya", "KÜTAHYA": "Kütahya", "KUTAHYA": "Kütahya",
    "MALATYA": "Malatya", "MANİSA": "Manisa", "MANISA": "Manisa",
    "MARDİN": "Mardin", "MARDIN": "Mardin",
    "MERSİN": "Mersin", "MERSIN": "Mersin", "İÇEL": "Mersin",
    "MUĞLA": "Muğla", "MUGLA": "Muğla",
    "MUŞ": "Muş", "MUS": "Muş",
    "NEVŞEHİR": "Nevşehir", "NEVSEHIR": "Nevşehir",
    "NİĞDE": "Niğde", "NIGDE": "Niğde",
    "ORDU": "Ordu", "OSMANİYE": "Osmaniye", "OSMANIYE": "Osmaniye",
    "RİZE": "Rize", "RIZE": "Rize",
    "SAKARYA": "Sakarya", "SAMSUN": "Samsun",
    "SİİRT": "Siirt", "SIIRT": "Siirt",
    "SİNOP": "Sinop", "SINOP": "Sinop",
    "SİVAS": "Sivas", "SIVAS": "Sivas",
    "ŞANLIURFA": "Şanlıurfa", "SANLIURFA": "Şanlıurfa", "URFA": "Şanlıurfa",
    "ŞIRNAK": "Şırnak", "SIRNAK": "Şırnak",
    "TEKİRDAĞ": "Tekirdağ", "TEKIRDAG": "Tekirdağ",
    "TOKAT": "Tokat", "TRABZON": "Trabzon", "TUNCELİ": "Tunceli", "TUNCELI": "Tunceli",
    "UŞAK": "Uşak", "USAK": "Uşak",
    "VAN": "Van", "YALOVA": "Yalova",
    "YOZGAT": "Yozgat", "ZONGULDAK": "Zonguldak",
}

# Merkezi kurum anahtar kelimeleri → Ankara varsayılan
MERKEZI_KURUMLAR = [
    "BAKANLIĞI", "BAŞKANLIĞI", "KURUMU", "KURULU",
    "MÜSTEŞARLIĞI", "GENEL MÜDÜRLÜĞÜ", "DAİRESİ BAŞKANLIĞI",
    "KAMU İHALE", "HAZİNE", "TÜRKIYE", "TÜRKİYE",
    "DEVLET", "CUMHURBAŞKANLIĞI", "MECLİS", "YARGITAY",
    "DANIŞTAY", "SAYIŞTAY", "ANAYASA MAHKEMESİ",
    "RADYO VE TELEVİZYON", "TRT", "BDDK", "EPDK", "BTK", "SPK",
    "REKABET KURUMU", "SOSYAL GÜVENLİK", "SGK",
]


# Üniversite adı → şehir (adında il geçmeyenler)
UNIVERSITE_SEHIR = {
    "EGE ÜNİVERSİTESİ": "İzmir",
    "EGE UNIVERSITESI": "İzmir",
    "KARADENİZ TEKNİK": "Trabzon",
    "KARADENIZ TEKNIK": "Trabzon",
    "SÜLEYMAN DEMİREL": "Isparta",
    "SULEYMAN DEMIREL": "Isparta",
    "AKDENİZ ÜNİVERSİTESİ": "Antalya",
    "AKDENIZ UNIVERSITESI": "Antalya",
    "HACETTEPE": "Ankara",
    "ORTA DOĞU TEKNİK": "Ankara",
    "METU": "Ankara",
    "ODTÜ": "Ankara",
    "BOĞAZİÇİ": "İstanbul",
    "BOGAZICI": "İstanbul",
    "İTÜ": "İstanbul",
    "İSTANBUL TEKNİK": "İstanbul",
    "ISTANBUL TEKNIK": "İstanbul",
    "GAZİ ÜNİVERSİTESİ": "Ankara",
    "GAZI UNIVERSITESI": "Ankara",
    "NECMETTİN ERBAKAN": "Konya",
    "NECMETTIN ERBAKAN": "Konya",
    "YILDIRIM BEYAZIT": "Ankara",
    "ANKARA YILDIRIM": "Ankara",
    "SOSYAL BİLİMLER ÜNİVERSİTESİ": "Ankara",
    "IHSAN DOĞRAMACI": "Ankara",
    "IHSAN DOGRAMACI": "Ankara",
    "BİLKENT": "Ankara",
    "BILKENT": "Ankara",
    "ATATÜRK ÜNİVERSİTESİ": "Erzurum",
    "ATATURK UNIVERSITESI": "Erzurum",
    "CUMHURİYET ÜNİVERSİTESİ": "Sivas",
    "CUMHURIYET UNIVERSITESI": "Sivas",
    "FIRAT ÜNİVERSİTESİ": "Elazığ",
    "FIRAT UNIVERSITESI": "Elazığ",
    "İNÖNÜ ÜNİVERSİTESİ": "Malatya",
    "INONU UNIVERSITESI": "Malatya",
    "ONDOKUZ MAYIS": "Samsun",
    "ERCİYES": "Kayseri",
    "ERCIYES": "Kayseri",
    "ULUDAĞ": "Bursa",
    "ULUDAG": "Bursa",
    "CELALEDDİN KARATAY": "Konya",
    "KONYA TEKNİK": "Konya",
    "KONYA TEKNIK": "Konya",
    "SELÇUK ÜNİVERSİTESİ": "Konya",
    "SELCUK UNIVERSITESI": "Konya",
    "MARMARA ÜNİVERSİTESİ": "İstanbul",
    "MARMARA UNIVERSITESI": "İstanbul",
    "GALATASARAY": "İstanbul",
    "YILDIZ TEKNİK": "İstanbul",
    "YILDIZ TEKNIK": "İstanbul",
    "GEBZE TEKNİK": "Kocaeli",
    "GEBZE TEKNIK": "Kocaeli",
    "KÜTAHYA SAĞLIK": "Kütahya",
    "KUTAHYA SAGLIK": "Kütahya",
    "SAĞLIK BİLİMLERİ ÜNİVERSİTESİ": "İstanbul",
    "SAGLIK BILIMLERI": "İstanbul",
    "TARSUS ÜNİVERSİTESİ": "Mersin",
    "TARSUS UNIVERSITESI": "Mersin",
    "ALANYA": "Antalya",
    "BURDUR MEHMET AKİF": "Burdur",
    "MEHMET AKİF ERSOY": "Burdur",
    "MEHMET AKIF ERSOY": "Burdur",
    "AFYON KOCATEPE": "Afyonkarahisar",
    "DÜZCE ÜNİVERSİTESİ": "Düzce",
    "DUZCE UNIVERSITESI": "Düzce",
    "İSPİR": "Erzurum",
    "ISPIR": "Erzurum",
}


def extract_city(organization: str, title: str = "", pdf_text: str = "") -> str:
    """
    Organization adından veya ilan içeriğinden şehir çıkar.
    Önce organization, sonra title, sonra pdf_text dener.
    """
    if not organization:
        return ""

    org_upper = organization.upper()

    # 0. Üniversite adı mapping
    for uni_key, sehir in UNIVERSITE_SEHIR.items():
        if uni_key in org_upper:
            return sehir

    # 1. İl adı doğrudan organization'da geçiyor mu?
    for il_key, il_val in ILLER.items():
        # Kelime sınırlarıyla eşleştir (ANKARA ÜNİVERSİTESİ → Ankara)
        if il_key in org_upper:
            # Kısmi eşleşme önle: "VAN" → "ADIYAMAN" ile eşleşmesin
            # Kontrol: il_key öncesi ve sonrası boşluk veya satır başı/sonu
            import re
            pattern = r'(?<![A-ZÇĞİÖŞÜa-zçğışöşü])' + re.escape(il_key) + r'(?![A-ZÇĞİÖŞÜa-zçğışöşü])'
            if re.search(pattern, org_upper):
                return il_val

    # 2. Merkezi kurum → Ankara
    for keyword in MERKEZI_KURUMLAR:
        if keyword in org_upper:
            return "Ankara"

    # 3. title içinde il var mı?
    if title:
        title_upper = title.upper()
        for il_key, il_val in ILLER.items():
            import re
            pattern = r'(?<![A-ZÇĞİÖŞÜa-zçğışöşü])' + re.escape(il_key) + r'(?![A-ZÇĞİÖŞÜa-zçğışöşü])'
            if re.search(pattern, title_upper):
                return il_val

    # 4. PDF metninin ilk 500 karakterinde il var mı? (son çare)
    if pdf_text:
        sample = pdf_text[:500].upper()
        for il_key, il_val in ILLER.items():
            import re
            pattern = r'(?<![A-ZÇĞİÖŞÜa-zçğışöşü])' + re.escape(il_key) + r'(?![A-ZÇĞİÖŞÜa-zçğışöşü])'
            if re.search(pattern, sample):
                return il_val

    return ""
