#!/usr/bin/env python3
"""
karlilik_core.py — E-ticaret karlilik hesap motoru

Tum gider kalemleri OPSIYONEL. Her birinin "aktif" bayragi var,
kapatilirsa hesaba girmez. Boylece basit bir hesapla baslayip
ihtiyac olduk\u00e7a kalem eklenebilir.

Veriler JSON dosyasinda tutulur, sunucu gerekmez.
"""

import json
import os
from datetime import datetime, date


# ---------------------------------------------------------------- ayarlar
VARSAYILAN_TARIFE = [
    (1, 62.0), (2, 74.0), (3, 86.0), (5, 108.0),
    (10, 165.0), (15, 220.0), (20, 275.0),
]

VARSAYILAN_KANALLAR = [
    {"ad": "Trendyol",    "komisyon": 21.5, "odeme": 0.0,
     "kargo_saticida": True,  "aktif": True},
    {"ad": "Hepsiburada", "komisyon": 19.0, "odeme": 0.0,
     "kargo_saticida": True,  "aktif": True},
    {"ad": "Amazon TR",   "komisyon": 15.0, "odeme": 0.0,
     "kargo_saticida": True,  "aktif": False},
    {"ad": "Kendi sitem", "komisyon": 0.0,  "odeme": 2.9,
     "kargo_saticida": True,  "aktif": True},
]

# kargo hesap yontemi
VARSAYILAN_KARGO = {
    "yontem": "sabit",   # "sabit" veya "desi"
    "sabit_tutar": 62.0, # kargo yontemi "sabit" ise urun basina bu tutar
}

# sabit gider kategorileri
GIDER_KATEGORILERI = [
    "Kira", "Elektrik", "Su", "Dogalgaz", "Internet / telefon",
    "Personel maasi", "SGK / vergi", "Yemek", "Muhasebe",
    "Depo / lojistik", "Yazilim / abonelik", "Reklam (genel)", "Diger",
]

# hangi gider kalemleri acik
VARSAYILAN_KALEMLER = {
    "kdv":        True,   # KDV ayrimi yap
    "komisyon":   True,   # pazaryeri komisyonu
    "odeme":      True,   # sanal POS / odeme komisyonu
    "kargo":      True,   # kargo (desi bazli)
    "ambalaj":    True,   # kutu, dolgu, etiket
    "iade":       True,   # iade kargosu ve hurda
    "reklam":     False,  # urun basina reklam maliyeti
    "isletme":    False,  # depo, personel vb. paylastirilmis gider
}


def desi(en, boy, yuk, kg, bolen=3000):
    """Kargo desi: hacimsel ve fiili agirliktan buyuk olani."""
    if not all([en, boy, yuk]):
        return kg or 0.0
    hacim = (en * boy * yuk) / bolen
    return max(hacim, kg or 0.0)


def kargo_ucreti(d, tarife=None):
    tarife = tarife or VARSAYILAN_TARIFE
    for ust, fiyat in tarife:
        if d <= ust:
            return fiyat
    son_ust, son_fiyat = tarife[-1]
    return son_fiyat + (d - son_ust) * 12.0


# ------------------------------------------------------------- ana hesap
def hesapla(urun, kanal, kalemler=None, tarife=None, satis_fiyati=None,
            kargo_ayar=None):
    """
    Tek urun + tek kanal icin karlilik dokumu.
    Kapali kalemler 0 doner ama anahtar yine bulunur (rapor kolayligi).
    """
    k = {**VARSAYILAN_KALEMLER, **(kalemler or {})}
    satis = satis_fiyati if satis_fiyati is not None else urun["satis"]
    alis = urun["alis"]
    kdv_o = (urun.get("kdv", 20) / 100) if k["kdv"] else 0.0

    alis_net = alis / (1 + kdv_o)
    satis_net = satis / (1 + kdv_o)
    net_kdv = (satis - satis_net) - (alis - alis_net)

    komisyon = satis * (kanal.get("komisyon", 0) / 100) if k["komisyon"] else 0.0
    odeme = satis * (kanal.get("odeme", 0) / 100) if k["odeme"] else 0.0

    ka = {**VARSAYILAN_KARGO, **(kargo_ayar or {})}
    d = desi(urun.get("en"), urun.get("boy"), urun.get("yuk"),
             urun.get("kg"), urun.get("desi_bolen", 3000))
    if k["kargo"] and kanal.get("kargo_saticida", True):
        if urun.get("kargo_ozel"):          # urune ozel sabit tutar
            kargo = float(urun["kargo_ozel"])
        elif ka["yontem"] == "sabit":
            kargo = float(ka["sabit_tutar"])
        else:
            kargo = kargo_ucreti(d, tarife)
    else:
        kargo = 0.0

    ambalaj = urun.get("ambalaj", 0.0) if k["ambalaj"] else 0.0

    if k["iade"]:
        oran = urun.get("iade", 0) / 100
        hurda = urun.get("iade_hurda", 40) / 100
        iade_kargo = kargo * 2 * oran
        iade_kayip = alis_net * oran * hurda
    else:
        iade_kargo = iade_kayip = 0.0

    reklam = urun.get("reklam", 0.0) if k["reklam"] else 0.0
    isletme = urun.get("isletme", 0.0) if k["isletme"] else 0.0

    giderler = (alis_net + komisyon + odeme + kargo + ambalaj
                + iade_kargo + iade_kayip + reklam + isletme)
    kar = satis_net - giderler

    return {
        "kanal": kanal["ad"],
        "satis": satis, "satis_net": satis_net,
        "alis": alis, "alis_net": alis_net,
        "kdv": net_kdv, "desi": d,
        "komisyon": komisyon, "odeme": odeme, "kargo": kargo,
        "ambalaj": ambalaj, "iade_kargo": iade_kargo,
        "iade_kayip": iade_kayip, "reklam": reklam, "isletme": isletme,
        "gider_toplam": giderler,
        "kar": kar,
        "marj": (kar / satis_net * 100) if satis_net else 0.0,
        "getiri": (kar / alis_net * 100) if alis_net else 0.0,
    }


def basabas(urun, kanal, kalemler=None, tarife=None, kargo_ayar=None):
    """Zarar etmemek icin gereken en dusuk satis fiyati."""
    dus, ust = 0.01, max(urun["alis"] * 30, 100)
    for _ in range(90):
        orta = (dus + ust) / 2
        if hesapla(urun, kanal, kalemler, tarife, orta,
                   kargo_ayar)["kar"] < 0:
            dus = orta
        else:
            ust = orta
    return ust


def hedef_fiyat(urun, kanal, hedef_marj, kalemler=None, tarife=None,
                kargo_ayar=None):
    """Istenen kar marjini veren satis fiyati."""
    dus, ust = 0.01, max(urun["alis"] * 40, 200)
    for _ in range(90):
        orta = (dus + ust) / 2
        if hesapla(urun, kanal, kalemler, tarife, orta,
                   kargo_ayar)["marj"] < hedef_marj:
            dus = orta
        else:
            ust = orta
    return ust


def kampanya(urun, kanal, indirim_yuzde, kalemler=None, tarife=None,
             kargo_ayar=None):
    """Indirimde ayni kari korumak icin gereken satis kati."""
    temel = hesapla(urun, kanal, kalemler, tarife, None, kargo_ayar)["kar"]
    yeni_fiyat = urun["satis"] * (1 - indirim_yuzde / 100)
    yeni = hesapla(urun, kanal, kalemler, tarife, yeni_fiyat,
                   kargo_ayar)["kar"]
    kat = (temel / yeni) if yeni > 0 else None
    return {"indirim": indirim_yuzde, "fiyat": yeni_fiyat,
            "kar": yeni, "kat": kat, "temel_kar": temel}


# ------------------------------------------------------------- veri katmani
class Depo:
    """JSON tabanli basit veri deposu."""

    def __init__(self, yol=None):
        self.yol = yol or os.path.join(
            os.path.expanduser("~"), ".karlilik_verileri.json")
        self.veri = {"urunler": [], "kanallar": VARSAYILAN_KANALLAR,
                     "satislar": [], "kalemler": VARSAYILAN_KALEMLER,
                     "tarife": VARSAYILAN_TARIFE,
                     "kargo": dict(VARSAYILAN_KARGO),
                     "giderler": []}
        self.yukle()

    def yukle(self):
        if os.path.exists(self.yol):
            try:
                with open(self.yol, encoding="utf-8") as f:
                    gelen = json.load(f)
                self.veri.update(gelen)
                # tarife listesi JSON'dan list-of-list gelir, tuple'a cevir
                self.veri["tarife"] = [tuple(x) for x in self.veri["tarife"]]
            except (json.JSONDecodeError, OSError):
                pass

    def kaydet(self):
        try:
            with open(self.yol, "w", encoding="utf-8") as f:
                json.dump(self.veri, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    # --- urun
    def urun_ekle(self, urun):
        urun["id"] = max([u.get("id", 0) for u in self.veri["urunler"]] + [0]) + 1
        self.veri["urunler"].append(urun)
        self.kaydet()
        return urun["id"]

    def urun_guncelle(self, urun):
        for i, u in enumerate(self.veri["urunler"]):
            if u["id"] == urun["id"]:
                self.veri["urunler"][i] = urun
                self.kaydet()
                return True
        return False

    def urun_sil(self, urun_id):
        self.veri["urunler"] = [u for u in self.veri["urunler"]
                                if u["id"] != urun_id]
        self.veri["satislar"] = [s for s in self.veri["satislar"]
                                 if s["urun_id"] != urun_id]
        self.kaydet()

    def urun_bul(self, urun_id):
        for u in self.veri["urunler"]:
            if u["id"] == urun_id:
                return u
        return None

    # --- satis
    def satis_ekle(self, urun_id, kanal_ad, adet, tarih=None,
                   birim_fiyat=None):
        kayit = {
            "id": max([s.get("id", 0) for s in self.veri["satislar"]] + [0]) + 1,
            "urun_id": urun_id, "kanal": kanal_ad, "adet": adet,
            "tarih": tarih or date.today().isoformat(),
            "birim_fiyat": birim_fiyat,
        }
        self.veri["satislar"].append(kayit)
        self.kaydet()
        return kayit["id"]

    def satis_sil(self, satis_id):
        self.veri["satislar"] = [s for s in self.veri["satislar"]
                                 if s["id"] != satis_id]
        self.kaydet()

    # --- sabit giderler
    def gider_ekle(self, kategori, tutar, donem, aciklama=""):
        kayit = {
            "id": max([g.get("id", 0) for g in self.veri["giderler"]] + [0]) + 1,
            "kategori": kategori, "tutar": float(tutar),
            "donem": donem, "aciklama": aciklama,
        }
        self.veri["giderler"].append(kayit)
        self.kaydet()
        return kayit["id"]

    def gider_sil(self, gid):
        self.veri["giderler"] = [g for g in self.veri["giderler"]
                                 if g["id"] != gid]
        self.kaydet()

    def donem_gideri(self, donem):
        """Belirli bir ayin (YYYY-MM) toplam sabit gideri."""
        return sum(g["tutar"] for g in self.veri["giderler"]
                   if g["donem"] == donem)

    def donem_adedi(self, donem):
        """Belirli bir ayda satilan toplam adet."""
        top = 0
        for s in self.veri["satislar"]:
            if s["tarih"][:7] == donem:
                top += s["adet"]
        return top

    def birim_isletme(self, donem=None):
        """
        Adet basina dusen sabit gider.
        donem verilmezse, satis kaydi olan son ayi kullanir.
        """
        if donem is None:
            aylar = sorted({s["tarih"][:7] for s in self.veri["satislar"]})
            if not aylar:
                return 0.0, None
            donem = aylar[-1]
        adet = self.donem_adedi(donem)
        gider = self.donem_gideri(donem)
        if adet == 0:
            return 0.0, donem
        return gider / adet, donem

    def kanal_bul(self, ad):
        for k in self.veri["kanallar"]:
            if k["ad"] == ad:
                return k
        return None


# ---------------------------------------------------------------- raporlar
def _donem(tarih_str, tip):
    d = datetime.fromisoformat(tarih_str).date()
    return d.strftime("%Y-%m") if tip == "ay" else d.strftime("%Y")


def rapor(depo, tip="ay"):
    """
    Satis kayitlarindan donemsel rapor uretir.
    tip: "ay" veya "yil"
    """
    donemler = {}
    for s in depo.veri["satislar"]:
        u = depo.urun_bul(s["urun_id"])
        k = depo.kanal_bul(s["kanal"])
        if not u or not k:
            continue
        h = hesapla(u, k, depo.veri["kalemler"], depo.veri["tarife"],
                    s.get("birim_fiyat"), depo.veri.get("kargo"))
        d = _donem(s["tarih"], tip)
        g = donemler.setdefault(d, {
            "ciro": 0.0, "kar": 0.0, "adet": 0, "maliyet": 0.0,
            "kdv": 0.0, "urunler": {}, "kanallar": {},
        })
        adet = s["adet"]
        g["ciro"] += h["satis"] * adet
        g["kar"] += h["kar"] * adet
        g["maliyet"] += h["gider_toplam"] * adet
        g["kdv"] += h["kdv"] * adet
        g["adet"] += adet

        ur = g["urunler"].setdefault(u["ad"], {"adet": 0, "kar": 0.0,
                                               "ciro": 0.0})
        ur["adet"] += adet
        ur["kar"] += h["kar"] * adet
        ur["ciro"] += h["satis"] * adet

        ka = g["kanallar"].setdefault(k["ad"], {"adet": 0, "kar": 0.0,
                                                "ciro": 0.0})
        ka["adet"] += adet
        ka["kar"] += h["kar"] * adet
        ka["ciro"] += h["satis"] * adet

    # sabit giderleri donemlere dagit
    for don, g in donemler.items():
        if tip == "ay":
            sabit = depo.donem_gideri(don)
        else:
            sabit = sum(x["tutar"] for x in depo.veri["giderler"]
                        if x["donem"].startswith(don))
        g["brut_kar"] = g["kar"]
        g["sabit_gider"] = sabit
        g["kar"] = g["brut_kar"] - sabit
        g["marj"] = (g["kar"] / g["ciro"] * 100) if g["ciro"] else 0.0
        g["brut_marj"] = (g["brut_kar"] / g["ciro"] * 100) if g["ciro"] else 0.0
    return dict(sorted(donemler.items()))
