# Forklift Barkod Okuyucu

Forklift kamerasının **ekrana yansıyan görüntüsündeki barkodu** okuyup,
barkod numarasını **bilgisayarda yazan** uygulama. Barkod net okunamıyorsa
**otomatik dijital zoom** ile yakınlaştırıp/uzaklaştırarak okumayı dener.

```
Ekran/kamera görüntüsü ──> Barkod bölgesi tespiti ──> Otomatik zoom (in/out)
                                                              │
        Konsol + önizleme penceresi <── Barkod numarası <── Çözümleme
```

## Özellikler

- **Ekran yakalama (varsayılan):** kameranın yansıdığı ekranı doğrudan okur;
  `screen.region` ile yalnızca kamera penceresinin bölgesi seçilebilir.
  İstenirse USB kamera / HDMI-AV capture kartı, RTSP IP kamera veya video
  dosyası da kaynak olarak kullanılabilir.
- **Otomatik dijital zoom:** barkod tam karede okunamazsa aday bölgeler
  bulunur; yapılandırılan ölçeklerde (0.5x–4x) yakınlaştırılıp uzaklaştırılarak
  okuma başarılı olana dek denenir. Başarılı bölge+ölçek hatırlanır, sonraki
  karelerde önce o denenir.
- **Numarayı bilgisayarda yazar:** okunan barkod hem konsola yazılır hem de
  önizleme penceresinin üst şeridinde büyük puntoyla gösterilir. İstenirse
  `csv` hedefiyle `readings.csv` dosyasına da kaydedilir.
- **Tekrar filtresi:** aynı barkod belirlenen süre içinde ikinci kez yazılmaz.
- İleride gerekirse barkodun yalnızca bir kısmını almak için `slice`/`regex`
  ayıklama kuralları hazırdır (`config.yaml` → `extraction`).

## Kurulum

```bash
# Linux'ta sistem bağımlılığı (pyzbar için; Windows'ta gerekmez)
sudo apt install libzbar0

pip install -r requirements.txt
```

## Kullanım

```bash
# Varsayılan: birincil ekranı yakalar, bulduğu barkodu konsola yazar
python -m forklift_barcode

# Yapılandırma dosyasıyla (kaynak, bölge, zoom ölçekleri...)
python -m forklift_barcode --config config.yaml

# USB kamera / capture kartından okumak için
python -m forklift_barcode --source camera

# Tek bir fotoğrafı dene
python -m forklift_barcode --image foto.png

# Donanımsız uçtan uca demo (sentetik kareler üretir, demo_out/ klasörüne yazar)
python tools/demo.py
```

Önizleme penceresinde `q` veya `ESC` ile çıkılır.

## VS Code ile çalıştırma

1. Klasörü VS Code ile açın (**File → Open Folder**). Önerilen **Python**
   eklentisini kurun (sağ altta bildirim çıkar).
2. `Ctrl+Shift+P` → **Python: Create Environment** → **Venv** → Python
   sürümünüzü seçin → bağımlılık sorusunda `requirements.txt`'i işaretleyin.
   (VS Code sanal ortamı kurup paketleri otomatik yükler.)
3. `F5`'e basın ve çalıştırma seçeneğini seçin:
   - **Demo (donanımsız)** — önce bunu deneyin; sentetik barkodlarla tüm
     sistemi test eder, sonuç görsellerini `demo_out/` klasörüne yazar.
   - **Canlı okuma** — ekranı yakalayıp barkod aramaya başlar.
   - **Tek fotoğraf dene** — bir fotoğraf yolu sorar ve sonucu yazar.

Testleri VS Code'un **Testing** panelinden (kavanoz simgesi) çalıştırabilirsiniz.

## Yapılandırma özeti (`config.yaml`)

| Bölüm | Ne işe yarar |
|---|---|
| `source` | Görüntü nereden alınacak: `screen` (varsayılan), `camera`, `rtsp`, `file` |
| `source.screen.region` | Ekranın yalnızca kamera penceresi olan bölgesini yakala |
| `source.flip` | Ayna/ters görüntü düzeltme: `horizontal`, `vertical`, `both`, `none` |
| `processing.zoom_scales` | Denenecek dijital zoom ölçekleri (yakınlaştırma **ve** uzaklaştırma) |
| `processing.symbologies` | Beklenen barkod tipleri (örn. `[CODE128]`) — yanlış okumaları azaltır |
| `processing.max_width` | Kareyi işlemeden önce küçült (performans) |
| `processing.full_search_every` | Ağır aramayı her N karede bir yap (performans) |
| `extraction` | `full` = barkodun tamamını yaz; gerekirse `slice`/`regex` ile bir kısmı |
| `output.targets` | `console` ve/veya `csv` |
| `output.dedupe_seconds` | Aynı barkodun tekrar yazılmaması için bekleme süresi |

## Performans mimarisi

Görüntü akışı ile barkod işleme **ayrı iş parçacıklarında** çalışır: ana
döngü kareyi alır, arka plandaki işlemciye bırakır ve beklemeden gösterir.
İşleme yetişemezse aradaki kareler atlanır (hep en yeni kare işlenir);
bu sayede ağır arama sürerken bile önizleme akıcı kalır.

Yine de yavaşlık yaşarsanız (`config.yaml`):

1. `processing.symbologies: [CODE128]` — yalnızca kullandığınız barkod tipini
   yazın; çözücü diğer tipleri hiç denemez, taramayı belirgin hızlandırır.
2. `source.screen.region` — ekranın tamamı yerine yalnızca kamera görüntüsünün
   olduğu bölgeyi yakalayın (ör. `{left: 0, top: 0, width: 1280, height: 720}`).
3. `processing.max_width: 960` — kareler daha da küçültülür.
4. `source.fps_limit: 10` — saniyede işlenen kare sayısını düşürür.
5. `processing.full_search_every: 5` — ağır arama daha seyrek çalışır
   (barkodun ilk yakalanması en fazla yarım saniye gecikebilir, sonrası aynı).

## Bulanık görüntüler

Zoom yapılan kesitlere hafif ve **güçlü keskinleştirme** varyantları
uygulanır; hafif odak bulanıklığındaki barkodlar 3x-4x zoom ile okunabilir.
Ancak dijital iyileştirmenin sınırı vardır: çizgiler tamamen birbirine
karışmışsa yazılım kurtaramaz. Kalıcı çözüm için kamera odağını ayarlayın,
merceği temizleyin veya kamerayı barkoda biraz yaklaştırın.

## Testler

```bash
python -m pytest tests/
```

Testler harici donanım gerektirmez: `tests/barcode_gen.py` içindeki Code128
üreteciyle sentetik kareler oluşturulur ve tüm hat (tespit → zoom →
çözümleme → yazma) uçtan uca doğrulanır.

## Proje yapısı

```
forklift_barcode/
├── __main__.py          # CLI girişi
├── app.py               # ana döngü + önizleme overlay
├── config.py            # YAML yapılandırma
├── capture/             # ekran / kamera / RTSP / dosya kaynakları
├── processing/
│   ├── locator.py       # barkod bölgesi tespiti (gradyan+morfoloji)
│   ├── zoom.py          # otomatik dijital zoom + takip
│   ├── decoder.py       # pyzbar (birincil) + OpenCV (yedek)
│   └── extractor.py     # yazılacak numara (full/slice/regex)
└── output/              # konsol + CSV kaydı
```

## Notlar

- Dijital zoom mevcut pikselleri büyütür; çok uzak/bulanık barkodlar için
  kamera çözünürlüğünü artırmak veya optik zoom kullanmak gerekebilir.
- Önizleme penceresi istemiyorsanız `--no-preview` bayrağını kullanın.
