#!/usr/bin/env python3
"""
karlilik_gui.py — E-ticaret Karlilik Takibi

Sekmeler:
  URUNLER   : urun listesi + duzenleme, kanal karsilastirmasi
  KARAR     : basabas, hedef marj, kampanya simulasyonu
  SATISLAR  : satis kaydi girme ve listeleme
  RAPORLAR  : aylik / yillik ozet, urun ve kanal dagilimi
  AYARLAR   : gider kalemlerini ac/kapa, kanal ve kargo tarifesi

Calistirma:
  python3 karlilik_gui.py     (Mac)
  python  karlilik_gui.py     (Windows)
"""

import sys
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

try:
    from karlilik_core import (Depo, hesapla, basabas, hedef_fiyat,
                               kampanya, rapor, desi, VARSAYILAN_KALEMLER,
                               VARSAYILAN_KARGO, GIDER_KATEGORILERI)
except ImportError:
    print("HATA: karlilik_core.py ayni klasorde olmali.")
    sys.exit(1)


BG, KART, KART2, CIZGI = "#12141a", "#1a1d25", "#212630", "#2c3340"
YAZI, SOLUK = "#e9ecf1", "#8b95a5"
MAVI, YESIL, SARI, KIRMIZI = "#3b82f6", "#10b981", "#f59e0b", "#ef4444"

KALEM_ADLARI = {
    "kdv": "KDV ayrimi",
    "komisyon": "Pazaryeri komisyonu",
    "odeme": "Odeme / POS komisyonu",
    "kargo": "Kargo (desi bazli)",
    "ambalaj": "Ambalaj",
    "iade": "Iade kargo ve hurda",
    "reklam": "Reklam (urun basina)",
    "isletme": "Isletme gideri (paylastirilmis)",
}


def para(x):
    return f"{x:,.2f}"


def marj_rengi(m):
    if m >= 25:
        return YESIL
    if m >= 12:
        return SARI
    return KIRMIZI


class Uygulama(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("E-ticaret Karlilik Takibi")
        self.geometry("1240x840")
        self.minsize(1080, 720)
        self.configure(bg=BG)

        self.depo = Depo()
        self.secili_id = None
        self.girisler = {}

        self._stil()
        self._duzen()
        self.urun_listesini_yenile()
        if self.depo.veri["urunler"]:
            self.tv_urun.selection_set(self.tv_urun.get_children()[0])
            self.urun_secildi()

    # -------------------------------------------------------------- stil
    def _stil(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=KART, foreground=SOLUK,
                    padding=(22, 10), borderwidth=0, font=("Helvetica", 11))
        s.map("TNotebook.Tab", background=[("selected", KART2)],
              foreground=[("selected", YAZI)])
        s.configure("Treeview", background=KART, fieldbackground=KART,
                    foreground=YAZI, borderwidth=0, rowheight=28,
                    font=("Helvetica", 11))
        s.configure("Treeview.Heading", background=KART2, foreground=SOLUK,
                    borderwidth=0, font=("Helvetica", 10, "bold"))
        s.map("Treeview", background=[("selected", "#2f3a4d")])
        s.configure("TCombobox", fieldbackground=KART2, background=KART2,
                    foreground=YAZI, arrowcolor=SOLUK, borderwidth=0)

    def _kart(self, ana, baslik=None):
        f = tk.Frame(ana, bg=KART, highlightbackground=CIZGI,
                     highlightthickness=1)
        if baslik:
            tk.Label(f, text=baslik, bg=KART, fg=SOLUK,
                     font=("Helvetica", 10, "bold")).pack(anchor="w",
                                                          padx=14, pady=(11, 6))
        return f

    def _btn(self, ana, metin, komut, renk=KART2, fg=YAZI, dolgu=9):
        return tk.Button(ana, text=metin, command=komut, bg=renk, fg=fg,
                         bd=0, highlightthickness=0, activebackground=renk,
                         activeforeground=fg, font=("Helvetica", 11),
                         pady=dolgu, cursor="hand2")

    def _giris(self, ana, w=10):
        return tk.Entry(ana, width=w, bg=KART2, fg=YAZI, bd=0,
                        insertbackground=YAZI, highlightbackground=CIZGI,
                        highlightthickness=1, font=("Helvetica", 11))

    # ------------------------------------------------------------- duzen
    def _duzen(self):
        ust = tk.Frame(self, bg=BG)
        ust.pack(fill="x", padx=20, pady=(15, 6))
        tk.Label(ust, text="E-ticaret Karlilik Takibi", bg=BG, fg=YAZI,
                 font=("Helvetica", 20, "bold")).pack(side="left")
        tk.Label(ust, text="   gercek kar, gorunmeyen giderler dahil",
                 bg=BG, fg=SOLUK, font=("Helvetica", 12)).pack(side="left",
                                                               pady=(6, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        self.s_urun = tk.Frame(self.nb, bg=BG)
        self.s_karar = tk.Frame(self.nb, bg=BG)
        self.s_satis = tk.Frame(self.nb, bg=BG)
        self.s_gider = tk.Frame(self.nb, bg=BG)
        self.s_rapor = tk.Frame(self.nb, bg=BG)
        self.s_ayar = tk.Frame(self.nb, bg=BG)
        for f, t in [(self.s_urun, "Urunler"), (self.s_karar, "Karar destek"),
                     (self.s_satis, "Satislar"), (self.s_gider, "Giderler"),
                     (self.s_rapor, "Raporlar"), (self.s_ayar, "Ayarlar")]:
            self.nb.add(f, text=t)

        self._urun_kur()
        self._karar_kur()
        self._satis_kur()
        self._gider_kur()
        self._rapor_kur()
        self._ayar_kur()
        self.nb.bind("<<NotebookTabChanged>>", self._sekme_degisti)

    # ------------------------------------------------------------ URUNLER
    def _urun_kur(self):
        f = self.s_urun
        sol = tk.Frame(f, bg=BG, width=300)
        sol.pack(side="left", fill="y", padx=(0, 14), pady=10)
        sol.pack_propagate(False)

        tk.Label(sol, text="URUNLER", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.tv_urun = ttk.Treeview(sol, columns=("ad",), show="headings",
                                    height=18)
        self.tv_urun.heading("ad", text="Urun")
        self.tv_urun.column("ad", width=280, anchor="w")
        self.tv_urun.pack(fill="both", expand=True)
        self.tv_urun.bind("<<TreeviewSelect>>", lambda e: self.urun_secildi())

        bf = tk.Frame(sol, bg=BG)
        bf.pack(fill="x", pady=8)
        self._btn(bf, "+ Yeni", self.urun_yeni, MAVI, "white").pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        self._btn(bf, "Sil", self.urun_sil).pack(side="left", fill="x",
                                                 expand=True, padx=(4, 0))

        sag = tk.Frame(f, bg=BG)
        sag.pack(side="left", fill="both", expand=True, pady=10)

        form = self._kart(sag, " URUN BILGILERI ")
        form.pack(fill="x")
        gr = tk.Frame(form, bg=KART)
        gr.pack(fill="x", padx=14, pady=(0, 12))

        alanlar = [
            ("ad", "Urun adi", 26, 0, 0, 3),
            ("alis", "Alis fiyati (KDV dahil)", 12, 1, 0, 1),
            ("satis", "Satis fiyati (KDV dahil)", 12, 1, 2, 1),
            ("kdv", "KDV %", 12, 2, 0, 1),
            ("ambalaj", "Ambalaj TL", 12, 2, 2, 1),
            ("en", "Kutu en cm", 12, 3, 0, 1),
            ("boy", "Kutu boy cm", 12, 3, 2, 1),
            ("yuk", "Kutu yuk cm", 12, 4, 0, 1),
            ("kg", "Agirlik kg", 12, 4, 2, 1),
            ("iade", "Iade orani %", 12, 5, 0, 1),
            ("iade_hurda", "Iadenin satilamaz %", 12, 5, 2, 1),
            ("reklam", "Reklam TL/adet", 12, 6, 0, 1),
            ("isletme", "Isletme TL/adet", 12, 6, 2, 1),
            ("kargo_ozel", "Kargo TL (bos = genel ayar)", 12, 7, 0, 1),
        ]
        for anahtar, etiket, w, r, c, span in alanlar:
            tk.Label(gr, text=etiket, bg=KART, fg=SOLUK, anchor="w",
                     font=("Helvetica", 10)).grid(row=r * 2, column=c,
                                                  columnspan=span, sticky="w",
                                                  pady=(6, 1), padx=(0, 12))
            e = self._giris(gr, 30 if anahtar == "ad" else w)
            e.grid(row=r * 2 + 1, column=c, columnspan=span, sticky="w",
                   ipady=3, padx=(0, 12))
            self.girisler[anahtar] = e

        kf = tk.Frame(form, bg=KART)
        kf.pack(fill="x", padx=14, pady=(0, 12))
        self._btn(kf, "Kaydet", self.urun_kaydet, MAVI, "white").pack(
            side="left", padx=(0, 8))
        self.desi_etiket = tk.Label(kf, text="", bg=KART, fg=SOLUK,
                                    font=("Helvetica", 11))
        self.desi_etiket.pack(side="left", padx=8)

        tk.Label(sag, text="KANAL KARSILASTIRMASI", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w",
                                                      pady=(14, 6))
        kol = ("kanal", "kar", "marj", "getiri", "komisyon", "kargo", "toplam")
        self.tv_kanal = ttk.Treeview(sag, columns=kol, show="headings",
                                     height=6)
        for k, t, w, a in [("kanal", "Kanal", 130, "w"),
                           ("kar", "Net kar", 100, "e"),
                           ("marj", "Marj", 80, "e"),
                           ("getiri", "Sermaye getirisi", 130, "e"),
                           ("komisyon", "Komisyon", 100, "e"),
                           ("kargo", "Kargo", 90, "e"),
                           ("toplam", "Toplam gider", 120, "e")]:
            self.tv_kanal.heading(k, text=t)
            self.tv_kanal.column(k, width=w, anchor=a)
        self.tv_kanal.pack(fill="x")
        self.tv_kanal.tag_configure("iyi", foreground=YESIL)
        self.tv_kanal.tag_configure("orta", foreground=SARI)
        self.tv_kanal.tag_configure("kotu", foreground=KIRMIZI)

        self.fark_kart = tk.Frame(sag, bg=KART2, highlightbackground=CIZGI,
                                  highlightthickness=1)
        self.fark_kart.pack(fill="x", pady=(14, 0))
        self.fark_etiket = tk.Label(self.fark_kart, text="", bg=KART2,
                                    fg=YAZI, justify="left",
                                    font=("Helvetica", 11))
        self.fark_etiket.pack(anchor="w", padx=16, pady=12)

    # ------------------------------------------------------------- KARAR
    def _karar_kur(self):
        f = self.s_karar
        ust = tk.Frame(f, bg=BG)
        ust.pack(fill="x", pady=(12, 8))
        tk.Label(ust, text="Kanal:", bg=BG, fg=YAZI,
                 font=("Helvetica", 11)).pack(side="left")
        self.karar_kanal = ttk.Combobox(ust, width=18, state="readonly")
        self.karar_kanal.pack(side="left", padx=8)
        self.karar_kanal.bind("<<ComboboxSelected>>",
                              lambda e: self.karar_yenile())

        self.bb_kart = tk.Frame(f, bg=KART2, highlightbackground=CIZGI,
                                highlightthickness=1)
        self.bb_kart.pack(fill="x", pady=(4, 14))
        self.bb_ust = tk.Label(self.bb_kart, text="BASABAS FIYAT", bg=KART2,
                               fg=SOLUK, font=("Helvetica", 10, "bold"))
        self.bb_ust.pack(anchor="w", padx=18, pady=(13, 2))
        self.bb_ana = tk.Label(self.bb_kart, text="—", bg=KART2, fg=YAZI,
                               font=("Helvetica", 20, "bold"))
        self.bb_ana.pack(anchor="w", padx=18)
        self.bb_alt = tk.Label(self.bb_kart, text="", bg=KART2, fg=SOLUK,
                               font=("Helvetica", 11))
        self.bb_alt.pack(anchor="w", padx=18, pady=(3, 14))

        iki = tk.Frame(f, bg=BG)
        iki.pack(fill="both", expand=True)

        sol = tk.Frame(iki, bg=BG)
        sol.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(sol, text="HEDEF MARJ ICIN FIYAT", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.tv_hedef = ttk.Treeview(sol, columns=("marj", "fiyat", "kar"),
                                     show="headings", height=8)
        for k, t, w in [("marj", "Hedef marj", 110),
                        ("fiyat", "Satis fiyati", 130),
                        ("kar", "Birim kar", 120)]:
            self.tv_hedef.heading(k, text=t)
            self.tv_hedef.column(k, width=w, anchor="e")
        self.tv_hedef.pack(fill="both", expand=True)

        sag = tk.Frame(iki, bg=BG)
        sag.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(sag, text="KAMPANYA SIMULASYONU", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.tv_kamp = ttk.Treeview(
            sag, columns=("ind", "fiyat", "kar", "kat"),
            show="headings", height=8)
        for k, t, w in [("ind", "Indirim", 90), ("fiyat", "Yeni fiyat", 110),
                        ("kar", "Birim kar", 110),
                        ("kat", "Gereken satis", 130)]:
            self.tv_kamp.heading(k, text=t)
            self.tv_kamp.column(k, width=w, anchor="e")
        self.tv_kamp.pack(fill="both", expand=True)
        self.tv_kamp.tag_configure("zarar", foreground=KIRMIZI)
        self.tv_kamp.tag_configure("ok", foreground=YAZI)

    # ------------------------------------------------------------ SATISLAR
    def _satis_kur(self):
        f = self.s_satis
        gir = self._kart(f, " SATIS KAYDI ")
        gir.pack(fill="x", pady=(12, 10))
        g = tk.Frame(gir, bg=KART)
        g.pack(fill="x", padx=14, pady=(0, 12))

        tk.Label(g, text="Urun", bg=KART, fg=SOLUK,
                 font=("Helvetica", 10)).grid(row=0, column=0, sticky="w")
        self.satis_urun = ttk.Combobox(g, width=26, state="readonly")
        self.satis_urun.grid(row=1, column=0, padx=(0, 12), pady=(1, 0))

        tk.Label(g, text="Kanal", bg=KART, fg=SOLUK,
                 font=("Helvetica", 10)).grid(row=0, column=1, sticky="w")
        self.satis_kanal = ttk.Combobox(g, width=16, state="readonly")
        self.satis_kanal.grid(row=1, column=1, padx=(0, 12), pady=(1, 0))

        tk.Label(g, text="Adet", bg=KART, fg=SOLUK,
                 font=("Helvetica", 10)).grid(row=0, column=2, sticky="w")
        self.satis_adet = self._giris(g, 8)
        self.satis_adet.grid(row=1, column=2, padx=(0, 12), ipady=3)

        tk.Label(g, text="Tarih (YYYY-AA-GG)", bg=KART, fg=SOLUK,
                 font=("Helvetica", 10)).grid(row=0, column=3, sticky="w")
        self.satis_tarih = self._giris(g, 14)
        self.satis_tarih.insert(0, date.today().isoformat())
        self.satis_tarih.grid(row=1, column=3, padx=(0, 12), ipady=3)

        tk.Label(g, text="Birim fiyat (bos = urun fiyati)", bg=KART,
                 fg=SOLUK, font=("Helvetica", 10)).grid(row=0, column=4,
                                                        sticky="w")
        self.satis_fiyat = self._giris(g, 14)
        self.satis_fiyat.grid(row=1, column=4, padx=(0, 12), ipady=3)

        self._btn(g, "Ekle", self.satis_ekle, MAVI, "white").grid(
            row=1, column=5, padx=(4, 0))

        bas = tk.Frame(f, bg=BG)
        bas.pack(fill="x", pady=(4, 6))
        tk.Label(bas, text="KAYITLAR", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(side="left")
        self._btn(bas, "Secili kaydi sil", self.satis_sil, KART).pack(
            side="right")
        self._btn(bas, "CSV disa aktar", self.satis_disa, KART).pack(
            side="right", padx=6)

        kol = ("tarih", "urun", "kanal", "adet", "fiyat", "kar")
        self.tv_satis = ttk.Treeview(f, columns=kol, show="headings",
                                     height=16)
        for k, t, w, a in [("tarih", "Tarih", 110, "w"),
                           ("urun", "Urun", 220, "w"),
                           ("kanal", "Kanal", 130, "w"),
                           ("adet", "Adet", 70, "center"),
                           ("fiyat", "Birim fiyat", 110, "e"),
                           ("kar", "Toplam kar", 120, "e")]:
            self.tv_satis.heading(k, text=t)
            self.tv_satis.column(k, width=w, anchor=a)
        self.tv_satis.pack(fill="both", expand=True)

    # ------------------------------------------------------------ GIDERLER
    def _gider_kur(self):
        f = self.s_gider
        gir = self._kart(f, " SABIT GIDER EKLE ")
        gir.pack(fill="x", pady=(12, 10))
        g = tk.Frame(gir, bg=KART)
        g.pack(fill="x", padx=14, pady=(0, 12))

        tk.Label(g, text="Kategori", bg=KART, fg=SOLUK,
                 font=("Helvetica", 10)).grid(row=0, column=0, sticky="w")
        self.gider_kat = ttk.Combobox(g, values=GIDER_KATEGORILERI,
                                      width=22, state="readonly")
        self.gider_kat.set(GIDER_KATEGORILERI[0])
        self.gider_kat.grid(row=1, column=0, padx=(0, 12), pady=(1, 0))

        tk.Label(g, text="Tutar TL", bg=KART, fg=SOLUK,
                 font=("Helvetica", 10)).grid(row=0, column=1, sticky="w")
        self.gider_tutar = self._giris(g, 12)
        self.gider_tutar.grid(row=1, column=1, padx=(0, 12), ipady=3)

        tk.Label(g, text="Donem (YYYY-AA)", bg=KART, fg=SOLUK,
                 font=("Helvetica", 10)).grid(row=0, column=2, sticky="w")
        self.gider_donem = self._giris(g, 12)
        self.gider_donem.insert(0, date.today().strftime("%Y-%m"))
        self.gider_donem.grid(row=1, column=2, padx=(0, 12), ipady=3)

        tk.Label(g, text="Aciklama", bg=KART, fg=SOLUK,
                 font=("Helvetica", 10)).grid(row=0, column=3, sticky="w")
        self.gider_aciklama = self._giris(g, 26)
        self.gider_aciklama.grid(row=1, column=3, padx=(0, 12), ipady=3)

        self._btn(g, "Ekle", self.gider_ekle, MAVI, "white").grid(
            row=1, column=4, padx=(4, 0))

        self.gider_ozet = tk.Frame(f, bg=KART2, highlightbackground=CIZGI,
                                   highlightthickness=1)
        self.gider_ozet.pack(fill="x", pady=(0, 12))
        self.gider_ozet_yazi = tk.Label(self.gider_ozet, text="", bg=KART2,
                                        fg=YAZI, justify="left",
                                        font=("Helvetica", 12))
        self.gider_ozet_yazi.pack(anchor="w", padx=16, pady=12)

        bas = tk.Frame(f, bg=BG)
        bas.pack(fill="x", pady=(0, 6))
        tk.Label(bas, text="GIDER KAYITLARI", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(side="left")
        self._btn(bas, "Secili kaydi sil", self.gider_sil, KART).pack(
            side="right")

        kol = ("donem", "kategori", "tutar", "aciklama")
        self.tv_gider = ttk.Treeview(f, columns=kol, show="headings",
                                     height=14)
        for k, t, w, a in [("donem", "Donem", 110, "w"),
                           ("kategori", "Kategori", 200, "w"),
                           ("tutar", "Tutar", 140, "e"),
                           ("aciklama", "Aciklama", 300, "w")]:
            self.tv_gider.heading(k, text=t)
            self.tv_gider.column(k, width=w, anchor=a)
        self.tv_gider.pack(fill="both", expand=True)

    def gider_ekle(self):
        try:
            tutar = float(self.gider_tutar.get().replace(",", ".") or 0)
        except ValueError:
            messagebox.showwarning("Hata", "Tutar sayi olmali.")
            return
        if tutar <= 0:
            return
        don = self.gider_donem.get().strip()
        if len(don) != 7 or don[4] != "-":
            messagebox.showwarning("Hata", "Donem YYYY-AA seklinde olmali.")
            return
        self.depo.gider_ekle(self.gider_kat.get(), tutar, don,
                             self.gider_aciklama.get().strip())
        self.gider_tutar.delete(0, "end")
        self.gider_aciklama.delete(0, "end")
        self.gider_yenile()

    def gider_sil(self):
        s = self.tv_gider.selection()
        if s:
            self.depo.gider_sil(int(s[0]))
            self.gider_yenile()

    def gider_yenile(self):
        for i in self.tv_gider.get_children():
            self.tv_gider.delete(i)
        for g in sorted(self.depo.veri["giderler"],
                        key=lambda x: (x["donem"], x["kategori"]),
                        reverse=True):
            self.tv_gider.insert("", "end", iid=str(g["id"]), values=(
                g["donem"], g["kategori"], para(g["tutar"]),
                g.get("aciklama", "")))

        birim, don = self.depo.birim_isletme()
        if don:
            top = self.depo.donem_gideri(don)
            adet = self.depo.donem_adedi(don)
            self.gider_ozet_yazi.config(
                text=f"Son donem: {don}\n"
                     f"Toplam sabit gider: {para(top)} TL   |   "
                     f"Satilan adet: {adet}\n"
                     f"Adet basina dusen isletme gideri: {para(birim)} TL")
        else:
            self.gider_ozet_yazi.config(
                text="Henuz satis kaydi yok.\n"
                     "Gider girip Satislar sekmesinden satis ekleyince "
                     "adet basina dusen gider hesaplanir.")

    # ------------------------------------------------------------ RAPORLAR
    def _rapor_kur(self):
        f = self.s_rapor
        ust = tk.Frame(f, bg=BG)
        ust.pack(fill="x", pady=(12, 8))
        tk.Label(ust, text="Donem:", bg=BG, fg=YAZI,
                 font=("Helvetica", 11)).pack(side="left")
        self.rapor_tip = ttk.Combobox(ust, values=["Aylik", "Yillik"],
                                      width=12, state="readonly")
        self.rapor_tip.set("Aylik")
        self.rapor_tip.pack(side="left", padx=8)
        self.rapor_tip.bind("<<ComboboxSelected>>",
                            lambda e: self.rapor_yenile())
        self._btn(ust, "CSV disa aktar", self.rapor_disa, KART, YAZI, 6).pack(
            side="right")

        kol = ("donem", "adet", "ciro", "brut", "sabit", "kar", "marj", "kdv")
        self.tv_rapor = ttk.Treeview(f, columns=kol, show="headings",
                                     height=9)
        for k, t, w, a in [("donem", "Donem", 100, "w"),
                           ("adet", "Adet", 70, "center"),
                           ("ciro", "Ciro", 130, "e"),
                           ("brut", "Brut kar", 130, "e"),
                           ("sabit", "Sabit gider", 130, "e"),
                           ("kar", "NET KAR", 130, "e"),
                           ("marj", "Net marj", 90, "e"),
                           ("kdv", "Odenecek KDV", 120, "e")]:
            self.tv_rapor.heading(k, text=t)
            self.tv_rapor.column(k, width=w, anchor=a)
        self.tv_rapor.pack(fill="x")
        self.tv_rapor.tag_configure("iyi", foreground=YESIL)
        self.tv_rapor.tag_configure("orta", foreground=SARI)
        self.tv_rapor.tag_configure("kotu", foreground=KIRMIZI)
        self.tv_rapor.bind("<<TreeviewSelect>>", lambda e: self.donem_detay())

        alt = tk.Frame(f, bg=BG)
        alt.pack(fill="both", expand=True, pady=(16, 0))

        sol = tk.Frame(alt, bg=BG)
        sol.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(sol, text="URUN DAGILIMI", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.tv_rurun = ttk.Treeview(sol, columns=("ad", "adet", "kar"),
                                     show="headings", height=8)
        for k, t, w, a in [("ad", "Urun", 200, "w"),
                           ("adet", "Adet", 80, "center"),
                           ("kar", "Kar", 130, "e")]:
            self.tv_rurun.heading(k, text=t)
            self.tv_rurun.column(k, width=w, anchor=a)
        self.tv_rurun.pack(fill="both", expand=True)

        sag = tk.Frame(alt, bg=BG)
        sag.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(sag, text="KANAL DAGILIMI", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.tv_rkanal = ttk.Treeview(sag, columns=("ad", "adet", "kar"),
                                      show="headings", height=8)
        for k, t, w, a in [("ad", "Kanal", 200, "w"),
                           ("adet", "Adet", 80, "center"),
                           ("kar", "Kar", 130, "e")]:
            self.tv_rkanal.heading(k, text=t)
            self.tv_rkanal.column(k, width=w, anchor=a)
        self.tv_rkanal.pack(fill="both", expand=True)

    # ------------------------------------------------------------- AYARLAR
    def _ayar_kur(self):
        f = self.s_ayar
        sol = tk.Frame(f, bg=BG)
        sol.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=12)

        kal = self._kart(sol, " HESABA KATILACAK GIDER KALEMLERI ")
        kal.pack(fill="x")
        tk.Label(kal, text="Kapatilan kalem hesaba girmez.",
                 bg=KART, fg=SOLUK, font=("Helvetica", 10)).pack(
            anchor="w", padx=14, pady=(0, 8))
        self.kalem_var = {}
        for anahtar, etiket in KALEM_ADLARI.items():
            v = tk.BooleanVar(value=self.depo.veri["kalemler"].get(
                anahtar, VARSAYILAN_KALEMLER[anahtar]))
            self.kalem_var[anahtar] = v
            tk.Checkbutton(kal, text=etiket, variable=v, bg=KART, fg=YAZI,
                           selectcolor=KART2, activebackground=KART,
                           activeforeground=YAZI, bd=0, highlightthickness=0,
                           font=("Helvetica", 11),
                           command=self.kalem_degisti).pack(anchor="w",
                                                            padx=12, pady=1)
        tk.Frame(kal, bg=KART, height=10).pack()

        kg = self._kart(sol, " KARGO ")
        kg.pack(fill="x", pady=(14, 0))
        ki = tk.Frame(kg, bg=KART)
        ki.pack(fill="x", padx=14, pady=(0, 12))

        ka = {**VARSAYILAN_KARGO, **self.depo.veri.get("kargo", {})}
        self.kargo_yontem = tk.StringVar(value=ka["yontem"])
        tk.Radiobutton(ki, text="Sabit tutar (TL / gonderi)",
                       variable=self.kargo_yontem, value="sabit", bg=KART,
                       fg=YAZI, selectcolor=KART2, activebackground=KART,
                       activeforeground=YAZI, bd=0, highlightthickness=0,
                       font=("Helvetica", 11),
                       command=self.kargo_kaydet).grid(row=0, column=0,
                                                       sticky="w")
        self.kargo_tutar = self._giris(ki, 9)
        self.kargo_tutar.insert(0, str(ka["sabit_tutar"]))
        self.kargo_tutar.grid(row=0, column=1, padx=8, ipady=3)
        self.kargo_tutar.bind("<FocusOut>", lambda e: self.kargo_kaydet())
        self.kargo_tutar.bind("<Return>", lambda e: self.kargo_kaydet())

        tk.Radiobutton(ki, text="Desi tablosuna gore",
                       variable=self.kargo_yontem, value="desi", bg=KART,
                       fg=YAZI, selectcolor=KART2, activebackground=KART,
                       activeforeground=YAZI, bd=0, highlightthickness=0,
                       font=("Helvetica", 11),
                       command=self.kargo_kaydet).grid(row=1, column=0,
                                                       sticky="w", pady=(6, 0))
        tk.Label(ki, text="Urun kartindaki 'Kargo TL' alani doluysa\n"
                          "o urun icin bu ayar gecersiz olur.",
                 bg=KART, fg=SOLUK, justify="left",
                 font=("Helvetica", 10)).grid(row=2, column=0, columnspan=2,
                                              sticky="w", pady=(10, 0))

        sag = tk.Frame(f, bg=BG)
        sag.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=12)
        tk.Label(sag, text="KANALLAR", bg=BG, fg=SOLUK,
                 font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.tv_kanal_ayar = ttk.Treeview(
            sag, columns=("ad", "kom", "ode", "aktif"),
            show="headings", height=7)
        for k, t, w, a in [("ad", "Kanal", 150, "w"),
                           ("kom", "Komisyon %", 110, "e"),
                           ("ode", "Odeme %", 100, "e"),
                           ("aktif", "Aktif", 80, "center")]:
            self.tv_kanal_ayar.heading(k, text=t)
            self.tv_kanal_ayar.column(k, width=w, anchor=a)
        self.tv_kanal_ayar.pack(fill="x")
        self.tv_kanal_ayar.bind("<<TreeviewSelect>>",
                                lambda e: self.kanal_secildi())

        g = tk.Frame(sag, bg=BG)
        g.pack(fill="x", pady=10)
        for etiket, w in [("Kanal adi", 15), ("Komisyon %", 9),
                          ("Odeme %", 9)]:
            tk.Label(g, text=etiket, bg=BG, fg=SOLUK, anchor="w",
                     font=("Helvetica", 10)).grid(
                row=0, column=[e for e, _ in
                               [("Kanal adi", 15), ("Komisyon %", 9),
                                ("Odeme %", 9)]].index(etiket),
                sticky="w", padx=(0, 8))
        self.kanal_ad = self._giris(g, 15)
        self.kanal_ad.grid(row=1, column=0, padx=(0, 8), ipady=3, sticky="w")
        self.kanal_kom = self._giris(g, 9)
        self.kanal_kom.grid(row=1, column=1, padx=(0, 8), ipady=3, sticky="w")
        self.kanal_ode = self._giris(g, 9)
        self.kanal_ode.grid(row=1, column=2, padx=(0, 8), ipady=3, sticky="w")
        self._btn(g, "Kaydet", self.kanal_kaydet, MAVI, "white", 5).grid(
            row=1, column=3, padx=(4, 4))
        self._btn(g, "Ac / Kapa", self.kanal_toggle, KART, YAZI, 5).grid(
            row=1, column=4, padx=4)
        self._btn(g, "Sil", self.kanal_sil, KART, YAZI, 5).grid(
            row=1, column=5, padx=4)
        tk.Label(sag, text="Listeden bir kanala tikla, kutular dolsun. "
                           "Orani degistirip Kaydet'e bas.\n"
                           "Yeni kanal icin kutulari elle doldur.",
                 bg=BG, fg=SOLUK, justify="left",
                 font=("Helvetica", 10)).pack(anchor="w", pady=(8, 0))

        tk.Label(sag, text=f"\nVeri dosyasi:\n{self.depo.yol}", bg=BG,
                 fg=SOLUK, justify="left",
                 font=("Helvetica", 10)).pack(anchor="w", pady=(18, 0))

        self.kanal_ayar_yenile()

    # ============================================================ islevler
    def _kalemler(self):
        return {k: v.get() for k, v in self.kalem_var.items()} \
            if self.kalem_var else self.depo.veri["kalemler"]

    def kalem_degisti(self):
        self.depo.veri["kalemler"] = self._kalemler()
        self.depo.kaydet()
        self.urun_secildi()

    def _sekme_degisti(self, e=None):
        i = self.nb.index(self.nb.select())
        if i == 1:
            self.karar_yenile()
        elif i == 2:
            self.satis_yenile()
        elif i == 3:
            self.gider_yenile()
        elif i == 4:
            self.rapor_yenile()

    # --- urun
    def urun_listesini_yenile(self):
        for i in self.tv_urun.get_children():
            self.tv_urun.delete(i)
        for u in self.depo.veri["urunler"]:
            self.tv_urun.insert("", "end", iid=str(u["id"]), values=(u["ad"],))

    def urun_yeni(self):
        self.secili_id = None
        for k, e in self.girisler.items():
            e.delete(0, "end")
        for k, v in [("kdv", "20"), ("iade", "8"), ("iade_hurda", "40"),
                     ("ambalaj", "0"), ("reklam", "0"), ("isletme", "0"),
                     ("kg", "0")]:
            self.girisler[k].insert(0, v)
        self.girisler["ad"].focus()

    def urun_kaydet(self):
        try:
            u = {"ad": self.girisler["ad"].get().strip()}
            if not u["ad"]:
                messagebox.showwarning("Eksik", "Urun adi gerekli.")
                return
            for k in ("alis", "satis", "kdv", "ambalaj", "en", "boy",
                      "yuk", "kg", "iade", "iade_hurda", "reklam",
                      "isletme", "kargo_ozel"):
                t = self.girisler[k].get().strip().replace(",", ".")
                u[k] = float(t) if t else 0.0
        except ValueError:
            messagebox.showwarning("Hata", "Sayisal alanlara sayi gir.")
            return
        if u["alis"] <= 0 or u["satis"] <= 0:
            messagebox.showwarning("Eksik", "Alis ve satis fiyati gerekli.")
            return

        if self.secili_id:
            u["id"] = self.secili_id
            self.depo.urun_guncelle(u)
        else:
            self.secili_id = self.depo.urun_ekle(u)
        self.urun_listesini_yenile()
        self.tv_urun.selection_set(str(self.secili_id))
        self.urun_secildi()

    def urun_sil(self):
        s = self.tv_urun.selection()
        if not s:
            return
        u = self.depo.urun_bul(int(s[0]))
        if messagebox.askyesno("Sil", f"{u['ad']} silinsin mi?\n"
                                      f"Satis kayitlari da silinecek."):
            self.depo.urun_sil(int(s[0]))
            self.secili_id = None
            self.urun_listesini_yenile()
            for e in self.girisler.values():
                e.delete(0, "end")
            for i in self.tv_kanal.get_children():
                self.tv_kanal.delete(i)

    def urun_secildi(self):
        s = self.tv_urun.selection()
        if not s:
            return
        self.secili_id = int(s[0])
        u = self.depo.urun_bul(self.secili_id)
        if not u:
            return
        for k, e in self.girisler.items():
            e.delete(0, "end")
            v = u.get(k, "")
            e.insert(0, str(v) if v not in (None, "") else "")

        d = desi(u.get("en"), u.get("boy"), u.get("yuk"), u.get("kg"))
        self.desi_etiket.config(text=f"Desi: {d:.2f}")

        kal = self._kalemler()
        for i in self.tv_kanal.get_children():
            self.tv_kanal.delete(i)
        sonuclar = []
        for k in self.depo.veri["kanallar"]:
            if not k.get("aktif", True):
                continue
            h = hesapla(u, k, kal, self.depo.veri["tarife"], None,
                        self.depo.veri.get("kargo"))
            sonuclar.append(h)
            tag = ("iyi" if h["marj"] >= 25 else
                   "orta" if h["marj"] >= 12 else "kotu")
            self.tv_kanal.insert("", "end", tags=(tag,), values=(
                k["ad"], para(h["kar"]), f"%{h['marj']:.1f}",
                f"%{h['getiri']:.1f}", para(h["komisyon"]),
                para(h["kargo"]), para(h["gider_toplam"])))

        if sonuclar:
            en_iyi = max(sonuclar, key=lambda x: x["kar"])
            basit = {x: False for x in VARSAYILAN_KALEMLER}
            basit.update({"komisyon": True, "kargo": True})
            kanal = self.depo.kanal_bul(en_iyi["kanal"])
            hb = hesapla(u, kanal, basit, self.depo.veri["tarife"], None,
                         self.depo.veri.get("kargo"))
            fark = hb["kar"] - en_iyi["kar"]
            oran = (fark / hb["kar"] * 100) if hb["kar"] else 0
            self.fark_etiket.config(
                text=f"Basit hesap (alis · satis · komisyon · kargo): "
                     f"{para(hb['kar'])} TL\n"
                     f"Gercek hesap (acik kalemlerin tamami):        "
                     f"{para(en_iyi['kar'])} TL\n"
                     f"Aradaki fark: {para(fark)} TL   (%{oran:.0f} sapma)   "
                     f"— {en_iyi['kanal']} uzerinden")

    # --- karar
    def karar_yenile(self):
        aktif = [k["ad"] for k in self.depo.veri["kanallar"]
                 if k.get("aktif", True)]
        self.karar_kanal["values"] = aktif
        if not self.karar_kanal.get() and aktif:
            self.karar_kanal.set(aktif[0])
        if not self.secili_id or not self.karar_kanal.get():
            return
        u = self.depo.urun_bul(self.secili_id)
        k = self.depo.kanal_bul(self.karar_kanal.get())
        if not u or not k:
            return
        kal = self._kalemler()
        tarife = self.depo.veri["tarife"]

        kargo_a = self.depo.veri.get("kargo")
        bb = basabas(u, k, kal, tarife, kargo_a)
        pay = u["satis"] - bb
        self.bb_ana.config(text=f"{para(bb)} TL",
                           fg=YESIL if pay > 0 else KIRMIZI)
        if pay > 0:
            self.bb_alt.config(
                text=f"Mevcut fiyat {para(u['satis'])} TL · "
                     f"en fazla %{pay/u['satis']*100:.1f} indirim yapabilirsin")
        else:
            self.bb_alt.config(text="Mevcut fiyat basabasin ALTINDA — "
                                    "her satista zarar ediyorsun.")

        for i in self.tv_hedef.get_children():
            self.tv_hedef.delete(i)
        for m in (10, 15, 20, 25, 30, 35, 40):
            fi = hedef_fiyat(u, k, m, kal, tarife, kargo_a)
            h = hesapla(u, k, kal, tarife, fi, kargo_a)
            self.tv_hedef.insert("", "end", values=(
                f"%{m}", para(fi), para(h["kar"])))

        for i in self.tv_kamp.get_children():
            self.tv_kamp.delete(i)
        for ind in (5, 10, 15, 20, 25, 30, 40):
            c = kampanya(u, k, ind, kal, tarife, kargo_a)
            if c["kat"] is None:
                self.tv_kamp.insert("", "end", tags=("zarar",), values=(
                    f"%{ind}", para(c["fiyat"]), para(c["kar"]), "ZARAR"))
            else:
                self.tv_kamp.insert("", "end", tags=("ok",), values=(
                    f"%{ind}", para(c["fiyat"]), para(c["kar"]),
                    f"{c['kat']:.2f}x"))

    # --- satis
    def satis_yenile(self):
        self.satis_urun["values"] = [u["ad"] for u in self.depo.veri["urunler"]]
        self.satis_kanal["values"] = [k["ad"] for k in self.depo.veri["kanallar"]
                                      if k.get("aktif", True)]
        for i in self.tv_satis.get_children():
            self.tv_satis.delete(i)
        kal = self._kalemler()
        for s in sorted(self.depo.veri["satislar"],
                        key=lambda x: x["tarih"], reverse=True):
            u = self.depo.urun_bul(s["urun_id"])
            k = self.depo.kanal_bul(s["kanal"])
            if not u or not k:
                continue
            h = hesapla(u, k, kal, self.depo.veri["tarife"],
                        s.get("birim_fiyat"), self.depo.veri.get("kargo"))
            self.tv_satis.insert("", "end", iid=str(s["id"]), values=(
                s["tarih"], u["ad"], s["kanal"], s["adet"],
                para(h["satis"]), para(h["kar"] * s["adet"])))

    def satis_ekle(self):
        ad = self.satis_urun.get()
        kanal = self.satis_kanal.get()
        if not ad or not kanal:
            messagebox.showwarning("Eksik", "Urun ve kanal sec.")
            return
        try:
            adet = int(self.satis_adet.get())
        except ValueError:
            messagebox.showwarning("Hata", "Adet sayi olmali.")
            return
        fiyat = self.satis_fiyat.get().strip().replace(",", ".")
        fiyat = float(fiyat) if fiyat else None
        urun = next(u for u in self.depo.veri["urunler"] if u["ad"] == ad)
        self.depo.satis_ekle(urun["id"], kanal, adet,
                             self.satis_tarih.get().strip() or None, fiyat)
        self.satis_adet.delete(0, "end")
        self.satis_fiyat.delete(0, "end")
        self.satis_yenile()

    def satis_sil(self):
        s = self.tv_satis.selection()
        if s:
            self.depo.satis_sil(int(s[0]))
            self.satis_yenile()

    def satis_disa(self):
        yol = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="satislar.csv")
        if not yol:
            return
        with open(yol, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["tarih", "urun", "kanal", "adet", "birim_fiyat",
                        "toplam_kar"])
            for i in self.tv_satis.get_children():
                w.writerow(self.tv_satis.item(i)["values"])
        messagebox.showinfo("Kaydedildi", yol)

    # --- rapor
    def rapor_yenile(self):
        tip = "ay" if self.rapor_tip.get() == "Aylik" else "yil"
        self.depo.veri["kalemler"] = self._kalemler()
        self.son_rapor = rapor(self.depo, tip)
        for i in self.tv_rapor.get_children():
            self.tv_rapor.delete(i)
        for don, g in self.son_rapor.items():
            tag = ("iyi" if g["marj"] >= 25 else
                   "orta" if g["marj"] >= 12 else "kotu")
            self.tv_rapor.insert("", "end", iid=don, tags=(tag,), values=(
                don, g["adet"], para(g["ciro"]),
                para(g.get("brut_kar", g["kar"])),
                para(g.get("sabit_gider", 0)),
                para(g["kar"]), f"%{g['marj']:.1f}", para(g["kdv"])))
        cocuklar = self.tv_rapor.get_children()
        if cocuklar:
            self.tv_rapor.selection_set(cocuklar[-1])
            self.donem_detay()

    def donem_detay(self):
        s = self.tv_rapor.selection()
        if not s or not hasattr(self, "son_rapor"):
            return
        g = self.son_rapor.get(s[0])
        if not g:
            return
        for tv, veri in [(self.tv_rurun, g["urunler"]),
                         (self.tv_rkanal, g["kanallar"])]:
            for i in tv.get_children():
                tv.delete(i)
            for ad, v in sorted(veri.items(), key=lambda x: -x[1]["kar"]):
                tv.insert("", "end", values=(ad, v["adet"], para(v["kar"])))

    def rapor_disa(self):
        if not hasattr(self, "son_rapor"):
            return
        yol = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="rapor.csv")
        if not yol:
            return
        with open(yol, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["donem", "adet", "ciro", "degisken_maliyet",
                        "brut_kar", "sabit_gider", "net_kar", "net_marj",
                        "kdv"])
            for don, g in self.son_rapor.items():
                w.writerow([don, g["adet"], f"{g['ciro']:.2f}",
                            f"{g['maliyet']:.2f}",
                            f"{g.get('brut_kar', g['kar']):.2f}",
                            f"{g.get('sabit_gider', 0):.2f}",
                            f"{g['kar']:.2f}", f"{g['marj']:.1f}",
                            f"{g['kdv']:.2f}"])
        messagebox.showinfo("Kaydedildi", yol)

    # --- kanal ayarlari
    def kargo_kaydet(self):
        try:
            tutar = float(self.kargo_tutar.get().replace(",", ".") or 0)
        except ValueError:
            tutar = VARSAYILAN_KARGO["sabit_tutar"]
        self.depo.veri["kargo"] = {"yontem": self.kargo_yontem.get(),
                                   "sabit_tutar": tutar}
        self.depo.kaydet()
        self.urun_secildi()

    def kanal_ayar_yenile(self):
        for i in self.tv_kanal_ayar.get_children():
            self.tv_kanal_ayar.delete(i)
        for k in self.depo.veri["kanallar"]:
            self.tv_kanal_ayar.insert("", "end", values=(
                k["ad"], f"{k.get('komisyon',0):.1f}",
                f"{k.get('odeme',0):.1f}",
                "acik" if k.get("aktif", True) else "kapali"))

    def kanal_secildi(self):
        s = self.tv_kanal_ayar.selection()
        if not s:
            return
        ad = self.tv_kanal_ayar.item(s[0])["values"][0]
        k = self.depo.kanal_bul(str(ad))
        if not k:
            return
        self.kanal_ad.delete(0, "end")
        self.kanal_ad.insert(0, k["ad"])
        self.kanal_kom.delete(0, "end")
        self.kanal_kom.insert(0, f"{k.get('komisyon', 0):g}")
        self.kanal_ode.delete(0, "end")
        self.kanal_ode.insert(0, f"{k.get('odeme', 0):g}")

    def kanal_sil(self):
        s = self.tv_kanal_ayar.selection()
        if not s:
            return
        ad = str(self.tv_kanal_ayar.item(s[0])["values"][0])
        kullanim = sum(1 for x in self.depo.veri["satislar"]
                       if x["kanal"] == ad)
        mesaj = f"{ad} silinsin mi?"
        if kullanim:
            mesaj += f"\n\nDIKKAT: bu kanalda {kullanim} satis kaydi var, "
            mesaj += "raporlarda gorunmez olur."
        if messagebox.askyesno("Sil", mesaj):
            self.depo.veri["kanallar"] = [
                x for x in self.depo.veri["kanallar"] if x["ad"] != ad]
            self.depo.kaydet()
            self.kanal_ayar_yenile()
            self.urun_secildi()

    def kanal_kaydet(self):
        ad = self.kanal_ad.get().strip()
        if not ad:
            return
        try:
            kom = float(self.kanal_kom.get().replace(",", ".") or 0)
            ode = float(self.kanal_ode.get().replace(",", ".") or 0)
        except ValueError:
            messagebox.showwarning("Hata", "Komisyon ve odeme sayi olmali.")
            return
        mevcut = self.depo.kanal_bul(ad)
        if mevcut:
            mevcut.update({"komisyon": kom, "odeme": ode})
        else:
            self.depo.veri["kanallar"].append({
                "ad": ad, "komisyon": kom, "odeme": ode,
                "kargo_saticida": True, "aktif": True})
        self.depo.kaydet()
        self.kanal_ad.delete(0, "end")
        self.kanal_kom.delete(0, "end")
        self.kanal_ode.delete(0, "end")
        self.kanal_ayar_yenile()
        self.urun_secildi()

    def kanal_toggle(self):
        s = self.tv_kanal_ayar.selection()
        if not s:
            return
        ad = self.tv_kanal_ayar.item(s[0])["values"][0]
        k = self.depo.kanal_bul(ad)
        if k:
            k["aktif"] = not k.get("aktif", True)
            self.depo.kaydet()
            self.kanal_ayar_yenile()
            self.urun_secildi()


if __name__ == "__main__":
    Uygulama().mainloop()
