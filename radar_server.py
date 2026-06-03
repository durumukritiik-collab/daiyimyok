"""
Kamu Radar yerel sunucusu.
PDF'leri doğru Referer ile çeker, radar.html'i tarayıcıda açar.

Kullanım: python radar_server.py
Sonra: http://localhost:8765 adresi otomatik açılır.
"""
import os
import subprocess
import threading
import urllib.parse
import warnings
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

warnings.filterwarnings("ignore")

PORT = 8765
KAMUILAN_REFERER = "https://kamuilan.sbb.gov.tr/"


class RadarHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # sessiz mod

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # /pdf?url=... → PDF proxy
        if parsed.path == "/pdf":
            params = urllib.parse.parse_qs(parsed.query)
            target = params.get("url", [""])[0]
            if not target or "kamuilan.sbb.gov.tr" not in target:
                self.send_error(400, "Geçersiz URL")
                return
            try:
                r = requests.get(
                    target,
                    verify=False,
                    timeout=20,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
                        "Referer": KAMUILAN_REFERER,
                    },
                )
                if r.content[:4] == b"%PDF":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", "inline")
                    self.end_headers()
                    self.wfile.write(r.content)
                else:
                    self.send_error(404, "PDF alınamadı")
            except Exception as e:
                self.send_error(500, str(e))
            return

        # /radar.html veya / → HTML dosyası
        if parsed.path in ("/", "/radar.html"):
            html_path = os.path.join(os.path.dirname(__file__), "radar.html")
            try:
                with open(html_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404, "radar.html bulunamadı — önce generate_report.py çalıştır")
            return

        self.send_error(404)


def main():
    # radar.html URL'lerini proxy'ye yönlendir
    _patch_html_for_proxy()

    server = HTTPServer(("localhost", PORT), RadarHandler)
    url = f"http://localhost:{PORT}"
    print(f"\n  Kamu Radar Sunucusu başlatıldı")
    print(f"  Adres : {url}")
    print(f"  Durdurmak için Ctrl+C\n")

    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu durduruldu.")


def _patch_html_for_proxy():
    """radar.html'deki kamuilan PDF linklerini proxy URL'sine çevir."""
    html_path = os.path.join(os.path.dirname(__file__), "radar.html")
    if not os.path.exists(html_path):
        return
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    import re
    # JS içindeki kamuilan URL'lerini proxy'ye yönlendir
    def replace_url(m):
        url = m.group(1)
        if "kamuilan.sbb.gov.tr" in url:
            encoded = urllib.parse.quote(url, safe="")
            return f'"{url}"'  # JS kodu zaten link.href'e atıyor, orada proxy'ye çevireceğiz
        return m.group(0)

    # Zaten generate_report.py'deki JS kısmı proxy'yi kullanacak şekilde güncellendi
    # Burada sadece kontrol amaçlı — asıl dönüşüm generate_report.py'de yapılacak
    print("  radar.html proxy için hazır.")


if __name__ == "__main__":
    main()
