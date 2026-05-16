# Citation Converter — Atıf Dönüştürücü

Kopyala-yapıştır yapılan atıfları 8 farklı formata otomatik dönüştüren hafif masaüstü uygulaması.

## İndirme

👉 [Releases sayfasından indirin](../../releases/latest)

Windows 10/11 (64-bit) — kurulum gerekmez, ZIP'i açıp exe'yi çalıştırın.

## Özellikler

- Yapıştırılan atıfı otomatik tanır (Nature/Springer, APA, Chicago, Harvard, Vancouver, MLA, BibTeX)
- Tüm formatları aynı anda gösterir
- Her format için tek tıkla kopyalama
- API çağrısı yok — tamamen yerel çalışır, internet bağlantısı gerekmez

## Desteklenen Çıktı Formatları

| Format | Açıklama |
|--------|----------|
| APA | 7th Edition |
| IEEE | — |
| Springer/Nature | — |
| Chicago | Notes and Bibliography |
| Harvard | — |
| MLA | 9th Edition |
| BibTeX | LaTeX için |
| Vancouver | Tıp/biyomedikal |

## Kullanım

1. Uygulamayı açın
2. Atıfı giriş kutusuna yapıştırın
3. 8 formattaki karşılıkları anında görün, istediğinizi kopyalayın

### Örnek

**Giriş** (IEEE formatında bir atıf):

```
S. E. KARA, O. YİĞİD, M. ŞEN, and M. HÜSEYİNOĞLU, "Model Predictive Trajectory Tracking
Control of 2 DoFs SCARA Robot under External Force Acting to the Tip along the Trajectory,"
Dicle University Journal of Engineering (DUJE), vol. 14, no. 2, pp. 325-332, Jun. 2023.
```

**Çıktı** (otomatik dönüştürülen formatlar):

```
APA
Kara, S. E., Yiğid, O., Şen, M., & Hüseyinoğlu, M. (2023). Model predictive trajectory
tracking control of 2 DoFs SCARA robot under external force acting to the tip along the
trajectory. Dicle University Journal of Engineering (DUJE), 14(2), 325-332.

Chicago
Kara, S. E., O. Yiğid, M. Şen, M. Hüseyinoğlu. "Model Predictive Trajectory Tracking
Control of 2 DoFs SCARA Robot..." Dicle University Journal of Engineering (DUJE) 14,
no. 2 (2023): 325-332.

Harvard
Kara, S. E. et al., 2023. Model predictive trajectory tracking control...
Dicle University Journal of Engineering (DUJE), 14(2), pp. 325-332.

BibTeX
@article{kara2023,
  author  = {KARA, S. E. and YİĞİD, O. and ŞEN, M. and HÜSEYİNOĞLU, M.},
  title   = {Model Predictive Trajectory Tracking Control of 2 DoFs SCARA Robot...},
  journal = {Dicle University Journal of Engineering (DUJE)},
  volume  = {14},
  number  = {2},
  pages   = {325--332},
  year    = {2023},
}
```

## Kaynak Koddan Çalıştırma

```bash
pip install PyQt6
python main.py
```

**Gereksinimler:** Python 3.9+ · PyQt6

## Tekrar Build Alma

```bash
pip install pyinstaller
pyinstaller citation_converter.spec
```

Exe `dist/CitationConverter_v1.0-beta/` klasöründe oluşur.

## Lisans

[MIT](LICENSE)
