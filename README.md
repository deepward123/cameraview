# Forklift Barkod Okuyucu

Forklift kamerasının görüntüsünü (ekrana yansıyan görüntü, USB/capture kartı,
RTSP IP kamera veya video dosyası) okuyup işleyen, barkodu **otomatik dijital
zoom** ile yakınlaştırıp/uzaklaştırarak çözen ve barkodun **belirli bir
kısmındaki numarayı** ayıklayıp **SAP'ye gönderen** uygulama.

```
Görüntü kaynağı ──> Barkod bölgesi tespiti ──> Otomatik zoom (in/out) ──> Çözümleme
                                                                              │
       SAP / CSV / Konsol  <── Tekrar filtresi <── Numara ayıklama  <─────────┘
```

## Özellikler

- **4 görüntü kaynağı:** kameranın yansıdığı **ekranı yakalama** (mss),
  USB kamera / HDMI-AV capture kartı, RTSP IP kamera, video dosyası
- **Otomatik dijital zoom:** barkod tam karede okunamazsa aday bölgeler
  bulunur; yapılandırılan ölçeklerde (örn. 0.5x–4x) yakınlaştırılıp
  uzaklaştırılarak okuma başarılı olana dek denenir. Başarılı bölge+ölçek
  hatırlanır, sonraki karelerde önce o denenir (takip modu).
- **Numara ayıklama:** barkod içeriğinin istenen kısmı karakter aralığı
  (`slice`) veya düzenli ifade (`regex`) ile alınır
- **SAP entegrasyonu:** OData/REST uç noktasına JSON POST; basic/token
  kimlik doğrulama, X-CSRF-Token akışı, yeniden deneme ve **çevrimdışı
  kuyruk** (ağ yokken `sap_failed.jsonl` dosyasına yazılır)
- **Canlı önizleme:** barkod kutusu, kullanılan zoom ve ayıklanan numara
  ekranda gösterilir
- **Tekrar filtresi:** aynı numara belirlenen süre içinde ikinci kez gönderilmez

## Kurulum

```bash
# Sistem bağımlılığı (pyzbar için)
sudo apt install libzbar0        # Windows'ta gerekmez (whl içinde gelir)

pip install -r requirements.txt
```

## Kullanım

```bash
# Yapılandırmayı düzenleyin (kaynak, ayıklama kuralı, SAP adresi)
nano config.yaml

# SAP kimlik bilgileri ortam değişkeniyle verilir (config'e yazılmaz)
export SAP_USER=rfc_kullanici
export SAP_PASSWORD=parola

# Canlı okuma
python -m forklift_barcode --config config.yaml

# Tek bir fotoğrafı dene
python -m forklift_barcode --image foto.png

# Donanımsız uçtan uca demo (sentetik kareler üretir, demo_out/ klasörüne yazar)
python tools/demo.py
```

Önizleme penceresinde `q` veya `ESC` ile çıkılır.

## Yapılandırma özeti (`config.yaml`)

| Bölüm | Ne işe yarar |
|---|---|
| `source` | Görüntü nereden alınacak: `camera`, `screen`, `rtsp`, `file` |
| `processing.zoom_scales` | Denenecek dijital zoom ölçekleri (yakınlaştırma **ve** uzaklaştırma) |
| `processing.symbologies` | Beklenen barkod tipleri (örn. `[CODE128]`) — yanlış okumaları azaltır |
| `extraction` | Numaranın barkodun neresinden alınacağı (`slice` veya `regex`) |
| `output.targets` | Sonuç nereye gidecek: `console`, `csv`, `sap` (birden fazla seçilebilir) |
| `output.sap` | SAP uç noktası, kimlik doğrulama ve alan eşlemesi |

### Ayıklama örnekleri

```yaml
# Barkodun 4. karakterinden itibaren 10 hane:
extraction: {mode: slice, start: 4, length: 10}

# "PLT" önekinden sonraki 10 rakam:
extraction: {mode: regex, regex: 'PLT(\d{10})', regex_group: 1}

# Son 8 rakam:
extraction: {mode: regex, regex: '(\d{8})$', regex_group: 1}
```

### SAP alan eşlemesi

`field_map` içindeki şablonlarda şu yer tutucular kullanılabilir:
`{value}` (ayıklanan numara), `{raw}` (barkodun tamamı), `{timestamp}`,
`{symbol}` (barkod tipi), `{zoom}`.

## Testler

```bash
python -m pytest tests/
```

Testler harici donanım gerektirmez: `tests/barcode_gen.py` içindeki Code128
üreteciyle sentetik kareler oluşturulur ve tüm hat (tespit → zoom →
çözümleme → ayıklama → gönderim) uçtan uca doğrulanır.

## Proje yapısı

```
forklift_barcode/
├── __main__.py          # CLI girişi
├── app.py               # ana döngü + önizleme overlay
├── config.py            # YAML yapılandırma
├── capture/             # kamera / ekran / RTSP / dosya kaynakları
├── processing/
│   ├── locator.py       # barkod bölgesi tespiti (gradyan+morfoloji)
│   ├── zoom.py          # otomatik dijital zoom + takip
│   ├── decoder.py       # pyzbar (birincil) + OpenCV (yedek)
│   └── extractor.py     # numara ayıklama (slice/regex)
└── output/              # konsol, CSV, SAP (CSRF + çevrimdışı kuyruk)
```

## Notlar

- Ekran yakalama (`source.type: screen`) kameranın görüntüsünün bir monitörde
  gösterildiği kurulumlar içindir; `screen.region` ile yalnızca kamera
  penceresinin bölgesi yakalanabilir.
- Dijital zoom mevcut pikselleri büyütür; çok uzak/bulanık barkodlar için
  kamera çözünürlüğünü artırmak veya optik zoom kullanmak gerekebilir.
- Sunucu/kiosk ortamında önizleme istemiyorsanız `--no-preview` bayrağını
  kullanın ve `opencv-python` yerine `opencv-python-headless` kurabilirsiniz.
