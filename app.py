
import re
import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO
try:
    import qrcode
except Exception:
    qrcode = None

try:
    import serial
except Exception:
    serial = None

APP_DIR = Path(__file__).resolve().parent
DB = APP_DIR / "kayacar_v02.db"
LOGO_PATH = APP_DIR / "kayacar_logo.png"
BRAND_BOARD_PATH = APP_DIR / "kayacar_brand_board.png"

# -----------------------------
# MASTER RECIPES (% w/w)
# -----------------------------
PRODUCTS = {
    "Lastik Parlatıcı Jel": {
        "code":"KC-LPJ-SOP-003","platform":"P3 Lastik","ph":"6,5–7,5",
        "steps":[
            ("Deiyonize Su",87.75),("Polybutene Ham",7.0),("Silikon Yağı 350 cSt",1.5),
            ("Noniyonik Emülgatör",2.5),("DPM",0.5),("Islatıcı",0.2),("Carbomer 940",0.35),
            ("Koruyucu",0.1),("Parfüm + Boya",0.1)
        ]
    },
    "Sıvı Lastik Parlatıcı": {
        "code":"KC-SLP-SOP-003","platform":"P3 Lastik","ph":"Pilot",
        "steps":[
            ("Deiyonize Su",88.5),("Polybutene Ham",6.0),("Silikon Yağı 350 cSt",1.5),
            ("Noniyonik Emülgatör",2.5),("DPM",1.0),("Islatıcı",0.2),("Koruyucu",0.1),("Parfüm + Boya",0.2)
        ]
    },
    "Torpido Temizleme & Bakım Sütü": {
        "code":"KC-TBS-SOP-003","platform":"P2 Silikon Bakım","ph":"7,0–7,5",
        "steps":[
            ("Deiyonize Su",92.45),("%25 PDMS Silikon Emülsiyonu",5.0),("APG",1.0),("CAPB",0.5),
            ("DPM",0.5),("GLDA",0.1),("Sodyum Sitrat",0.2),("Koruyucu",0.1),("Parfüm",0.15)
        ]
    },
    "Normal Oto Yıkama Şampuanı": {
        "code":"KC-NOS-SOP-003","platform":"P1 Şampuan","ph":"7,5–8,5",
        "steps":[
            ("Deiyonize Su",80.745),("SLES %70",10.0),("CAPB",5.0),("APG",2.0),
            ("Sodyum Sitrat",0.3),("GLDA",0.2),("NaCl",1.5),("Koruyucu",0.1),("Parfüm",0.15),("Boya",0.005)
        ]
    },
    "Pembe Oto Yıkama Şampuanı": {
        "code":"KC-POS-SOP-003","platform":"P1 Şampuan","ph":"7,5–8,5",
        "steps":[
            ("Deiyonize Su",80.735),("SLES %70",10.0),("CAPB",5.0),("APG",2.0),
            ("Sodyum Sitrat",0.3),("GLDA",0.2),("NaCl",1.5),("Koruyucu",0.1),("Parfüm",0.15),
            ("Pembe/Kırmızı Deterjan Boyası",0.015)
        ]
    },
    "pH Nötr Premium Oto Şampuanı": {
        "code":"KC-PHN-SOP-003","platform":"P1 Şampuan","ph":"6,8–7,2",
        "steps":[
            ("Deiyonize Su",82.25),("SLES %70",6.0),("CAPB",6.0),("APG",4.0),
            ("Sodyum Sitrat",0.3),("GLDA",0.2),("NaCl",1.0),("Koruyucu",0.1),("Parfüm",0.15)
        ]
    },
    "Cilalı Oto Yıkama Şampuanı": {
        "code":"KC-COS-SOP-003","platform":"P1 + P2","ph":"7,0–8,0",
        "steps":[
            ("Deiyonize Su",81.25),("SLES %70",8.0),("CAPB",5.0),("APG",2.0),
            ("%25 PDMS Emülsiyonu",1.5),("Noniyonik Wax Emülsiyonu",0.5),
            ("Sodyum Sitrat",0.3),("GLDA",0.2),("NaCl",1.0),("Koruyucu",0.1),("Parfüm",0.15)
        ]
    },
    "Islak Cila / Wet Surface": {
        "code":"KC-RWX-SOP-004","platform":"P6 Wet Surface","ph":"6,5–7,5",
        "steps":[
            ("Deiyonize Su",95.095),("%25 PDMS Silikon Emülsiyonu",4.0),("DPM",0.5),
            ("APG",0.2),("Koruyucu",0.1),("Parfüm",0.1),("Mavi/Turkuaz Boya",0.005)
        ]
    },
    "Deri Koltuk Temizleyici": {
        "code":"KC-DKT-SOP-003","platform":"P4 İç Temizlik","ph":"6,5–7,2",
        "steps":[
            ("Deiyonize Su",97.35),("APG",1.0),("CAPB",0.5),("DPM",0.5),
            ("Sodyum Sitrat",0.3),("GLDA",0.2),("Koruyucu",0.1),("Parfüm",0.05)
        ]
    },
    "Kumaş / Döşeme Temizleyici": {
        "code":"KC-KDT-SOP-003","platform":"P4 İç Temizlik","ph":"8,0–9,0",
        "steps":[
            ("Deiyonize Su",94.5),("Düşük Köpüklü Noniyonik",1.5),("APG",1.5),("DPM",1.5),
            ("Sodyum Sitrat",0.5),("GLDA",0.3),("Koruyucu",0.1),("Parfüm",0.1)
        ]
    },
    "Jant & Motor Temizleyici": {
        "code":"KC-JMT-SOP-003","platform":"P5 Ağır Temizlik","ph":"11–12",
        "steps":[
            ("Deiyonize Su",87.2),("Yağ Çözücü Noniyonik",3.0),("APG",2.0),
            ("Sodyum Metasilikat Pentahidrat",2.0),("Sodyum Karbonat",2.0),
            ("Sodyum Sitrat",1.0),("GLDA",0.5),("SXS / Hidrotrop",2.0),("Koruyucu",0.1),("Parfüm",0.2)
        ]
    },
    "Tır / Kamyon Ağır Kir Ön Yıkama Köpüğü": {
        "code":"KC-TKF-SOP-003","platform":"P5 Ağır Temizlik","ph":"11,5–12",
        "steps":[
            ("Deiyonize Su",80.2),("SLES %70",6.0),("APG",3.0),("Yağ Çözücü Noniyonik",3.0),
            ("SXS / Hidrotrop",2.0),("Sodyum Metasilikat Pentahidrat",2.0),("Sodyum Karbonat",2.0),
            ("Sodyum Sitrat",1.0),("GLDA",0.5),("Koruyucu",0.1),("Parfüm",0.2)
        ]
    },
    "Demir Tozu Sökücü / Iron Remover": {
        "code":"KC-IRS-SOP-003","platform":"P7 Iron","ph":"6,5–7,5",
        "steps":[
            ("Deiyonize Su",78.9),("Amonyum Tiyoglikolat %60",15.0),("CAPB",2.0),("APG",1.0),
            ("DPM",2.0),("GLDA",0.5),("Koruyucu",0.1),("Koku Maskeleme",0.5)
        ]
    },
    "Cam Temizleyici": {
        "code":"KC-CTM-SOP-003","platform":"P8 Özel","ph":"Pilot",
        "steps":[
            ("Deiyonize Su",92.4),("İzopropil Alkol (IPA)",5.0),("DPM",2.0),
            ("Düşük Köpüklü Noniyonik",0.3),("GLDA",0.2),("Koruyucu",0.1)
        ]
    },
    "Quick Detailer / Hızlı Parlatıcı": {
        "code":"KC-QDT-SOP-003","platform":"P2 Silikon Bakım","ph":"6,5–7,5",
        "steps":[
            ("Deiyonize Su",95.0),("%25 PDMS Silikon Emülsiyonu",3.5),("DPM",1.0),
            ("APG",0.2),("GLDA",0.1),("Koruyucu",0.1),("Parfüm",0.1)
        ]
    },
    "Dış Plastik / Trim Yenileyici": {
        "code":"KC-DTR-SOP-003","platform":"P2 Silikon Bakım","ph":"6,5–7,5",
        "steps":[
            ("Deiyonize Su",91.5),("%25 PDMS Silikon Emülsiyonu",6.0),
            ("Amino Silikon Emülsiyonu",0.8),("DPM",1.0),("APG",0.5),("Koruyucu",0.1),("Parfüm",0.1)
        ]
    },
    "Asitli Jant Temizleyici - Fosforik Bazlı": {
        "code":"KC-AJT-SOP-003","platform":"P8 Özel","ph":"Asidik",
        "steps":[
            ("Deiyonize Su",92.5),("Fosforik Asit %85",3.0),("Düşük Köpüklü Noniyonik",1.5),
            ("DPM",1.0),("SXS / Hidrotrop",1.0),("GLDA",0.3),
            ("Asit Uyumlu Korozyon İnhibitörü",0.5),("Koruyucu",0.1),("Parfüm",0.1)
        ]
    },
    "Zift / Katran Sökücü": {
        "code":"KC-ZKS-SOP-003","platform":"P8 Özel","ph":"Pilot",
        "steps":[
            ("Deiyonize Su",81.9),("D-Limonene",8.0),("DPM",6.0),("Noniyonik Emülgatör",3.0),
            ("SXS / Hidrotrop",1.0),("Koruyucu",0.1)
        ]
    },
    "Oto Parfümü - Water Based Spray": {
        "code":"KC-APF-SOP-004","platform":"P9 Koku","ph":"Pilot",
        "steps":[
            ("Deiyonize Su",82.49),("Etanol %96",10.0),("Oto Parfüm Esansı",3.0),
            ("PEG-40 Hydrogenated Castor Oil",4.0),("DPM",0.3),("Koruyucu",0.2),("Boya",0.01)
        ]
    },
}


# -----------------------------
# R04 PRODUCT-SPECIFIC PROCESS MASTER
# Source: KayaCar_Kimyasal_R04_DUZELTILMIS.pdf
# "source_text" preserves the controlled R04 wording.
# Numeric rpm/min values below are separately marked as PILOT recommendations
# unless R04 itself gives a time range.
# -----------------------------
PRODUCT_SOPS = {
    "Lastik Parlatıcı Jel": [
        {"title":"Su Fazı","source_text":"Suyun %85-90'ını ana kaba al.","materials":["Deiyonize Su"]},
        {"title":"Carbomer","source_text":"Yavaş serp; 20-30 dk hidratasyona bırak.","materials":["Carbomer 940"],"source_time":"20–30 dk","pilot_min":20,"pilot_rpm":"250–350"},
        {"title":"Jel Aktivasyonu","source_text":"TEA'yı seyrelterek küçük porsiyonlarda ekle; pH 6,5-7,5.","materials":[],"source_time":None,"pilot_min":0,"pilot_rpm":"Düşük devir"},
        {"title":"Yağ Fazı","source_text":"Polybutene + silikon yağı + DPM'yi ayrı kapta ön karıştır.","materials":["Polybutene Ham","Silikon Yağı 350 cSt","DPM"],"vessel":"AYRI ÖN KARIŞIM KABI","pilot_min":3,"pilot_rpm":"300–500"},
        {"title":"Emülsifikasyon","source_text":"Yağ fazını noniyonik emülgatör eşliğinde ince akışla ekle.","materials":["Noniyonik Emülgatör"],"pilot_min":5,"pilot_rpm":"400–700"},
        {"title":"Sonlandırma","source_text":"Islatıcı, koruyucu, boya/parfüm; su ile tamamla; 12-24 saat dinlendir.","materials":["Islatıcı","Koruyucu","Parfüm + Boya"],"source_time":"12–24 saat dinlendirme","pilot_min":2,"pilot_rpm":"200–300"},
    ],
    "Sıvı Lastik Parlatıcı": [
        {"title":"Su Fazı","source_text":"Suyun %85-90'ını kaba al; emülgatörü ekle.","materials":["Deiyonize Su","Noniyonik Emülgatör"],"pilot_min":2,"pilot_rpm":"300–450"},
        {"title":"Yağ Fazı","source_text":"Polybutene + silikon yağı + DPM ön karışımı hazırla.","materials":["Polybutene Ham","Silikon Yağı 350 cSt","DPM"],"vessel":"AYRI ÖN KARIŞIM KABI","pilot_min":3,"pilot_rpm":"300–500"},
        {"title":"Emülsifikasyon","source_text":"Yağ fazını yavaşça ana faza ver.","materials":[],"pilot_min":5,"pilot_rpm":"400–700"},
        {"title":"Yardımcılar","source_text":"Islatıcı, koruyucu, boya/parfüm.","materials":["Islatıcı","Koruyucu","Parfüm + Boya"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"Dinlendirme","source_text":"24 saat faz ayrımı kontrolü.","materials":[],"source_time":"24 saat","pilot_min":0,"pilot_rpm":"Karıştırma yok"},
    ],
    "Torpido Temizleme & Bakım Sütü": [
        {"title":"Su Fazı","source_text":"GLDA ve sitratı suda çöz.","materials":["Deiyonize Su","GLDA","Sodyum Sitrat"],"pilot_min":3,"pilot_rpm":"350–500"},
        {"title":"Temizleme","source_text":"APG ve CAPB'yi düşük devirde ekle.","materials":["APG","CAPB"],"pilot_min":3,"pilot_rpm":"Düşük devir / 250–350 pilot"},
        {"title":"Bakım","source_text":"PDMS emülsiyonunu yavaş ekle.","materials":["%25 PDMS Silikon Emülsiyonu"],"pilot_min":3,"pilot_rpm":"Düşük devir / 250–350 pilot"},
        {"title":"Sonlandırma","source_text":"DPM, koruyucu, parfüm.","materials":["DPM","Koruyucu","Parfüm"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"pH","source_text":"Sitrik asitle 7,0-7,5; su ile tamamla.","materials":[],"pilot_min":0,"pilot_rpm":"Düşük devir"},
    ],
    "Normal Oto Yıkama Şampuanı": [
        {"title":"Su Fazı","source_text":"Suyun %80-85'ine sitrat ve GLDA'yı çöz.","materials":["Deiyonize Su","Sodyum Sitrat","GLDA"],"pilot_min":3,"pilot_rpm":"350–500"},
        {"title":"Surfaktanlar","source_text":"SLES, CAPB, APG'yi düşük devirde sırayla ekle.","materials":["SLES %70","CAPB","APG"],"pilot_min":3,"pilot_rpm":"Düşük devir / 200–350 pilot"},
        {"title":"Yardımcılar","source_text":"Koruyucu, parfüm ve boya.","materials":["Koruyucu","Parfüm","Boya"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"Kıvam","source_text":"NaCl'yi kademeli ekle.","materials":["NaCl"],"pilot_min":3,"pilot_rpm":"200–300"},
        {"title":"Son","source_text":"pH 7,5-8,5; suyla tamamla.","materials":[],"pilot_min":0,"pilot_rpm":"Düşük devir"},
    ],
    "Pembe Oto Yıkama Şampuanı": [
        {"title":"Baz","source_text":"Normal şampuan sırasını uygula.","materials":["Deiyonize Su","Sodyum Sitrat","GLDA","SLES %70","CAPB","APG","Koruyucu","Parfüm","NaCl"],"pilot_min":0,"pilot_rpm":"Normal şampuan SOP"},
        {"title":"Boya Ön Çözeltisi","source_text":"Boyayı az deiyonize suda çöz.","materials":["Pembe/Kırmızı Deterjan Boyası"],"vessel":"AYRI KÜÇÜK KAP","pilot_min":1,"pilot_rpm":"Elle / düşük devir"},
        {"title":"Renklendirme","source_text":"Damla damla hedef tona getir.","materials":[],"pilot_min":1,"pilot_rpm":"200–300"},
        {"title":"Uyumluluk","source_text":"Beyaz boya, PPF ve mat plastik leke testi.","materials":[],"pilot_min":0,"pilot_rpm":"Test"},
    ],
    "pH Nötr Premium Oto Şampuanı": [
        {"title":"Su Fazı","source_text":"Sitrat ve GLDA'yı çöz.","materials":["Deiyonize Su","Sodyum Sitrat","GLDA"],"pilot_min":3,"pilot_rpm":"350–500"},
        {"title":"Surfaktanlar","source_text":"SLES, CAPB, APG'yi düşük devirde ekle.","materials":["SLES %70","CAPB","APG"],"pilot_min":3,"pilot_rpm":"Düşük devir / 200–350 pilot"},
        {"title":"Kıvam","source_text":"NaCl'yi kademeli ekle.","materials":["NaCl"],"pilot_min":3,"pilot_rpm":"200–300"},
        {"title":"pH","source_text":"Sitrik asitle 6,8-7,2.","materials":[],"pilot_min":0,"pilot_rpm":"Düşük devir"},
        {"title":"Son","source_text":"Koruyucu/parfüm; su ile tamamla.","materials":["Koruyucu","Parfüm"],"pilot_min":2,"pilot_rpm":"200–300"},
    ],
    "Cilalı Oto Yıkama Şampuanı": [
        {"title":"Şampuan Bazı","source_text":"SLES + CAPB + APG bazını hazırla.","materials":["Deiyonize Su","Sodyum Sitrat","GLDA","SLES %70","CAPB","APG"],"pilot_min":3,"pilot_rpm":"200–350"},
        {"title":"Bakım Fazı","source_text":"PDMS + wax emülsiyonunu düşük devirde ön karıştır.","materials":["%25 PDMS Emülsiyonu","Noniyonik Wax Emülsiyonu"],"vessel":"AYRI ÖN KARIŞIM KABI","pilot_min":3,"pilot_rpm":"Düşük devir / 250–350 pilot"},
        {"title":"Birleştirme","source_text":"Bakım fazını yavaş ekle.","materials":[],"pilot_min":4,"pilot_rpm":"250–400"},
        {"title":"Kıvam/pH","source_text":"NaCl; pH 7,0-8,0.","materials":["NaCl"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"Stabilite","source_text":"24 saat faz ayrımı/köpük kontrolü.","materials":["Koruyucu","Parfüm"],"source_time":"24 saat","pilot_min":1,"pilot_rpm":"200–300"},
    ],
    "Islak Cila / Wet Surface": [
        {"title":"Su Fazı","source_text":"Suyun yaklaşık %90'ını kaba al.","materials":["Deiyonize Su"],"pilot_min":1,"pilot_rpm":"250–350"},
        {"title":"APG","source_text":"Düşük devirde ekle; köpüğü minimumda tut.","materials":["APG"],"pilot_min":2,"pilot_rpm":"Düşük devir / 200–300 pilot"},
        {"title":"DPM","source_text":"Ekle ve homojenleştir.","materials":["DPM"],"pilot_min":2,"pilot_rpm":"250–350"},
        {"title":"PDMS","source_text":"%25 emülsiyonu yavaşça ekle; aşırı yüksek kesme uygulama.","materials":["%25 PDMS Silikon Emülsiyonu"],"pilot_min":3,"pilot_rpm":"Düşük devir / 200–300 pilot"},
        {"title":"Sonlandırma","source_text":"Koruyucu, parfüm, boya; su ile tamamla.","materials":["Koruyucu","Parfüm","Mavi/Turkuaz Boya"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"Dinlendirme","source_text":"12-24 saat; faz ayrımı, köpük ve suyla karışma testi.","materials":[],"source_time":"12–24 saat","pilot_min":0,"pilot_rpm":"Karıştırma yok"},
    ],
    "Deri Koltuk Temizleyici": [
        {"title":"Su Fazı","source_text":"Sitrat ve GLDA'yı çöz.","materials":["Deiyonize Su","Sodyum Sitrat","GLDA"],"pilot_min":3,"pilot_rpm":"350–500"},
        {"title":"Surfaktanlar","source_text":"APG ve CAPB düşük devir.","materials":["APG","CAPB"],"pilot_min":3,"pilot_rpm":"Düşük devir / 200–350 pilot"},
        {"title":"DPM","source_text":"Düşük doz ekle.","materials":["DPM"],"pilot_min":2,"pilot_rpm":"250–350"},
        {"title":"Son","source_text":"Koruyucu/parfüm; pH 6,5-7,2.","materials":["Koruyucu","Parfüm"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"Ön Test","source_text":"Görünmeyen alanda renk/finish kontrolü.","materials":[],"pilot_min":0,"pilot_rpm":"Test"},
    ],
    "Kumaş / Döşeme Temizleyici": [
        {"title":"Su Fazı","source_text":"Sitrat ve GLDA'yı çöz.","materials":["Deiyonize Su","Sodyum Sitrat","GLDA"],"pilot_min":3,"pilot_rpm":"350–500"},
        {"title":"Surfaktanlar","source_text":"Noniyonik ve APG düşük devir.","materials":["Düşük Köpüklü Noniyonik","APG"],"pilot_min":3,"pilot_rpm":"Düşük devir / 200–350 pilot"},
        {"title":"DPM","source_text":"Ekle ve homojenleştir.","materials":["DPM"],"pilot_min":2,"pilot_rpm":"250–350"},
        {"title":"Son","source_text":"Koruyucu/parfüm; pH 8,0-9,0.","materials":["Koruyucu","Parfüm"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"Test","source_text":"Renk atması ve sertlik kontrolü.","materials":[],"pilot_min":0,"pilot_rpm":"Test"},
    ],
    "Jant & Motor Temizleyici": [
        {"title":"Su Fazı","source_text":"Sitrat, karbonat ve GLDA'yı çöz.","materials":["Deiyonize Su","Sodyum Sitrat","Sodyum Karbonat","GLDA"],"pilot_min":4,"pilot_rpm":"350–550"},
        {"title":"Metasilikat","source_text":"Yavaş ekle; tozu/sıçramayı kontrol et.","materials":["Sodyum Metasilikat Pentahidrat"],"pilot_min":4,"pilot_rpm":"350–500"},
        {"title":"Surfaktanlar","source_text":"Noniyonik + APG.","materials":["Yağ Çözücü Noniyonik","APG"],"pilot_min":3,"pilot_rpm":"250–400"},
        {"title":"Hidrotrop","source_text":"SXS ekle.","materials":["SXS / Hidrotrop"],"pilot_min":2,"pilot_rpm":"300–450"},
        {"title":"Son","source_text":"pH yaklaşık 11-12; suyla tamamla.","materials":["Koruyucu","Parfüm"],"pilot_min":1,"pilot_rpm":"200–300"},
    ],
    "Tır / Kamyon Ağır Kir Ön Yıkama Köpüğü": [
        {"title":"Su Fazı","source_text":"Sitrat, karbonat, GLDA.","materials":["Deiyonize Su","Sodyum Sitrat","Sodyum Karbonat","GLDA"],"pilot_min":4,"pilot_rpm":"350–550"},
        {"title":"Metasilikat","source_text":"Yavaş ekle.","materials":["Sodyum Metasilikat Pentahidrat"],"pilot_min":4,"pilot_rpm":"350–500"},
        {"title":"Surfaktanlar","source_text":"SLES, APG, noniyonik.","materials":["SLES %70","APG","Yağ Çözücü Noniyonik"],"pilot_min":4,"pilot_rpm":"Düşük devir / 250–400 pilot"},
        {"title":"Hidrotrop","source_text":"SXS ekle.","materials":["SXS / Hidrotrop"],"pilot_min":2,"pilot_rpm":"300–450"},
        {"title":"Son","source_text":"pH ~11,5-12; seyreltmeyi panel testleriyle belirle.","materials":["Koruyucu","Parfüm"],"pilot_min":1,"pilot_rpm":"200–300"},
    ],
    "Demir Tozu Sökücü / Iron Remover": [
        {"title":"Su Fazı","source_text":"Suyun %80-85'ine GLDA'yı çöz.","materials":["Deiyonize Su","GLDA"],"pilot_min":3,"pilot_rpm":"350–500"},
        {"title":"Surfaktanlar","source_text":"CAPB ve APG düşük devir.","materials":["CAPB","APG"],"pilot_min":3,"pilot_rpm":"Düşük devir / 200–350 pilot"},
        {"title":"Aktif","source_text":"Amonyum tiyoglikolatı yavaş ekle; havalandırma.","materials":["Amonyum Tiyoglikolat %60"],"pilot_min":4,"pilot_rpm":"250–350"},
        {"title":"DPM","source_text":"Ekle.","materials":["DPM"],"pilot_min":2,"pilot_rpm":"250–350"},
        {"title":"pH","source_text":"6,5-7,5 doğrula.","materials":[],"pilot_min":0,"pilot_rpm":"Düşük devir"},
        {"title":"Son","source_text":"Koruyucu/koku; su ile tamamla.","materials":["Koruyucu","Koku Maskeleme"],"pilot_min":2,"pilot_rpm":"200–300"},
    ],
    "Cam Temizleyici": [
        {"title":"Su Fazı","source_text":"GLDA'yı çöz.","materials":["Deiyonize Su","GLDA"],"pilot_min":2,"pilot_rpm":"300–450"},
        {"title":"Solvent","source_text":"IPA + DPM.","materials":["İzopropil Alkol (IPA)","DPM"],"pilot_min":2,"pilot_rpm":"250–350"},
        {"title":"Surfaktan","source_text":"Düşük köpüklü noniyonik.","materials":["Düşük Köpüklü Noniyonik"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"Son","source_text":"Koruyucu; su ile tamamla; parfüm tercih edilmez.","materials":["Koruyucu"],"pilot_min":1,"pilot_rpm":"200–300"},
    ],
    "Quick Detailer / Hızlı Parlatıcı": [
        {"title":"Su Fazı","source_text":"GLDA'yı çöz.","materials":["Deiyonize Su","GLDA"],"pilot_min":2,"pilot_rpm":"300–450"},
        {"title":"PDMS","source_text":"Düşük devirde yavaş ekle.","materials":["%25 PDMS Silikon Emülsiyonu"],"pilot_min":3,"pilot_rpm":"Düşük devir / 200–300 pilot"},
        {"title":"Yardımcılar","source_text":"DPM + APG.","materials":["DPM","APG"],"pilot_min":2,"pilot_rpm":"250–350"},
        {"title":"Son","source_text":"Koruyucu/parfüm; pH 6,5-7,5.","materials":["Koruyucu","Parfüm"],"pilot_min":2,"pilot_rpm":"200–300"},
    ],
    "Dış Plastik / Trim Yenileyici": [
        {"title":"Su Fazı","source_text":"Suyu kaba al.","materials":["Deiyonize Su"],"pilot_min":1,"pilot_rpm":"250–350"},
        {"title":"Silikonlar","source_text":"PDMS ve amino silikonu düşük devirde ekle.","materials":["%25 PDMS Silikon Emülsiyonu","Amino Silikon Emülsiyonu"],"pilot_min":4,"pilot_rpm":"Düşük devir / 200–300 pilot"},
        {"title":"Yardımcılar","source_text":"DPM + APG + koruyucu + parfüm.","materials":["DPM","APG","Koruyucu","Parfüm"],"pilot_min":3,"pilot_rpm":"200–300"},
        {"title":"Son","source_text":"pH 6,5-7,5; 24 saat stabilite.","materials":[],"source_time":"24 saat","pilot_min":0,"pilot_rpm":"Karıştırma yok"},
    ],
    "Asitli Jant Temizleyici - Fosforik Bazlı": [
        {"title":"Su Fazı","source_text":"Suyun %85-90'ını kaba al.","materials":["Deiyonize Su"],"pilot_min":1,"pilot_rpm":"250–350"},
        {"title":"Asit","source_text":"Fosforik asidi yavaşça suya ekle.","materials":["Fosforik Asit %85"],"pilot_min":4,"pilot_rpm":"250–350"},
        {"title":"Yardımcılar","source_text":"Noniyonik, DPM, SXS, GLDA.","materials":["Düşük Köpüklü Noniyonik","DPM","SXS / Hidrotrop","GLDA"],"pilot_min":4,"pilot_rpm":"250–400"},
        {"title":"İnhibitör","source_text":"Tedarikçi dozuna göre ekle.","materials":["Asit Uyumlu Korozyon İnhibitörü"],"pilot_min":2,"pilot_rpm":"250–350"},
        {"title":"Son","source_text":"pH ve yüzey testini kaydet.","materials":["Koruyucu","Parfüm"],"pilot_min":1,"pilot_rpm":"200–300"},
    ],
    "Zift / Katran Sökücü": [
        {"title":"Solvent Fazı","source_text":"D-limonene + DPM + emülgatör ön karışımı.","materials":["D-Limonene","DPM","Noniyonik Emülgatör"],"vessel":"AYRI ÖN KARIŞIM KABI","pilot_min":4,"pilot_rpm":"300–500"},
        {"title":"Su Fazı","source_text":"Suyun %85-90'ına SXS'yi çöz.","materials":["Deiyonize Su","SXS / Hidrotrop"],"pilot_min":3,"pilot_rpm":"350–500"},
        {"title":"Birleştirme","source_text":"Solvent fazını yavaş ekle.","materials":[],"pilot_min":5,"pilot_rpm":"350–550"},
        {"title":"Son","source_text":"Koruyucu; 24 saat faz ayrımı.","materials":["Koruyucu"],"source_time":"24 saat","pilot_min":1,"pilot_rpm":"200–300"},
        {"title":"Uygulama","source_text":"Soğuk yüzey; kısa temas; PPF/boya ön testi.","materials":[],"pilot_min":0,"pilot_rpm":"Test"},
    ],
    "Oto Parfümü - Water Based Spray": [
        {"title":"Ön Karışım","source_text":"Esans + PEG-40 HCO + DPM ayrı kapta homojen/berrak ön karışım yapılır.","materials":["Oto Parfüm Esansı","PEG-40 Hydrogenated Castor Oil","DPM"],"vessel":"AYRI ÖN KARIŞIM KABI","pilot_min":3,"pilot_rpm":"300–450"},
        {"title":"Etanol","source_text":"Etanol ön karışıma yavaşça eklenir.","materials":["Etanol %96"],"vessel":"AYRI ÖN KARIŞIM KABI","pilot_min":2,"pilot_rpm":"250–350"},
        {"title":"Su Fazı","source_text":"Ana kaba deiyonize suyun yaklaşık %90'ı alınır.","materials":["Deiyonize Su"],"pilot_min":1,"pilot_rpm":"250–350"},
        {"title":"Birleştirme","source_text":"Koku konsantresi düşük devirde suya ince akışla verilir.","materials":[],"pilot_min":4,"pilot_rpm":"Düşük devir / 200–300 pilot"},
        {"title":"Sonlandırma","source_text":"Koruyucu ve isteğe bağlı ön çözündürülmüş boya eklenir; kalan suyla tamamlanır.","materials":["Koruyucu","Boya"],"pilot_min":2,"pilot_rpm":"200–300"},
        {"title":"Dinlendirme","source_text":"24-48 saat kapalı dinlendir; bulanıklık, yağ halkası, çökelme ve püskürtme testi.","materials":[],"source_time":"24–48 saat","pilot_min":0,"pilot_rpm":"Karıştırma yok"},
    ],
}

# Source-backed material dosing order. Formula percentages are unchanged; only the
# production sequence is reordered to follow the R04 procedure more closely.
DOSING_ORDER = {
    "Lastik Parlatıcı Jel":["Deiyonize Su","Carbomer 940","Polybutene Ham","Silikon Yağı 350 cSt","DPM","Noniyonik Emülgatör","Islatıcı","Koruyucu","Parfüm + Boya"],
    "Sıvı Lastik Parlatıcı":["Deiyonize Su","Noniyonik Emülgatör","Polybutene Ham","Silikon Yağı 350 cSt","DPM","Islatıcı","Koruyucu","Parfüm + Boya"],
    "Torpido Temizleme & Bakım Sütü":["Deiyonize Su","GLDA","Sodyum Sitrat","APG","CAPB","%25 PDMS Silikon Emülsiyonu","DPM","Koruyucu","Parfüm"],
    "Normal Oto Yıkama Şampuanı":["Deiyonize Su","Sodyum Sitrat","GLDA","SLES %70","CAPB","APG","Koruyucu","Parfüm","Boya","NaCl"],
    "Pembe Oto Yıkama Şampuanı":["Deiyonize Su","Sodyum Sitrat","GLDA","SLES %70","CAPB","APG","Koruyucu","Parfüm","NaCl","Pembe/Kırmızı Deterjan Boyası"],
    "pH Nötr Premium Oto Şampuanı":["Deiyonize Su","Sodyum Sitrat","GLDA","SLES %70","CAPB","APG","NaCl","Koruyucu","Parfüm"],
    "Cilalı Oto Yıkama Şampuanı":["Deiyonize Su","Sodyum Sitrat","GLDA","SLES %70","CAPB","APG","%25 PDMS Emülsiyonu","Noniyonik Wax Emülsiyonu","NaCl","Koruyucu","Parfüm"],
    "Islak Cila / Wet Surface":["Deiyonize Su","APG","DPM","%25 PDMS Silikon Emülsiyonu","Koruyucu","Parfüm","Mavi/Turkuaz Boya"],
    "Deri Koltuk Temizleyici":["Deiyonize Su","Sodyum Sitrat","GLDA","APG","CAPB","DPM","Koruyucu","Parfüm"],
    "Kumaş / Döşeme Temizleyici":["Deiyonize Su","Sodyum Sitrat","GLDA","Düşük Köpüklü Noniyonik","APG","DPM","Koruyucu","Parfüm"],
    "Jant & Motor Temizleyici":["Deiyonize Su","Sodyum Sitrat","Sodyum Karbonat","GLDA","Sodyum Metasilikat Pentahidrat","Yağ Çözücü Noniyonik","APG","SXS / Hidrotrop","Koruyucu","Parfüm"],
    "Tır / Kamyon Ağır Kir Ön Yıkama Köpüğü":["Deiyonize Su","Sodyum Sitrat","Sodyum Karbonat","GLDA","Sodyum Metasilikat Pentahidrat","SLES %70","APG","Yağ Çözücü Noniyonik","SXS / Hidrotrop","Koruyucu","Parfüm"],
    "Demir Tozu Sökücü / Iron Remover":["Deiyonize Su","GLDA","CAPB","APG","Amonyum Tiyoglikolat %60","DPM","Koruyucu","Koku Maskeleme"],
    "Cam Temizleyici":["Deiyonize Su","GLDA","İzopropil Alkol (IPA)","DPM","Düşük Köpüklü Noniyonik","Koruyucu"],
    "Quick Detailer / Hızlı Parlatıcı":["Deiyonize Su","GLDA","%25 PDMS Silikon Emülsiyonu","DPM","APG","Koruyucu","Parfüm"],
    "Dış Plastik / Trim Yenileyici":["Deiyonize Su","%25 PDMS Silikon Emülsiyonu","Amino Silikon Emülsiyonu","DPM","APG","Koruyucu","Parfüm"],
    "Asitli Jant Temizleyici - Fosforik Bazlı":["Deiyonize Su","Fosforik Asit %85","Düşük Köpüklü Noniyonik","DPM","SXS / Hidrotrop","GLDA","Asit Uyumlu Korozyon İnhibitörü","Koruyucu","Parfüm"],
    "Zift / Katran Sökücü":["D-Limonene","DPM","Noniyonik Emülgatör","Deiyonize Su","SXS / Hidrotrop","Koruyucu"],
    "Oto Parfümü - Water Based Spray":["Oto Parfüm Esansı","PEG-40 Hydrogenated Castor Oil","DPM","Etanol %96","Deiyonize Su","Koruyucu","Boya"],
}

def apply_r04_dosing_order():
    for pname, order in DOSING_ORDER.items():
        if pname not in PRODUCTS:
            continue
        original=dict(PRODUCTS[pname]["steps"])
        reordered=[]
        for m in order:
            if m in original:
                reordered.append((m,original[m]))
        # append anything accidentally omitted without changing formula
        used={m for m,_ in reordered}
        for m,pct in PRODUCTS[pname]["steps"]:
            if m not in used:
                reordered.append((m,pct))
        PRODUCTS[pname]["steps"]=reordered

apply_r04_dosing_order()

def sop_stage_for_material(product, material):
    stages=PRODUCT_SOPS.get(product,[])
    for idx,stage in enumerate(stages):
        if material in stage.get("materials",[]):
            return idx,stage
    return None, {"title":"Genel","source_text":"Bu hammadde için R04'te bağımsız dozaj satırı tanımlı değildir.",
                  "materials":[material],"pilot_min":0,"pilot_rpm":"SOP kontrolü"}

def product_sop_table(product):
    rows=[]
    for i,s in enumerate(PRODUCT_SOPS.get(product,[]),1):
        rows.append({
            "SOP Adımı":i,
            "Başlık":s["title"],
            "R04 Talimatı":s["source_text"],
            "Hammaddeler":", ".join(s.get("materials",[])) or "Proses / kontrol",
            "R04 Süre":s.get("source_time") or "Belirtilmemiş",
            "Pilot Başlangıç":("—" if not s.get("pilot_min") else f"{s['pilot_min']} dk / {s.get('pilot_rpm','')}"),
        })
    return pd.DataFrame(rows)

# -----------------------------
# DB
# -----------------------------
def db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con=db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS raw_materials(
      name TEXT PRIMARY KEY,
      stock_kg REAL NOT NULL DEFAULT 0,
      unit_cost_tl REAL NOT NULL DEFAULT 0,
      supplier TEXT DEFAULT '',
      active_pct REAL,
      note TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS tanks(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      material TEXT NOT NULL,
      tank_name TEXT NOT NULL,
      capacity_kg REAL NOT NULL DEFAULT 0,
      current_kg REAL NOT NULL DEFAULT 0,
      mode TEXT NOT NULL DEFAULT 'MANUEL',
      sensor_ref TEXT DEFAULT '',
      low_alarm_pct REAL NOT NULL DEFAULT 15
    );

    CREATE TABLE IF NOT EXISTS production_batches(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_no TEXT UNIQUE,
      product TEXT NOT NULL,
      target_kg REAL NOT NULL,
      created_at TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'DEVAM',
      current_step INTEGER NOT NULL DEFAULT 0,
      ph TEXT DEFAULT '',
      temp_c REAL,
      note TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS dosing_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_id INTEGER NOT NULL,
      step_index INTEGER NOT NULL,
      material TEXT NOT NULL,
      target_g REAL NOT NULL,
      actual_g REAL NOT NULL,
      tolerance_g REAL NOT NULL,
      source TEXT NOT NULL DEFAULT 'MANUEL',
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS batch_parameters(
      batch_no TEXT NOT NULL,
      key TEXT NOT NULL,
      value TEXT DEFAULT '',
      source TEXT DEFAULT '',
      approved_by TEXT DEFAULT '',
      updated_at TEXT NOT NULL,
      PRIMARY KEY(batch_no,key)
    );

    CREATE TABLE IF NOT EXISTS stage_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_no TEXT NOT NULL,
      stage_index INTEGER NOT NULL,
      stage_title TEXT NOT NULL,
      event TEXT NOT NULL,
      detail TEXT DEFAULT '',
      username TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS settings(
      key TEXT PRIMARY KEY,
      value TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS stock_movements(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      material TEXT NOT NULL,
      movement_type TEXT NOT NULL,
      qty_kg REAL NOT NULL,
      ref TEXT DEFAULT '',
      note TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS finished_goods(
      product TEXT PRIMARY KEY,
      stock_kg REAL NOT NULL DEFAULT 0,
      unit_cost_tl REAL NOT NULL DEFAULT 0,
      note TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS finished_goods_movements(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      product TEXT NOT NULL,
      movement_type TEXT NOT NULL,
      qty_kg REAL NOT NULL,
      batch_no TEXT DEFAULT '',
      note TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS users(
      username TEXT PRIMARY KEY,
      password TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'OPERATOR',
      active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS audit_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL,
      action TEXT NOT NULL,
      detail TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );
    """)
    all_mats=sorted({m for p in PRODUCTS.values() for m,_ in p["steps"]})
    for m in all_mats:
        con.execute("INSERT OR IGNORE INTO raw_materials(name) VALUES(?)",(m,))
    for pname in PRODUCTS.keys():
        con.execute("INSERT OR IGNORE INTO finished_goods(product) VALUES(?)",(pname,))
    defaults={
        "scale_mode":"MANUEL",
        "serial_port":"COM3",
        "baudrate":"9600",
        "tolerance_pct":"0.50",
        "min_tolerance_g":"1.0",
        "tare_command":"",
        "auto_beep":"1",
        "stable_window":"5",
        "stable_delta_g":"0.5",
        "yellow_zone_pct":"5.0",
        "red_over_pct":"0.5",
        "scale_read_command":"",
        "scale_line_ending":"\\r\\n"
    }
    for k,v in defaults.items():
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
    con.execute("INSERT OR IGNORE INTO users(username,password,role,active) VALUES('admin','1234','ADMIN',1)")
    con.execute("INSERT OR IGNORE INTO users(username,password,role,active) VALUES('operator','1234','OPERATOR',1)")
    # v0.6 migration: command-driven production state
    cols={r["name"] for r in con.execute("PRAGMA table_info(production_batches)").fetchall()}
    if "phase" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN phase TEXT NOT NULL DEFAULT 'TARE'")
    if "mix_started_at" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN mix_started_at TEXT DEFAULT ''")
    if "mix_end_at" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN mix_end_at TEXT DEFAULT ''")
    if "fg_received" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN fg_received INTEGER NOT NULL DEFAULT 0")
    if "stage_index" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN stage_index INTEGER NOT NULL DEFAULT 0")
    if "stage_material_index" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN stage_material_index INTEGER NOT NULL DEFAULT 0")
    if "engine_state" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN engine_state TEXT NOT NULL DEFAULT 'STAGE_INTRO'")
    if "stage_started_at" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN stage_started_at TEXT DEFAULT ''")
    if "hold_end_at" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN hold_end_at TEXT DEFAULT ''")
    if "engine_version" not in cols:
        con.execute("ALTER TABLE production_batches ADD COLUMN engine_version TEXT NOT NULL DEFAULT 'LEGACY'")
    sm_cols={r["name"] for r in con.execute("PRAGMA table_info(stock_movements)").fetchall()}
    if "tank_name" not in sm_cols:
        con.execute("ALTER TABLE stock_movements ADD COLUMN tank_name TEXT DEFAULT ''")
    dl_cols={r["name"] for r in con.execute("PRAGMA table_info(dosing_log)").fetchall()}
    if "stage_index" not in dl_cols:
        con.execute("ALTER TABLE dosing_log ADD COLUMN stage_index INTEGER")
    if "stage_material_index" not in dl_cols:
        con.execute("ALTER TABLE dosing_log ADD COLUMN stage_material_index INTEGER")
    if "vessel" not in dl_cols:
        con.execute("ALTER TABLE dosing_log ADD COLUMN vessel TEXT DEFAULT ''")
    # Existing in-progress batches with old dose logs should not silently continue under the new engine.
    con.execute("""UPDATE production_batches SET engine_version='LEGACY'
                   WHERE id IN (SELECT DISTINCT batch_id FROM dosing_log)
                     AND engine_version<>'v09'""")
    con.commit(); con.close()

def setting(key, default=""):
    con=db()
    row=con.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
    con.close()
    return row["value"] if row else default

def set_setting(key,value):
    con=db()
    con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))
    con.commit(); con.close()

# -----------------------------
# Scale abstraction
# -----------------------------
def parse_weight_to_g(text):
    """Generic parser: accepts '1234 g', '1.234 kg', 'ST,GS,+  001.250kg', etc."""
    if not text:
        return None
    s=text.strip().lower().replace(",",".")
    nums=re.findall(r"[-+]?\d+(?:\.\d+)?",s)
    if not nums:
        return None
    try:
        val=float(nums[-1])
    except:
        return None
    if "kg" in s:
        return val*1000.0
    if "mg" in s:
        return val/1000.0
    return val

def read_scale_once():
    mode=setting("scale_mode","MANUEL")
    if mode=="MANUEL":
        return None, "Manuel mod"
    if mode=="SIMULATOR":
        return float(st.session_state.get("sim_scale_g",0.0)), "SIMULATOR"
    if mode!="SERIAL":
        return None, f"Bilinmeyen mod: {mode}"
    if serial is None:
        return None, "pyserial kurulu değil"
    port=setting("serial_port","COM3")
    baud=int(setting("baudrate","9600"))
    read_cmd=setting("scale_read_command","")
    try:
        with serial.Serial(port,baudrate=baud,timeout=0.35) as ser:
            if read_cmd:
                payload=read_cmd.encode("utf-8").decode("unicode_escape").encode("latin1","ignore")
                ser.write(payload)
            raw=ser.readline().decode(errors="ignore").strip()
        g=parse_weight_to_g(raw)
        return g, raw or "Veri yok"
    except Exception as e:
        return None, str(e)

def weight_status(actual_g,target_g,tolerance_g):
    if actual_g is None:
        return "NO_DATA", "Veri yok"
    diff=actual_g-target_g
    yellow_pct=float(setting("yellow_zone_pct","5.0"))/100
    yellow=max(target_g*yellow_pct,tolerance_g*2)
    if abs(diff)<=tolerance_g:
        return "GREEN", f"UYGUN • {diff:+.2f} g"
    if actual_g>target_g+tolerance_g:
        return "RED", f"FAZLA • {diff:+.2f} g"
    if target_g-actual_g<=yellow:
        return "YELLOW", f"YAKLAŞIYOR • {target_g-actual_g:.2f} g kaldı"
    return "BLUE", f"EKSİK • {target_g-actual_g:.2f} g kaldı"

def stable_weight(new_g, key="scale_history"):
    if new_g is None:
        return False
    window=max(3,int(setting("stable_window","5")))
    delta=float(setting("stable_delta_g","0.5"))
    hist=st.session_state.get(key,[])
    hist=(hist+[float(new_g)])[-window:]
    st.session_state[key]=hist
    if len(hist)<window:
        return False
    return max(hist)-min(hist) <= delta

def scale_panel(actual,target,tolerance,stable=False):
    status,msg=weight_status(actual,target,tolerance)
    palette={
        "GREEN":("#075f35","#71f0aa"),
        "YELLOW":("#7b6000","#ffe27a"),
        "RED":("#7c1717","#ff8d8d"),
        "BLUE":("#0a3a5a","#7bd1ff"),
        "NO_DATA":("#29323a","#d5dde5"),
    }
    bg,fg=palette[status]
    val="—" if actual is None else f"{actual:,.2f} g"
    stab="STABİL" if stable else "HAREKETLİ"
    low=target-tolerance
    high=target+tolerance
    components.html(f"""
    <div style="box-sizing:border-box;width:100%;font-family:Segoe UI,Arial,sans-serif;
                background:{bg};color:white;border:2px solid {fg};border-radius:18px;
                padding:18px 20px;text-align:center;min-height:190px;overflow:hidden">
      <div style="font-size:17px;font-weight:700;letter-spacing:.3px">⚖ CANLI TERAZİ</div>
      <div style="font-size:56px;font-weight:900;line-height:1.05;margin:5px 0 7px">{val}</div>
      <div style="display:inline-block;padding:7px 18px;border-radius:999px;background:rgba(255,255,255,.12);
                  font-size:21px;font-weight:900;color:{fg}">{msg}</div>
      <div style="margin-top:13px;border-top:1px solid rgba(255,255,255,.25);padding-top:10px;
                  display:flex;justify-content:space-around;gap:8px;font-size:13px">
        <span><b>Hedef</b><br>{target:,.2f} g</span>
        <span><b>Kabul Aralığı</b><br>{low:,.2f} – {high:,.2f} g</span>
        <span><b>Durum</b><br>{stab}</span>
      </div>
    </div>
    """,height=205,scrolling=False)
    return status

# -----------------------------
# Business logic
# -----------------------------
def recipe_df(product,target_kg):
    return pd.DataFrame([
        {"Sıra":i+1,"Hammadde":m,"%":pct,"Hedef kg":target_kg*pct/100,"Hedef g":target_kg*pct*10}
        for i,(m,pct) in enumerate(PRODUCTS[product]["steps"])
    ])

def stock_df():
    con=db()
    d=pd.read_sql_query("SELECT * FROM raw_materials ORDER BY name",con)
    con.close()
    return d

def tanks_df():
    con=db()
    d=pd.read_sql_query("SELECT * FROM tanks ORDER BY tank_name",con)
    con.close()
    return d

def save_stock_editor(df):
    con=db()
    for _,r in df.iterrows():
        con.execute("""UPDATE raw_materials SET stock_kg=?,unit_cost_tl=?,supplier=?,active_pct=?,note=? WHERE name=?""",
                    (float(r["stock_kg"] or 0),float(r["unit_cost_tl"] or 0),str(r["supplier"] or ""),
                     None if pd.isna(r["active_pct"]) else float(r["active_pct"]),
                     str(r["note"] or ""),str(r["name"])))
    con.commit(); con.close()

def create_batch(product,target_kg,note=""):
    no="KC-"+datetime.now().strftime("%Y%m%d-%H%M%S")
    con=db()
    con.execute("""INSERT INTO production_batches(
                     batch_no,product,target_kg,created_at,status,current_step,note,
                     stage_index,stage_material_index,engine_state,engine_version)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (no,product,target_kg,datetime.now().isoformat(timespec="seconds"),"DEVAM",0,note,
                 0,0,"STAGE_INTRO","v09"))
    con.commit(); con.close()
    return no

def get_batch(batch_no):
    con=db()
    r=con.execute("SELECT * FROM production_batches WHERE batch_no=?",(batch_no,)).fetchone()
    con.close()
    return dict(r) if r else None

def open_batches():
    con=db()
    d=pd.read_sql_query("SELECT * FROM production_batches WHERE status='DEVAM' ORDER BY id DESC",con)
    con.close()
    return d

def all_batches():
    con=db()
    d=pd.read_sql_query("SELECT * FROM production_batches ORDER BY id DESC",con)
    con.close()
    return d

def material_stock(material):
    con=db()
    row=con.execute("SELECT stock_kg FROM raw_materials WHERE name=?",(material,)).fetchone()
    con.close()
    return float(row["stock_kg"]) if row else 0

def add_stock_movement(material,movement_type,qty_kg,ref="",note=""):
    con=db()
    con.execute("""INSERT INTO stock_movements(material,movement_type,qty_kg,ref,note,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (material,movement_type,float(qty_kg),ref,note,datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()

def deduct_stock(material,actual_g,ref=""):
    kg=actual_g/1000
    con=db()
    current=con.execute("SELECT stock_kg FROM raw_materials WHERE name=?",(material,)).fetchone()
    if not current:
        con.close()
        raise ValueError("Hammadde stok kartı bulunamadı")
    if float(current["stock_kg"])+1e-9 < kg:
        con.close()
        raise ValueError(f"Yetersiz stok. Mevcut: {float(current['stock_kg']):.3f} kg")
    con.execute("UPDATE raw_materials SET stock_kg=stock_kg-? WHERE name=?",(kg,material))
    tank=con.execute("""SELECT id,current_kg FROM tanks WHERE material=? AND current_kg>=?
                       ORDER BY current_kg DESC LIMIT 1""",(material,kg)).fetchone()
    used_tank=""
    if tank:
        con.execute("UPDATE tanks SET current_kg=current_kg-? WHERE id=?",(kg,tank["id"]))
        tr=con.execute("SELECT tank_name FROM tanks WHERE id=?",(tank["id"],)).fetchone()
        used_tank=tr["tank_name"] if tr else ""
    con.execute("""INSERT INTO stock_movements(material,movement_type,qty_kg,ref,note,created_at,tank_name)
                   VALUES(?,?,?,?,?,?,?)""",
                (material,"ÜRETİM ÇIKIŞ",-kg,ref,"Dozaj onayı",
                 datetime.now().isoformat(timespec="seconds"),used_tank))
    con.commit(); con.close()

def receive_stock(material,qty_kg,unit_cost=None,supplier="",lot="",note=""):
    con=db()
    current=con.execute("SELECT stock_kg,unit_cost_tl FROM raw_materials WHERE name=?",(material,)).fetchone()
    old_stock=float(current["stock_kg"] or 0)
    old_cost=float(current["unit_cost_tl"] or 0)
    new_stock=old_stock+float(qty_kg)
    if unit_cost is not None and float(unit_cost)>0:
        if new_stock>0:
            avg=((old_stock*old_cost)+(float(qty_kg)*float(unit_cost)))/new_stock
        else:
            avg=float(unit_cost)
        con.execute("UPDATE raw_materials SET stock_kg=?,unit_cost_tl=?,supplier=? WHERE name=?",
                    (new_stock,avg,supplier,material))
    else:
        con.execute("UPDATE raw_materials SET stock_kg=?,supplier=? WHERE name=?",
                    (new_stock,supplier,material))
    con.execute("""INSERT INTO stock_movements(material,movement_type,qty_kg,ref,note,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (material,"SATIN ALMA GİRİŞ",float(qty_kg),lot,note,datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()

def stock_movements_df():
    con=db()
    d=pd.read_sql_query("SELECT * FROM stock_movements ORDER BY id DESC",con)
    con.close()
    return d

def next_tank_name():
    con=db()
    rows=con.execute("SELECT tank_name FROM tanks").fetchall()
    con.close()
    nums=[]
    for r in rows:
        m=re.search(r"(\d+)$",str(r["tank_name"]))
        if m:
            nums.append(int(m.group(1)))
    return f"HMT-{(max(nums) if nums else 0)+1:03d}"

def tank_options_for_material(material):
    t=tanks_df()
    if t.empty:
        return []
    sub=t[t["material"]==material].copy()
    if sub.empty:
        return []
    sub["free_kg"]=sub["capacity_kg"]-sub["current_kg"]
    return sub.sort_values("free_kg",ascending=False).to_dict("records")

def add_or_fill_tank(material,qty_kg,tank_name=None,auto_create=True,default_capacity=25.0):
    qty=float(qty_kg)
    if qty<=0:
        return []
    con=db()
    allocations=[]

    def unique_name():
        names={r["tank_name"] for r in con.execute("SELECT tank_name FROM tanks").fetchall()}
        n=1
        while f"HMT-{n:03d}" in names:
            n+=1
        return f"HMT-{n:03d}"

    if tank_name:
        row=con.execute("SELECT * FROM tanks WHERE tank_name=?",(tank_name,)).fetchone()
        if not row:
            con.close(); raise ValueError("Seçilen tank bulunamadı.")
        if row["material"]!=material:
            con.close(); raise ValueError("Seçilen tank başka bir hammaddeye ait.")
        free=float(row["capacity_kg"])-float(row["current_kg"])
        add=min(qty,max(0,free))
        if add>0:
            con.execute("UPDATE tanks SET current_kg=current_kg+? WHERE id=?",(add,row["id"]))
            allocations.append((row["tank_name"],add)); qty-=add

    if qty>1e-9:
        rows=con.execute("""SELECT * FROM tanks WHERE material=? AND current_kg<capacity_kg
                            ORDER BY (capacity_kg-current_kg) DESC""",(material,)).fetchall()
        for row in rows:
            if tank_name and row["tank_name"]==tank_name:
                continue
            free=float(row["capacity_kg"])-float(row["current_kg"])
            add=min(qty,max(0,free))
            if add>0:
                con.execute("UPDATE tanks SET current_kg=current_kg+? WHERE id=?",(add,row["id"]))
                allocations.append((row["tank_name"],add)); qty-=add
            if qty<=1e-9:
                break

    while qty>1e-9 and auto_create:
        cap=float(default_capacity)
        name=unique_name()
        add=min(qty,cap)
        con.execute("""INSERT INTO tanks(material,tank_name,capacity_kg,current_kg,mode,low_alarm_pct)
                       VALUES(?,?,?,?,?,?)""",(material,name,cap,add,"MANUEL",15.0))
        allocations.append((name,add)); qty-=add

    if qty>1e-9:
        con.close()
        raise ValueError(f"Tank kapasitesi yetersiz. {qty:.3f} kg yerleştirilemedi.")

    con.commit(); con.close()
    return allocations

def receive_stock_to_tank(material,qty_kg,unit_cost=None,supplier="",lot="",note="",
                          tank_name=None,auto_create=True,default_capacity=25.0):
    con=db()
    current=con.execute("SELECT stock_kg,unit_cost_tl FROM raw_materials WHERE name=?",(material,)).fetchone()
    if not current:
        con.close(); raise ValueError("Hammadde kartı bulunamadı.")
    old_stock=float(current["stock_kg"] or 0); old_cost=float(current["unit_cost_tl"] or 0)
    qty=float(qty_kg); new_stock=old_stock+qty
    if unit_cost is not None and float(unit_cost)>0:
        avg=((old_stock*old_cost)+(qty*float(unit_cost)))/new_stock if new_stock>0 else float(unit_cost)
        con.execute("UPDATE raw_materials SET stock_kg=?,unit_cost_tl=?,supplier=? WHERE name=?",
                    (new_stock,avg,supplier,material))
    else:
        con.execute("UPDATE raw_materials SET stock_kg=?,supplier=? WHERE name=?",(new_stock,supplier,material))
    con.commit(); con.close()

    try:
        allocations=add_or_fill_tank(material,qty,tank_name,auto_create,default_capacity)
    except Exception:
        con=db(); con.execute("UPDATE raw_materials SET stock_kg=? WHERE name=?",(old_stock,material)); con.commit(); con.close()
        raise

    con=db()
    alloc_text=", ".join(f"{n}: {q:.3f} kg" for n,q in allocations)
    first_tank=allocations[0][0] if allocations else ""
    con.execute("""INSERT INTO stock_movements(material,movement_type,qty_kg,ref,note,created_at,tank_name)
                   VALUES(?,?,?,?,?,?,?)""",
                (material,"SATIN ALMA GİRİŞ",qty,lot,f"{note} | Tank dağılımı: {alloc_text}".strip(" |"),
                 datetime.now().isoformat(timespec="seconds"),first_tank))
    con.commit(); con.close()
    return allocations

def finished_goods_df():
    con=db(); d=pd.read_sql_query("SELECT * FROM finished_goods ORDER BY product",con); con.close(); return d

def finished_goods_movements_df():
    con=db(); d=pd.read_sql_query("SELECT * FROM finished_goods_movements ORDER BY id DESC",con); con.close(); return d

def wip_summary_df():
    con=db()
    d=pd.read_sql_query("""SELECT batch_no,product,target_kg,created_at,current_step,status
                           FROM production_batches WHERE status='DEVAM' ORDER BY id DESC""",con)
    con.close(); return d

def receive_finished_batch(batch_no,actual_output_kg,note=""):
    b=get_batch(batch_no)
    if not b: raise ValueError("Parti bulunamadı.")
    if b["status"]!="TAMAMLANDI": raise ValueError("Parti henüz tamamlanmadı.")
    if int(b.get("fg_received") or 0)==1: raise ValueError("Bu parti daha önce mamul stoğa alınmış.")
    qty=float(actual_output_kg)
    if qty<=0: raise ValueError("Mamul miktarı 0'dan büyük olmalı.")
    cost=batch_cost(batch_no); unit_cost=(cost/qty) if qty>0 else 0
    con=db()
    old=con.execute("SELECT stock_kg,unit_cost_tl FROM finished_goods WHERE product=?",(b["product"],)).fetchone()
    old_stock=float(old["stock_kg"] or 0); old_cost=float(old["unit_cost_tl"] or 0)
    new_stock=old_stock+qty
    avg=((old_stock*old_cost)+(qty*unit_cost))/new_stock if new_stock>0 else unit_cost
    con.execute("UPDATE finished_goods SET stock_kg=?,unit_cost_tl=? WHERE product=?",(new_stock,avg,b["product"]))
    con.execute("""INSERT INTO finished_goods_movements(product,movement_type,qty_kg,batch_no,note,created_at)
                   VALUES(?,?,?,?,?,?)""",(b["product"],"ÜRETİMDEN GİRİŞ",qty,batch_no,note,datetime.now().isoformat(timespec="seconds")))
    con.execute("UPDATE production_batches SET fg_received=1 WHERE batch_no=?",(batch_no,))
    con.commit(); con.close()

def issue_finished_goods(product,qty_kg,ref="",note=""):
    qty=float(qty_kg)
    con=db()
    row=con.execute("SELECT stock_kg FROM finished_goods WHERE product=?",(product,)).fetchone()
    if not row or float(row["stock_kg"])<qty:
        con.close(); raise ValueError("Yetersiz mamul stoğu.")
    con.execute("UPDATE finished_goods SET stock_kg=stock_kg-? WHERE product=?",(qty,product))
    con.execute("""INSERT INTO finished_goods_movements(product,movement_type,qty_kg,batch_no,note,created_at)
                   VALUES(?,?,?,?,?,?)""",(product,"SEVK / SATIŞ",-qty,ref,note,datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()

def confirm_dose(batch_no,actual_g,source):
    b=get_batch(batch_no)
    if not b:
        raise ValueError("Parti bulunamadı")
    steps=PRODUCTS[b["product"]]["steps"]
    idx=int(b["current_step"])
    if idx>=len(steps):
        raise ValueError("Parti tamamlanmış")
    material,pct=steps[idx]
    target_g=float(b["target_kg"])*pct*10
    tol_pct=float(setting("tolerance_pct","0.50"))/100
    min_tol=float(setting("min_tolerance_g","1.0"))
    tol=max(target_g*tol_pct,min_tol)
    deduct_stock(material,actual_g,ref=batch_no)
    con=db()
    bid=con.execute("SELECT id FROM production_batches WHERE batch_no=?",(batch_no,)).fetchone()["id"]
    con.execute("""INSERT INTO dosing_log(batch_id,step_index,material,target_g,actual_g,tolerance_g,source,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (bid,idx,material,target_g,actual_g,tol,source,datetime.now().isoformat(timespec="seconds")))
    next_idx=idx+1
    status="TAMAMLANDI" if next_idx>=len(steps) else "DEVAM"
    con.execute("UPDATE production_batches SET current_step=?,status=? WHERE batch_no=?",(next_idx,status,batch_no))
    con.commit(); con.close()
    return material,target_g,tol,status

def batch_log(batch_no):
    con=db()
    d=pd.read_sql_query("""SELECT dl.step_index+1 AS Sıra, dl.material AS Hammadde,
                           dl.target_g AS 'Hedef g', dl.actual_g AS 'Gerçek g',
                           dl.tolerance_g AS 'Tolerans g', dl.source AS Kaynak, dl.created_at AS Zaman
                           FROM dosing_log dl
                           JOIN production_batches b ON b.id=dl.batch_id
                           WHERE b.batch_no=? ORDER BY dl.step_index""",con,params=(batch_no,))
    con.close()
    return d


def send_tare():
    mode=setting("scale_mode","MANUEL")
    if mode=="SIMULATOR":
        st.session_state["sim_scale_g"]=0.0
        st.session_state["scale_history"]=[]
        st.session_state["op_scale_history"]=[]
        return True, "Simülatör sıfırlandı"
    if serial is None:
        return False, "pyserial kurulu değil"
    if mode!="SERIAL":
        return False, "Terazi SERIAL modunda değil"
    cmd=setting("tare_command","")
    if not cmd:
        return False, "TARE komutu tanımlı değil"
    try:
        port=setting("serial_port","COM3")
        baud=int(setting("baudrate","9600"))
        with serial.Serial(port,baudrate=baud,timeout=1) as ser:
            payload=cmd.encode("utf-8").decode("unicode_escape").encode("latin1","ignore")
            ser.write(payload)
        return True, "TARE komutu gönderildi"
    except Exception as e:
        return False, str(e)

def beep_component(kind="ok"):
    freq=880 if kind=="ok" else 420
    duration=220 if kind=="ok" else 420
    components.html(f"""
    <script>
    try {{
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = {freq};
      g.gain.setValueAtTime(0.12, ctx.currentTime);
      o.start();
      setTimeout(()=>{{o.stop();ctx.close();}}, {duration});
    }} catch(e) {{}}
    </script>
    """,height=0)

def qr_png_bytes(batch_no):
    if qrcode is None:
        return None
    b=get_batch(batch_no)
    payload={
        "batch_no":b["batch_no"],
        "product":b["product"],
        "target_kg":b["target_kg"],
        "created_at":b["created_at"],
        "status":b["status"]
    }
    img=qrcode.make(json.dumps(payload,ensure_ascii=False))
    bio=BytesIO()
    img.save(bio,format="PNG")
    return bio.getvalue()

def batch_label_text(batch_no):
    b=get_batch(batch_no)
    return f"""KayaCar Kimyasal
{b['product']}
Parti: {b['batch_no']}
Hedef: {b['target_kg']:.3f} kg
Tarih: {b['created_at']}
Durum: {b['status']}"""

def mixer_timer_widget(seconds, title="Karıştırma Zamanlayıcı"):
    seconds=max(1,int(seconds))
    components.html(f"""
    <div style="font-family:system-ui;background:#0b2234;color:white;border:1px solid #d8ab46;border-radius:10px;padding:14px">
      <div style="font-weight:700">{title}</div>
      <div id="t" style="font-size:34px;font-weight:800;margin:8px 0"></div>
      <button onclick="startT()">Başlat / Yeniden Başlat</button>
    </div>
    <script>
    let total={seconds}, left=total, timer=null;
    function fmt(s){{let m=Math.floor(s/60),r=s%60;return String(m).padStart(2,'0')+":"+String(r).padStart(2,'0')}}
    function render(){{document.getElementById('t').innerText=fmt(left)}}
    function startT(){{
      clearInterval(timer); left=total; render();
      timer=setInterval(()=>{{
        left--; render();
        if(left<=0){{
          clearInterval(timer);
          try {{
            const ctx=new (window.AudioContext||window.webkitAudioContext)();
            const o=ctx.createOscillator(); const g=ctx.createGain();
            o.connect(g);g.connect(ctx.destination);o.frequency.value=1000;o.start();
            setTimeout(()=>o.stop(),600);
          }} catch(e){{}}
        }}
      }},1000)
    }}
    render();
    </script>
    """,height=115)


def audit(username, action, detail=""):
    con=db()
    con.execute("""INSERT INTO audit_log(username,action,detail,created_at)
                   VALUES(?,?,?,?)""",
                (username,action,detail,datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()

def authenticate(username,password):
    con=db()
    row=con.execute("""SELECT username,role,active FROM users
                       WHERE username=? AND password=?""",(username,password)).fetchone()
    con.close()
    if row and int(row["active"])==1:
        return dict(row)
    return None

def audit_df():
    con=db()
    d=pd.read_sql_query("SELECT * FROM audit_log ORDER BY id DESC",con)
    con.close()
    return d

def users_df():
    con=db()
    d=pd.read_sql_query("SELECT username,role,active FROM users ORDER BY username",con)
    con.close()
    return d

def update_user(username,password=None,role=None,active=None):
    con=db()
    if password:
        con.execute("UPDATE users SET password=? WHERE username=?",(password,username))
    if role:
        con.execute("UPDATE users SET role=? WHERE username=?",(role,username))
    if active is not None:
        con.execute("UPDATE users SET active=? WHERE username=?",(1 if active else 0,username))
    con.commit(); con.close()

def add_user(username,password,role):
    con=db()
    con.execute("INSERT INTO users(username,password,role,active) VALUES(?,?,?,1)",(username,password,role))
    con.commit(); con.close()

def production_needed_stock(product,target_kg):
    plan=recipe_df(product,target_kg)
    stocks=stock_df()[["name","stock_kg"]]
    x=plan.merge(stocks,left_on="Hammadde",right_on="name",how="left")
    x["Yeterli"]=x["stock_kg"].fillna(0) >= x["Hedef kg"]
    return x

def low_stock_materials(threshold_kg=5):
    s=stock_df()
    return s[s["stock_kg"]<=threshold_kg].sort_values("stock_kg")

def batch_cost(batch_no):
    b=get_batch(batch_no)
    if not b:
        return 0.0
    con=db()
    log=pd.read_sql_query("""SELECT dl.material,dl.actual_g,rm.unit_cost_tl
                             FROM dosing_log dl
                             JOIN production_batches pb ON pb.id=dl.batch_id
                             LEFT JOIN raw_materials rm ON rm.name=dl.material
                             WHERE pb.batch_no=?""",con,params=(batch_no,))
    con.close()
    if log.empty:
        return 0.0
    return float(((log["actual_g"]/1000)*log["unit_cost_tl"].fillna(0)).sum())


def simulator_controls(key_prefix="sim"):
    if "sim_scale_g" not in st.session_state:
        st.session_state["sim_scale_g"]=0.0
    st.caption("🧪 Simülatör: gerçek terazi gelmeden üretim ekranını test etmek için.")
    c1,c2,c3,c4,c5=st.columns(5)
    if c1.button("+100 g",key=key_prefix+"_p100"):
        st.session_state["sim_scale_g"]+=100
        st.rerun()
    if c2.button("+10 g",key=key_prefix+"_p10"):
        st.session_state["sim_scale_g"]+=10
        st.rerun()
    if c3.button("+1 g",key=key_prefix+"_p1"):
        st.session_state["sim_scale_g"]+=1
        st.rerun()
    if c4.button("-1 g",key=key_prefix+"_m1"):
        st.session_state["sim_scale_g"]=max(0,st.session_state["sim_scale_g"]-1)
        st.rerun()
    if c5.button("SIFIRLA",key=key_prefix+"_zero"):
        st.session_state["sim_scale_g"]=0.0
        st.session_state["scale_history"]=[]
        st.session_state["op_scale_history"]=[]
        st.rerun()


# -----------------------------
# v0.6 Process Command Engine
# -----------------------------
def process_recommendation(material, product=""):
    stage_no, stage=sop_stage_for_material(product,material)
    return {
        "minutes": float(stage.get("pilot_min") or 0),
        "rpm": stage.get("pilot_rpm","SOP'ta belirtilmemiş"),
        "command": stage.get("source_text",""),
        "type": stage.get("title","GENEL"),
        "stage_no": None if stage_no is None else stage_no+1,
        "source_time": stage.get("source_time"),
        "vessel": stage.get("vessel","ANA KAZAN"),
    }

def tank_for_material(material):
    con=db()
    row=con.execute("""SELECT * FROM tanks WHERE material=? ORDER BY current_kg DESC LIMIT 1""",(material,)).fetchone()
    con.close()
    return dict(row) if row else None

def dose_done(batch_no, step_index):
    con=db()
    bid=con.execute("SELECT id FROM production_batches WHERE batch_no=?",(batch_no,)).fetchone()
    if not bid:
        con.close(); return False
    row=con.execute("SELECT 1 FROM dosing_log WHERE batch_id=? AND step_index=? LIMIT 1",(bid["id"],step_index)).fetchone()
    con.close()
    return bool(row)

def confirm_dose_v06(batch_no, actual_g, source):
    b=get_batch(batch_no)
    if not b: raise ValueError("Parti bulunamadı")
    idx=int(b["current_step"])
    steps=PRODUCTS[b["product"]]["steps"]
    if idx>=len(steps): raise ValueError("Parti tamamlanmış")
    if dose_done(batch_no,idx):
        raise ValueError("Bu adımın dozajı daha önce kaydedildi.")
    material,pct=steps[idx]
    target_g=float(b["target_kg"])*pct*10
    tol=max(target_g*(float(setting("tolerance_pct","0.50"))/100),float(setting("min_tolerance_g","1.0")))
    deduct_stock(material,actual_g,ref=batch_no)
    con=db()
    bid=con.execute("SELECT id FROM production_batches WHERE batch_no=?",(batch_no,)).fetchone()["id"]
    con.execute("""INSERT INTO dosing_log(batch_id,step_index,material,target_g,actual_g,tolerance_g,source,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (bid,idx,material,target_g,actual_g,tol,source,datetime.now().isoformat(timespec="seconds")))
    con.execute("""UPDATE production_batches SET phase='MIX',mix_started_at='',mix_end_at='' WHERE batch_no=?""",(batch_no,))
    con.commit(); con.close()
    return material,target_g,tol

def start_mix(batch_no, minutes):
    now=time.time()
    end=now+float(minutes)*60
    con=db()
    con.execute("""UPDATE production_batches SET phase='MIX',mix_started_at=?,mix_end_at=? WHERE batch_no=?""",
                (str(now),str(end),batch_no))
    con.commit(); con.close()
    return end

def remaining_mix_seconds(batch_no):
    b=get_batch(batch_no)
    try:
        end=float(b.get("mix_end_at") or 0)
    except:
        end=0
    return max(0,int(round(end-time.time()))), end

def finish_mix_and_advance(batch_no, force=False):
    b=get_batch(batch_no)
    if not b: raise ValueError("Parti bulunamadı")
    rem,_=remaining_mix_seconds(batch_no)
    if rem>0 and not force:
        raise ValueError(f"Önerilen karıştırma süresi henüz bitmedi: {rem} sn")
    idx=int(b["current_step"])+1
    total=len(PRODUCTS[b["product"]]["steps"])
    status="TAMAMLANDI" if idx>=total else "DEVAM"
    con=db()
    con.execute("""UPDATE production_batches SET current_step=?,status=?,phase='TARE',
                   mix_started_at='',mix_end_at='' WHERE batch_no=?""",(idx,status,batch_no))
    con.commit(); con.close()
    return status

def reset_step_phase(batch_no):
    con=db()
    con.execute("UPDATE production_batches SET phase='TARE',mix_started_at='',mix_end_at='' WHERE batch_no=?",(batch_no,))
    con.commit(); con.close()

def command_strip(phase):
    phases=["TARE","DOSE","MIX","NEXT"]
    labels=[("1","Kabı TARE / SIFIRLA"),("2","Hammaddeyi hedefe kadar ekle"),
            ("3","Önerilen süre/devirde karıştır"),("4","Sonraki hammaddeye geç")]
    cols=st.columns(4)
    current={"TARE":0,"DOSE":1,"MIX":2,"NEXT":3}.get(phase,0)
    for i,(n,txt) in enumerate(labels):
        icon="✅" if i<current else ("▶️" if i==current else "⏳")
        cols[i].markdown(f"**{icon} {n}. {txt}**")

def mix_countdown_html(seconds, minutes, rpm, command):
    seconds=max(0,int(seconds))
    components.html(f"""
    <div style="font-family:Segoe UI,Arial;background:#071b31;color:white;border:1px solid #2c5f8c;
                border-radius:16px;padding:16px;min-height:142px">
      <div style="font-size:15px;font-weight:800">🔄 KARIŞTIRMA KOMUTU</div>
      <div style="display:flex;gap:28px;align-items:end;margin:8px 0">
        <div><div style="font-size:12px;opacity:.75">Kalan süre</div>
             <div id="kc_timer" style="font-size:38px;font-weight:900">--:--</div></div>
        <div><div style="font-size:12px;opacity:.75">Tavsiye</div>
             <div style="font-size:20px;font-weight:800">{minutes:g} dk • {rpm} rpm</div></div>
      </div>
      <div style="font-size:13px;background:rgba(255,255,255,.07);padding:8px;border-radius:8px">{command}</div>
    </div>
    <script>
      let s={seconds};
      function f(x){{let m=Math.floor(x/60),r=x%60;return String(m).padStart(2,'0')+":"+String(r).padStart(2,'0')}}
      const el=document.getElementById('kc_timer');
      el.innerText=f(s);
      const t=setInterval(()=>{{s=Math.max(0,s-1);el.innerText=f(s);if(s<=0)clearInterval(t)}},1000);
    </script>
    """,height=160,scrolling=False)

def tank_card(r):
    cap=float(r["capacity_kg"] or 0); cur=float(r["current_kg"] or 0)
    pct=max(0,min(100,(cur/cap*100) if cap else 0))
    alarm=float(r["low_alarm_pct"] or 15)
    color="#dc3545" if pct<=5 else ("#e3a008" if pct<=alarm else "#159957")
    status="KRİTİK" if pct<=5 else ("DÜŞÜK" if pct<=alarm else "NORMAL")
    html=f"""
    <div style="font-family:Segoe UI,Arial;border:1px solid #d8e1eb;border-radius:14px;padding:12px;text-align:center;background:white">
      <div style="font-weight:900;font-size:16px;color:#0b2e59">{r['tank_name']}</div>
      <div style="height:150px;display:flex;align-items:flex-end;justify-content:center;margin:10px auto;width:92px;
                  border:3px solid #697785;border-radius:14px 14px 20px 20px;overflow:hidden;background:#eef2f5;position:relative">
        <div style="width:100%;height:{pct:.1f}%;background:{color};opacity:.85"></div>
        <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:22px;color:#10263e">
          %{pct:.0f}
        </div>
      </div>
      <div style="font-weight:800;color:{color}">{status}</div>
      <div style="font-size:13px;color:#425466">{cur:,.2f} / {cap:,.2f} kg</div>
      <div style="font-size:12px;margin-top:5px;color:#0b2e59">{r['material']}</div>
      <div style="font-size:11px;color:#6b7785">Alarm: %{alarm:g}</div>
    </div>
    """
    components.html(html,height=270,scrolling=False)



# ============================================================
# v0.9 PHASE-BASED BATCH ENGINE
# Research basis: ISA-88 procedural separation (procedure/operation/phase),
# adapted here for manual/pilot chemical batching.
# R04 controls WHAT/ORDER where explicitly stated.
# Numeric mixing RPM/time not present in R04 remains PILOT-only.
# ============================================================

WATER_RULES = {
    "Lastik Parlatıcı Jel":{"mode":"range","min":85.0,"max":90.0,"default":85.0,"final_qs":True,
        "basis":"R04: suyun %85-90'ı başta; sonlandırmada su ile tamamla."},
    "Sıvı Lastik Parlatıcı":{"mode":"range","min":85.0,"max":90.0,"default":85.0,"final_qs":False,
        "basis":"R04: suyun %85-90'ı başta; kalan suyun zamanı açık yazılmamış."},
    "Torpido Temizleme & Bakım Sütü":{"mode":"approved_split","default":85.0,"final_qs":True,
        "basis":"R04: GLDA/sitrat suda çöz; son pH adımında su ile tamamla. Başlangıç su yüzdesi belirtilmemiş."},
    "Normal Oto Yıkama Şampuanı":{"mode":"range","min":80.0,"max":85.0,"default":80.0,"final_qs":True,
        "basis":"R04: suyun %80-85'ine sitrat/GLDA; sonda suyla tamamla."},
    "Pembe Oto Yıkama Şampuanı":{"mode":"range","min":80.0,"max":85.0,"default":80.0,"final_qs":True,
        "basis":"R04: normal şampuan sırasını uygula; boya az DI suda ön çözülür."},
    "pH Nötr Premium Oto Şampuanı":{"mode":"approved_split","default":85.0,"final_qs":True,
        "basis":"R04: sitrat/GLDA çöz; sonda su ile tamamla. Başlangıç su yüzdesi belirtilmemiş."},
    "Cilalı Oto Yıkama Şampuanı":{"mode":"approved_full","default":100.0,"final_qs":False,
        "basis":"R04: 'şampuan bazı' deniyor; proses su bölüşümü açık yazılmamış. Tam su başlangıcı teknik onay gerektirir."},
    "Islak Cila / Wet Surface":{"mode":"fixed","default":90.0,"final_qs":True,
        "basis":"R04: suyun yaklaşık %90'ı başta; sonlandırmada su ile tamamla."},
    "Deri Koltuk Temizleyici":{"mode":"approved_full","default":100.0,"final_qs":False,
        "basis":"R04: sitrat/GLDA suda çöz; su bölüşümü belirtilmemiş."},
    "Kumaş / Döşeme Temizleyici":{"mode":"approved_full","default":100.0,"final_qs":False,
        "basis":"R04: sitrat/GLDA suda çöz; su bölüşümü belirtilmemiş."},
    "Jant & Motor Temizleyici":{"mode":"approved_split","default":85.0,"final_qs":True,
        "basis":"R04: su fazında builderlar çözülür; sonda suyla tamamla. Başlangıç yüzdesi belirtilmemiş."},
    "Tır / Kamyon Ağır Kir Ön Yıkama Köpüğü":{"mode":"approved_full","default":100.0,"final_qs":False,
        "basis":"R04: su fazı var; ayrı son su tamamlama adımı açık değil."},
    "Demir Tozu Sökücü / Iron Remover":{"mode":"range","min":80.0,"max":85.0,"default":80.0,"final_qs":True,
        "basis":"R04: suyun %80-85'ine GLDA; sonda su ile tamamla."},
    "Cam Temizleyici":{"mode":"approved_split","default":85.0,"final_qs":True,
        "basis":"R04: GLDA suda çöz; sonda su ile tamamla. Başlangıç yüzdesi belirtilmemiş."},
    "Quick Detailer / Hızlı Parlatıcı":{"mode":"approved_full","default":100.0,"final_qs":False,
        "basis":"R04: GLDA su fazı; ayrı son su tamamlama adımı açık değil."},
    "Dış Plastik / Trim Yenileyici":{"mode":"fixed","default":100.0,"final_qs":False,
        "basis":"R04: 'Suyu kaba al.'"},
    "Asitli Jant Temizleyici - Fosforik Bazlı":{"mode":"range","min":85.0,"max":90.0,"default":85.0,"final_qs":False,
        "basis":"R04: suyun %85-90'ı başta; kalan suyun zamanı açık yazılmamış."},
    "Zift / Katran Sökücü":{"mode":"range","min":85.0,"max":90.0,"default":85.0,"final_qs":False,
        "basis":"R04: su fazında suyun %85-90'ına SXS; kalan suyun zamanı açık yazılmamış."},
    "Oto Parfümü - Water Based Spray":{"mode":"fixed","default":90.0,"final_qs":True,
        "basis":"R04: ana kaba DI suyun yaklaşık %90'ı; kalan suyla ağırlık tamamlanır."},
}

# Some stage mappings are derived from the formula/platform because R04 uses a
# higher-level phrase rather than listing every base ingredient.
STAGE_MAPPING_BASIS = {
    ("Cilalı Oto Yıkama Şampuanı","Şampuan Bazı"):
        "KISMEN TÜRETİLMİŞ: R04 SLES+CAPB+APG bazını açıkça söyler; su/sitrat/GLDA yerleşimi P1 baz/formül kütle dengesinden türetilmiştir.",
    ("Pembe Oto Yıkama Şampuanı","Baz"):
        "KAYNAK BAĞLANTILI: R04 'Normal şampuan sırasını uygula' der; baz fazları normal şampuandan miras alınır.",
}

def batch_param_get(batch_no,key,default=None):
    con=db()
    row=con.execute("SELECT value FROM batch_parameters WHERE batch_no=? AND key=?",(batch_no,key)).fetchone()
    con.close()
    return row["value"] if row else default

def batch_param_set(batch_no,key,value,source="",approved_by=""):
    con=db()
    con.execute("""INSERT INTO batch_parameters(batch_no,key,value,source,approved_by,updated_at)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(batch_no,key) DO UPDATE SET
                     value=excluded.value, source=excluded.source,
                     approved_by=excluded.approved_by, updated_at=excluded.updated_at""",
                (batch_no,key,str(value),source,approved_by,datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()

def stage_event(batch_no,stage_index,stage_title,event,detail="",username=""):
    con=db()
    con.execute("""INSERT INTO stage_log(batch_no,stage_index,stage_title,event,detail,username,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (batch_no,int(stage_index),stage_title,event,detail,username,
                 datetime.now().isoformat(timespec="seconds")))
    con.commit(); con.close()

def formula_dict(product):
    return dict(PRODUCTS[product]["steps"])

def total_formula_g(product,target_kg,material):
    pct=formula_dict(product).get(material,0.0)
    return float(target_kg)*float(pct)*10.0

def classify_stage(stage):
    title=(stage.get("title") or "").lower()
    text=(stage.get("source_text") or "").lower()
    if any(x in title for x in ["dinlendirme","stabilite"]):
        return "HOLD"
    if any(x in title for x in ["ön test","uyumluluk","test","uygulama"]):
        return "QC"
    if any(x in title for x in ["ph","jel aktivasyonu"]):
        return "CONTROL"
    if any(x in title for x in ["birleştirme","emülsifikasyon"]):
        return "TRANSFER"
    return "DOSE"

def source_hold_seconds(stage):
    s=(stage.get("source_time") or "") + " " + (stage.get("source_text") or "")
    s=s.lower().replace(",",".")
    # For ranges, use the minimum source-backed hold before normal release.
    m=re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*saat",s)
    if m:
        return int(float(m.group(1))*3600)
    m=re.search(r"(\d+(?:\.\d+)?)\s*saat",s)
    if m:
        return int(float(m.group(1))*3600)
    m=re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*dk",s)
    if m:
        return int(float(m.group(1))*60)
    m=re.search(r"(\d+(?:\.\d+)?)\s*dk",s)
    if m:
        return int(float(m.group(1))*60)
    return 0

def phase_list(product):
    """Return source stages plus a transparent mass-balance stage if required."""
    phases=[]
    for s in PRODUCT_SOPS.get(product,[]):
        p=dict(s)
        p["kind"]=classify_stage(p)
        p["basis"]=STAGE_MAPPING_BASIS.get((product,p.get("title")),"R04 KONTROLLÜ SOP")
        phases.append(p)

    wr=WATER_RULES.get(product,{})
    # If R04 explicitly starts with partial water but never says where the remainder goes,
    # add a visible technical/mass-balance stage instead of silently inventing a step.
    if wr.get("mode") in ("range","fixed") and float(wr.get("default",100))<100 and not wr.get("final_qs"):
        phases.append({
            "title":"Formül Kütle Tamamlama",
            "source_text":"R04 başlangıçta suyun yalnız bir kısmını tarif ediyor; kalan suyun eklenme zamanı açık yazılmamış. Toplam reçete kütlesini kapatmak için teknik onaylı tamamlama adımı.",
            "materials":["Deiyonize Su"],
            "kind":"DOSE",
            "basis":"KÜTLE DENGESİ ÇIKARIMI — R04'te adım açık yazılmamış",
            "vessel":"ANA KAZAN",
            "pilot_min":0,
            "pilot_rpm":"Teknik onay",
            "mass_balance_water":True
        })
    return phases

def water_plan_pct(batch_no,product):
    v=batch_param_get(batch_no,"initial_water_pct")
    if v is not None:
        return float(v)
    return None

def water_remaining_g(batch_no,product,target_kg):
    total=total_formula_g(product,target_kg,"Deiyonize Su")
    con=db()
    row=con.execute("""SELECT COALESCE(SUM(dl.actual_g),0) AS s
                       FROM dosing_log dl
                       JOIN production_batches pb ON pb.id=dl.batch_id
                       WHERE pb.batch_no=? AND dl.material='Deiyonize Su'""",(batch_no,)).fetchone()
    con.close()
    used=float(row["s"] or 0)
    return max(0.0,total-used)

def phase_materials(product,stage,batch_no,target_kg):
    mats=list(stage.get("materials",[]))
    wr=WATER_RULES.get(product,{})
    title=stage.get("title","")
    text=(stage.get("source_text") or "").lower()

    # Explicit final q.s. water becomes a real dose at the final/son/pH stage.
    if wr.get("final_qs") and ("su ile tamamla" in text or "suyla tamamla" in text or "kalan suyla" in text):
        if "Deiyonize Su" not in mats:
            mats.append("Deiyonize Su")

    return mats

def phase_target_g(batch_no,product,target_kg,stage,material):
    if material!="Deiyonize Su":
        return total_formula_g(product,target_kg,material)

    total=total_formula_g(product,target_kg,"Deiyonize Su")
    wr=WATER_RULES.get(product,{"mode":"approved_full","default":100.0})
    text=(stage.get("source_text") or "").lower()

    if stage.get("mass_balance_water"):
        return water_remaining_g(batch_no,product,target_kg)

    # Final q.s. stage gets exactly the remaining formula water.
    if wr.get("final_qs") and ("su ile tamamla" in text or "suyla tamamla" in text or "kalan suyla" in text):
        return water_remaining_g(batch_no,product,target_kg)

    # Initial/process-water dose.
    pct=water_plan_pct(batch_no,product)
    if pct is None:
        return None
    return total*pct/100.0

def phase_material_dosed(batch_no,stage_index,material_index):
    con=db()
    row=con.execute("""SELECT 1 FROM dosing_log dl
                       JOIN production_batches pb ON pb.id=dl.batch_id
                       WHERE pb.batch_no=? AND dl.stage_index=? AND dl.stage_material_index=?
                       LIMIT 1""",(batch_no,int(stage_index),int(material_index))).fetchone()
    con.close()
    return bool(row)

def confirm_phase_dose(batch_no,stage_index,material_index,material,target_g,actual_g,source,vessel):
    b=get_batch(batch_no)
    if not b: raise ValueError("Parti bulunamadı.")
    if phase_material_dosed(batch_no,stage_index,material_index):
        raise ValueError("Bu faz hammaddesi daha önce kaydedildi.")
    tol=max(float(target_g)*(float(setting("tolerance_pct","0.50"))/100),
            float(setting("min_tolerance_g","1.0")))
    deduct_stock(material,actual_g,ref=batch_no)
    con=db()
    bid=con.execute("SELECT id FROM production_batches WHERE batch_no=?",(batch_no,)).fetchone()["id"]
    seq=con.execute("SELECT COUNT(*) AS c FROM dosing_log WHERE batch_id=?",(bid,)).fetchone()["c"]
    con.execute("""INSERT INTO dosing_log(
                     batch_id,step_index,material,target_g,actual_g,tolerance_g,source,created_at,
                     stage_index,stage_material_index,vessel)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (bid,int(seq),material,float(target_g),float(actual_g),float(tol),source,
                 datetime.now().isoformat(timespec="seconds"),int(stage_index),int(material_index),vessel))
    con.execute("""UPDATE production_batches SET stage_material_index=?,engine_state='STAGE_DOSING'
                   WHERE batch_no=?""",(int(material_index)+1,batch_no))
    con.commit(); con.close()
    return tol

def set_stage_state(batch_no,state,stage_index=None,material_index=None):
    con=db()
    fields=["engine_state=?"]; vals=[state]
    if stage_index is not None:
        fields.append("stage_index=?"); vals.append(int(stage_index))
    if material_index is not None:
        fields.append("stage_material_index=?"); vals.append(int(material_index))
    vals.append(batch_no)
    con.execute(f"UPDATE production_batches SET {','.join(fields)} WHERE batch_no=?",tuple(vals))
    con.commit(); con.close()

def start_stage_hold(batch_no,seconds):
    end=time.time()+int(seconds)
    con=db()
    con.execute("UPDATE production_batches SET engine_state='STAGE_HOLD',hold_end_at=? WHERE batch_no=?",
                (str(end),batch_no))
    con.commit(); con.close()
    return end

def stage_hold_remaining(batch_no):
    b=get_batch(batch_no)
    try: end=float(b.get("hold_end_at") or 0)
    except: end=0
    return max(0,int(round(end-time.time())))

def advance_stage(batch_no):
    b=get_batch(batch_no)
    product=b["product"]
    phases=phase_list(product)
    nxt=int(b.get("stage_index") or 0)+1
    if nxt>=len(phases):
        con=db()
        con.execute("""UPDATE production_batches
                       SET stage_index=?,stage_material_index=0,engine_state='COMPLETE',
                           status='TAMAMLANDI',hold_end_at=''
                       WHERE batch_no=?""",(nxt,batch_no))
        con.commit(); con.close()
        return "TAMAMLANDI"
    con=db()
    con.execute("""UPDATE production_batches
                   SET stage_index=?,stage_material_index=0,engine_state='STAGE_INTRO',
                       hold_end_at='',stage_started_at=?
                   WHERE batch_no=?""",
                (nxt,datetime.now().isoformat(timespec="seconds"),batch_no))
    con.commit(); con.close()
    return "DEVAM"

def ensure_v09_water_plan_ui(batch_no,product,operator):
    wr=WATER_RULES.get(product)
    if not wr:
        return True
    existing=water_plan_pct(batch_no,product)
    if existing is not None:
        return True

    st.warning("💧 Bu ürün için proses suyu planı henüz onaylanmamış. Hammadde toplam suyu ile proses başlangıç suyu aynı şey değildir.")
    st.caption(wr.get("basis",""))
    if operator:
        st.error("Operatör üretime devam edemez. Admin/teknik yetkili bu parti için başlangıç proses suyu setpointini onaylamalı.")
        return False

    mode=wr.get("mode")
    if mode=="range":
        val=st.slider("Başlangıçta kullanılacak reçete suyunun yüzdesi",
                      min_value=float(wr["min"]),max_value=float(wr["max"]),
                      value=float(wr["default"]),step=0.5,key=f"waterplan_{batch_no}")
    elif mode=="fixed":
        val=float(wr["default"])
        st.info(f"R04 yaklaşık/setpoint: **%{val:g}**")
    else:
        val=st.number_input("Teknik onaylı başlangıç su yüzdesi",
                            min_value=10.0,max_value=100.0,value=float(wr["default"]),step=1.0,
                            key=f"waterplan_{batch_no}")
        st.info("Bu yüzde R04'te sayısal verilmediği için teknik setpointtir; ürün pilotuyla revize edilebilir.")

    if st.button("✅ PROSES SUYU PLANINI ONAYLA",type="primary",key=f"savewater_{batch_no}"):
        batch_param_set(batch_no,"initial_water_pct",val,wr.get("basis",""),USER["username"])
        audit(USER["username"],"WATER_PLAN_APPROVE",f"{batch_no} | %{val}")
        st.rerun()
    return False

def stage_progress_strip(stage_idx,total):
    st.progress(min(stage_idx/max(total,1),1.0),text=f"Faz {stage_idx+1}/{total}")

def phase_card(stage,idx,total):
    kind=stage.get("kind",classify_stage(stage))
    vessel=stage.get("vessel","ANA KAZAN")
    basis=stage.get("basis","R04 KONTROLLÜ SOP")
    st.markdown(f"""
    <div style="background:#071b31;color:white;border:1px solid #d8ab46;border-radius:14px;padding:16px;margin:8px 0">
      <div style="font-size:13px;opacity:.8">FAZ {idx+1}/{total} • {kind} • {vessel}</div>
      <div style="font-size:24px;font-weight:900;margin-top:4px">{stage.get('title','FAZ')}</div>
      <div style="font-size:15px;margin-top:8px">{stage.get('source_text','')}</div>
      <div style="font-size:12px;margin-top:10px;color:#e7c35b">{basis}</div>
    </div>
    """,unsafe_allow_html=True)

def render_phase_engine(active,operator=False):
    b=get_batch(active)
    if b.get("engine_version")!="v09":
        st.error("Bu parti eski hammadde-bazlı motorla başlatılmış. v0.9 faz mimarisine sessizce dönüştürülmedi; izlenebilirlik için yeni parti başlat.")
        st.caption("Eski parti geçmişte kalır; yeni parti FAZ → DOZAJLAR → FAZ KARIŞTIRMA/KONTROL → SONRAKİ FAZ mantığıyla yürür.")
        return

    product=b["product"]; target=float(b["target_kg"]); phases=phase_list(product)
    sidx=int(b.get("stage_index") or 0)
    if sidx>=len(phases) or b["status"]=="TAMAMLANDI":
        st.success("🎉 Parti proses fazları tamamlandı. Mamul stoğa alma / QC serbest bırakma adımına geçilebilir.")
        return

    if not ensure_v09_water_plan_ui(active,product,operator):
        return

    stage=phases[sidx]
    stage["kind"]=stage.get("kind",classify_stage(stage))
    mats=phase_materials(product,stage,active,target)
    midx=int(b.get("stage_material_index") or 0)
    state=b.get("engine_state") or "STAGE_INTRO"

    st.markdown(f"**Parti:** {active}  |  **Ürün:** {product}  |  **Hedef:** {target:.3f} kg")
    with st.expander("📘 R04 / Faz Prosedürü",expanded=False):
        st.dataframe(product_sop_table(product),use_container_width=True,hide_index=True)
        st.caption("Kaynak prosedür ile kütle-dengesi/teknik çıkarımlar ayrı etiketlenir.")
    stage_progress_strip(sidx,len(phases))
    phase_card(stage,sidx,len(phases))

    # Stage introduction / equipment-vessel confirmation
    if state=="STAGE_INTRO":
        st.subheader("1️⃣ FAZI HAZIRLA")
        st.write(f"**Kap / ekipman:** {stage.get('vessel','ANA KAZAN')}")
        if stage.get("vessel","ANA KAZAN")!="ANA KAZAN":
            st.warning("Bu faz ana kazandan ayrı hazırlanır. Ayrı kap etiketi/temizliği doğrulanmadan dozaja geçme.")
        if st.button("✅ FAZ HAZIR — DEVAM",type="primary",use_container_width=True,key=f"stageintro_{active}_{sidx}"):
            next_state="STAGE_DOSING" if mats else "STAGE_GATE"
            set_stage_state(active,next_state,sidx,0)
            stage_event(active,sidx,stage["title"],"STAGE_START",stage.get("source_text",""),USER["username"])
            st.rerun()
        return

    # Dose all materials belonging to this phase, one by one. No mixing between every raw unless SOP says so.
    if state=="STAGE_DOSING" and mats:
        # Skip already logged materials on rerun.
        while midx<len(mats) and phase_material_dosed(active,sidx,midx):
            midx += 1
            set_stage_state(active,"STAGE_DOSING",sidx,midx)
        if midx>=len(mats):
            set_stage_state(active,"STAGE_GATE",sidx,midx)
            st.rerun()

        material=mats[midx]
        target_g=phase_target_g(active,product,target,stage,material)
        if target_g is None:
            st.error("Bu faz için proses suyu hedefi teknik olarak tanımlı değil.")
            return
        if target_g<=0.0001:
            st.info(f"{material}: bu fazda kalan hedef 0 g. Dozaj atlanıyor.")
            if st.button("ATLA / FAZDA DEVAM",key=f"skipzero_{active}_{sidx}_{midx}"):
                set_stage_state(active,"STAGE_DOSING",sidx,midx+1); st.rerun()
            return

        tol=max(target_g*(float(setting("tolerance_pct","0.50"))/100),float(setting("min_tolerance_g","1.0")))
        st.subheader(f"2️⃣ DOZAJ {midx+1}/{len(mats)} — {material}")
        c1,c2,c3=st.columns([1.0,1.35,1.0])
        with c1:
            st.metric("Hedef",f"{target_g:,.2f} g")
            st.metric("Kabul",f"{target_g-tol:,.2f}–{target_g+tol:,.2f} g")
            if material=="Deiyonize Su":
                st.caption(f"Toplam reçete suyu: {total_formula_g(product,target,'Deiyonize Su'):,.2f} g • Kalan: {water_remaining_g(active,product,target):,.2f} g")
            tank=tank_for_material(material)
            if tank: st.info(f"🛢️ {tank['tank_name']} • {tank['current_kg']:.2f}/{tank['capacity_kg']:.2f} kg")

        tare_key=f"v09_tare_{active}_{sidx}_{midx}"
        mode=setting("scale_mode","MANUEL")
        with c2:
            if not st.session_state.get(tare_key,False):
                st.markdown("#### TARE / SIFIRLA")
                if mode=="SERIAL":
                    if st.button("⚖️ TARE KOMUTU",key=f"v09tarecmd_{active}_{sidx}_{midx}",use_container_width=True):
                        ok_t,msg_t=send_tare(); (st.success if ok_t else st.warning)(msg_t)
                elif mode=="SIMULATOR":
                    if st.button("⚖️ SİMÜLATÖRÜ SIFIRLA",key=f"v09simtare_{active}_{sidx}_{midx}",use_container_width=True):
                        send_tare(); st.rerun()
                else:
                    st.info("Gerçek terazide TARE/ZERO tuşuna bas.")
                if st.button("✅ 0,00 g — TARTIMA GEÇ",type="primary",key=f"v09tareok_{active}_{sidx}_{midx}",use_container_width=True):
                    st.session_state[tare_key]=True; st.rerun()
                scale_panel(None,target_g,tol,False)
                return

            actual=0.0; stable=True; source=mode
            if mode=="SIMULATOR":
                simulator_controls(f"v09_{active}_{sidx}_{midx}")
                actual=float(st.session_state.get("sim_scale_g",0.0))
                stable=stable_weight(actual,f"v09hist_{active}_{sidx}_{midx}")
                scale_panel(actual,target_g,tol,stable)
            elif mode=="SERIAL":
                if st.button("🔄 TERAZİDEN OKU",key=f"v09read_{active}_{sidx}_{midx}",use_container_width=True):
                    g,raw=read_scale_once()
                    st.session_state[f"v09g_{active}_{sidx}_{midx}"]=g
                    st.session_state[f"v09raw_{active}_{sidx}_{midx}"]=raw
                g=st.session_state.get(f"v09g_{active}_{sidx}_{midx}")
                actual=float(g) if g is not None else 0.0
                stable=stable_weight(g,f"v09hist_{active}_{sidx}_{midx}") if g is not None else False
                scale_panel(g,target_g,tol,stable)
            else:
                actual=st.number_input("Terazide görünen gram",min_value=0.0,value=0.0,step=0.1,
                                       key=f"v09actual_{active}_{sidx}_{midx}")
                stable=True
                scale_panel(actual if actual>0 else None,target_g,tol,stable)

        diff=actual-target_g
        ok=actual>0 and abs(diff)<=tol and stable
        with c3:
            st.markdown("#### EKLE / ONAYLA")
            st.write(f"**Faz:** {stage['title']}")
            st.write(f"**Kap:** {stage.get('vessel','ANA KAZAN')}")
            if ok: st.success(f"✅ Uygun • {diff:+.2f} g")
            elif actual>0: st.error(f"⛔ Sapma • {diff:+.2f} g")
            override=False
            if not operator and actual>0 and not ok:
                override=st.checkbox("Yetkili tolerans dışı kabul",key=f"v09ovr_{active}_{sidx}_{midx}")
            if st.button("✅ DOZAJI KAYDET",type="primary",
                         disabled=not(actual>0 and (ok or override)),
                         key=f"v09dose_{active}_{sidx}_{midx}",use_container_width=True):
                try:
                    confirm_phase_dose(active,sidx,midx,material,target_g,actual,source,stage.get("vessel","ANA KAZAN"))
                    audit(USER["username"],"PHASE_DOSE",f"{active} | {stage['title']} | {material} | {actual} g")
                    st.session_state.pop(tare_key,None)
                    st.rerun()
                except Exception as e: st.error(str(e))
        return

    # If no materials or all materials completed, do ONE phase-level mix/control/transfer.
    if state in ("STAGE_DOSING","STAGE_GATE","STAGE_HOLD"):
        if state=="STAGE_DOSING":
            set_stage_state(active,"STAGE_GATE",sidx,len(mats)); st.rerun()

        kind=stage["kind"]
        st.subheader("3️⃣ FAZ KARIŞTIRMA / KONTROL / TRANSFER")

        # HOLD / source-backed wait
        hold_sec=source_hold_seconds(stage)
        if kind=="HOLD" or hold_sec>=3600:
            if state!="STAGE_HOLD":
                st.warning(f"Kaynak bekleme: {stage.get('source_time') or stage.get('source_text')}")
                if st.button("⏳ BEKLEMEYİ BAŞLAT",type="primary",use_container_width=True,key=f"holdstart_{active}_{sidx}"):
                    start_stage_hold(active,hold_sec if hold_sec else 3600)
                    stage_event(active,sidx,stage["title"],"HOLD_START",str(hold_sec),USER["username"])
                    st.rerun()
            else:
                rem=stage_hold_remaining(active)
                if rem>0:
                    hrs=rem//3600; mins=(rem%3600)//60
                    st.info(f"Bekleme devam ediyor: yaklaşık {hrs} sa {mins} dk")
                    if not operator:
                        reason=st.text_input("Yetkili erken geçiş gerekçesi",key=f"holdreason_{active}_{sidx}")
                        if st.button("⚠️ YETKİLİ OVERRIDE",disabled=not bool(reason.strip()),key=f"holdovr_{active}_{sidx}"):
                            stage_event(active,sidx,stage["title"],"HOLD_OVERRIDE",reason,USER["username"])
                            advance_stage(active); st.rerun()
                else:
                    st.success("✅ Kaynak bekleme süresi tamamlandı.")
                    if st.button("✅ BEKLEME TAMAM — SONRAKİ FAZ",type="primary",key=f"holddone_{active}_{sidx}"):
                        stage_event(active,sidx,stage["title"],"HOLD_COMPLETE","",USER["username"])
                        advance_stage(active); st.rerun()
            return

        # CONTROL/QC/TRANSFER: no fake tare/mix.
        if kind in ("CONTROL","QC","TRANSFER"):
            st.info(stage.get("source_text",""))
            if kind=="CONTROL" and ("ph" in stage.get("title","").lower() or "ph" in stage.get("source_text","").lower()):
                phv=st.text_input("Ölçülen pH / kontrol sonucu",key=f"phgate_{active}_{sidx}")
                if st.button("✅ KONTROLÜ ONAYLA — SONRAKİ FAZ",type="primary",
                             disabled=not bool(phv.strip()),key=f"ctrl_{active}_{sidx}"):
                    batch_param_set(active,f"stage_{sidx}_control",phv,stage.get("source_text",""),USER["username"])
                    stage_event(active,sidx,stage["title"],"CONTROL_COMPLETE",phv,USER["username"])
                    advance_stage(active); st.rerun()
            else:
                check=st.checkbox("Talimat uygulandı / kontrol edildi",key=f"stagecheck_{active}_{sidx}")
                if st.button("✅ FAZI ONAYLA — SONRAKİ FAZ",type="primary",
                             disabled=not check,key=f"stagegate_{active}_{sidx}"):
                    stage_event(active,sidx,stage["title"],"STAGE_COMPLETE",stage.get("source_text",""),USER["username"])
                    advance_stage(active); st.rerun()
            return

        # DOSE phase's ONE mixing gate after all raw materials are in.
        pilot_min=float(stage.get("pilot_min") or 0)
        rpm=stage.get("pilot_rpm","R04'te belirtilmemiş")
        st.write(f"**R04 talimatı:** {stage.get('source_text','')}")
        st.caption("Aşağıdaki sayısal süre/RPM yalnız R04'te açıkça verilmediyse pilot başlangıç parametresidir.")
        a,bcol=st.columns(2)
        a.metric("Pilot süre", "—" if pilot_min<=0 else f"{pilot_min:g} dk")
        bcol.metric("Pilot devir",rpm)

        if pilot_min>0:
            # Reuse existing mix timer fields only as a stage-level timer.
            rem,_=remaining_mix_seconds(active)
            if not b.get("mix_started_at"):
                if st.button("▶️ FAZ KARIŞTIRMAYI BAŞLAT",type="primary",key=f"v09mixstart_{active}_{sidx}",use_container_width=True):
                    start_mix(active,pilot_min)
                    stage_event(active,sidx,stage["title"],"MIX_START",f"{pilot_min} dk | {rpm}",USER["username"])
                    st.rerun()
            else:
                mix_countdown_html(rem,pilot_min,rpm,stage.get("source_text",""))
                if rem>0:
                    st.warning(f"Pilot karıştırma süresi devam ediyor: {rem} sn")
                else:
                    st.success("✅ Pilot faz karıştırma süresi tamamlandı.")
                if st.button("✅ FAZ TAMAM — SONRAKİ FAZ",type="primary",
                             disabled=rem>0,key=f"v09mixdone_{active}_{sidx}",use_container_width=True):
                    # clear old timer and advance stage
                    con=db()
                    con.execute("UPDATE production_batches SET mix_started_at='',mix_end_at='' WHERE batch_no=?",(active,))
                    con.commit(); con.close()
                    stage_event(active,sidx,stage["title"],"STAGE_COMPLETE","",USER["username"])
                    advance_stage(active); st.rerun()
        else:
            check=st.checkbox("Faz homojenliği / kaynak talimatı tamamlandı",key=f"v09phaseok_{active}_{sidx}")
            if st.button("✅ FAZ TAMAM — SONRAKİ FAZ",type="primary",
                         disabled=not check,key=f"v09phaseadvance_{active}_{sidx}",use_container_width=True):
                stage_event(active,sidx,stage["title"],"STAGE_COMPLETE","",USER["username"])
                advance_stage(active); st.rerun()
        return

def phase_architecture_df(product):
    rows=[]
    for i,s in enumerate(phase_list(product),1):
        rows.append({
            "Faz":i,
            "Başlık":s.get("title"),
            "Tip":s.get("kind",classify_stage(s)),
            "Kap":s.get("vessel","ANA KAZAN"),
            "Hammaddeler":", ".join(s.get("materials",[])) or "—",
            "Kaynak/Talimat":s.get("source_text",""),
            "Dayanak":s.get("basis","R04 KONTROLLÜ SOP"),
            "R04 Süre":s.get("source_time") or "—",
            "Pilot Süre":("—" if not s.get("pilot_min") else f"{s.get('pilot_min')} dk"),
            "Pilot RPM":s.get("pilot_rpm") or "—",
        })
    return pd.DataFrame(rows)


def render_brand_header(login=False):
    """Corporate KayaCar header; degrades gracefully if logo is missing."""
    if LOGO_PATH.exists():
        if login:
            left,mid,right=st.columns([1,3.2,1])
            with mid:
                st.image(str(LOGO_PATH),use_container_width=True)
        else:
            a,b=st.columns([2.3,5.7])
            with a:
                st.image(str(LOGO_PATH),use_container_width=True)
            with b:
                st.markdown("<div class='brand-title'>KİMYASAL ÜRETİM YÜRÜTME SİSTEMİ</div>",unsafe_allow_html=True)
                st.markdown("<div class='brand-sub'>Professional Car Care Chemicals • MES</div>",unsafe_allow_html=True)
    else:
        st.markdown("<div class='brand-title'>KayaCar Kimyasal — MES</div>",unsafe_allow_html=True)


def product_label_meta(product):
    meta={
      "Lastik Parlatıcı Jel":("TIRE SHINE GEL","LASTİK PARLATICI JEL","DEEP BLACK • WET LOOK • LONG LASTING","#168db2"),
      "Sıvı Lastik Parlatıcı":("LIQUID TIRE SHINE","SIVI LASTİK PARLATICI","GLOSS FINISH • FAST APPLICATION","#168db2"),
      "Torpido Temizleme & Bakım Sütü":("DASHBOARD CARE MILK","TORPİDO TEMİZLEME & BAKIM SÜTÜ","CLEAN • SATIN FINISH • INTERIOR CARE","#7fb8c9"),
      "Normal Oto Yıkama Şampuanı":("CAR SHAMPOO","OTO YIKAMA ŞAMPUANI","HIGH FOAM • EFFECTIVE CLEANING","#2485d0"),
      "Pembe Oto Yıkama Şampuanı":("PINK CAR SHAMPOO","PEMBE OTO YIKAMA ŞAMPUANI","HIGH FOAM • PROFESSIONAL FORMULA","#d86b9e"),
      "pH Nötr Premium Oto Şampuanı":("pH NEUTRAL PREMIUM SHAMPOO","pH NÖTR PREMIUM OTO ŞAMPUANI","COATING SAFE • GENTLE CLEANING","#69b8cf"),
      "Cilalı Oto Yıkama Şampuanı":("WASH & SHINE","CİLALI OTO YIKAMA ŞAMPUANI","WASH • GLOSS • PROTECTION","#25a6a8"),
      "Islak Cila / Wet Surface":("WET SURFACE","HIZLI DURULAMA CİLASI","HIGH GLOSS • FAST WATER BREAK","#17a9aa"),
      "Demir Tozu Sökücü":("IRON REMOVER","DEMİR TOZU SÖKÜCÜ","PROFESSIONAL DECONTAMINATION","#8354b8"),
      "Cam Temizleyici":("GLASS CLEANER","CAM TEMİZLEYİCİ","STREAK FREE • CLEAR FINISH","#83c8df"),
      "Zift / Katran Sökücü":("TAR REMOVER","ZİFT / KATRAN SÖKÜCÜ","FAST ACTION • PROFESSIONAL USE","#ba813a"),
      "Oto Parfümü":("AUTO PERFUME","OTO PARFÜMÜ","PROFESSIONAL INTERIOR FRAGRANCE","#8b65b5")
    }
    return meta.get(product,(product.upper(),product.upper(),"PROFESSIONAL CAR CARE CHEMICALS","#25a6a8"))


def label_preview_html(product,batch_no="",net_text="1 L"):
    en,tr,claim,accent=product_label_meta(product)
    code=PRODUCTS.get(product,{}).get("code","")
    lot=batch_no or "KC-LOT-________"
    return f"""
    <div class='label-shell'>
      <div class='label-accent' style='background:{accent}'></div>
      <div class='label-brand'>Kaya<span>Car</span></div>
      <div class='label-series'>PROFESSIONAL CAR CARE CHEMICALS</div>
      <div class='label-rule'></div>
      <div class='label-en'>{en}</div>
      <div class='label-product'>{tr}</div>
      <div class='label-claim'>{claim}</div>
      <div class='label-bottom'>
        <div><b>PROFESSIONAL FORMULA</b><br><small>{code}</small></div>
        <div class='label-net'>{net_text}</div>
      </div>
      <div class='label-lot'>BATCH / LOT: {lot}</div>
    </div>"""


def label_print_html(product,batch_no,net_text):
    preview=label_preview_html(product,batch_no,net_text)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>KayaCar Etiket</title>
    <style>body{{background:#eee;font-family:Arial;padding:30px}} .label-shell{{width:420px;min-height:620px;background:#0b1117;color:#fff;border-radius:20px;padding:28px;position:relative;box-sizing:border-box}} .label-accent{{height:8px;border-radius:8px;margin-bottom:28px}} .label-brand{{font-size:42px;font-weight:900}} .label-brand span{{color:#27a9ce}} .label-series{{font-size:11px;letter-spacing:2px;color:#bcc8d2}} .label-rule{{height:1px;background:#53616c;margin:22px 0 35px}} .label-en{{font-size:14px;letter-spacing:1.4px;color:#b9c4cc}} .label-product{{font-size:32px;font-weight:900;margin-top:7px;line-height:1.08}} .label-claim{{margin-top:30px;font-size:14px;letter-spacing:1.2px}} .label-bottom{{display:flex;justify-content:space-between;align-items:end;position:absolute;left:28px;right:28px;bottom:58px}} .label-net{{font-size:30px;font-weight:900}} .label-lot{{position:absolute;bottom:24px;font-size:11px;color:#9eabb4}}</style></head><body>{preview}</body></html>"""

# -----------------------------
# UI
# -----------------------------

def render_command_production(active, operator=False):
    # v0.9 uses phase-based execution. Kept same function name to avoid changing tabs.
    render_phase_engine(active,operator=operator)

st.set_page_config(page_title="KayaCar Kimyasal MES",page_icon="⚗️",layout="wide")
st.markdown("""
<style>
.block-container {padding-top:1rem;padding-bottom:2rem;}
[data-testid="stMetric"] {background:#0b2234;border:1px solid #31526a;padding:12px;border-radius:10px;}
[data-testid="stMetric"] label, [data-testid="stMetric"] [data-testid="stMetricLabel"] {color:#dce7ef !important;}
[data-testid="stMetric"] [data-testid="stMetricValue"] {color:#ffffff !important;}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {color:#b8d7e8 !important;}
.kc-step {font-size:1.35rem;font-weight:800;padding:16px;border-radius:12px;background:#071b31;color:#fff;border:1px solid #d8ab46;margin:8px 0 12px;}
.bigweight {font-size:2.5rem;font-weight:900;}
.operator-card {background:#07131f;border:1px solid #31526a;border-radius:14px;padding:18px;margin:8px 0;}
</style>
""",unsafe_allow_html=True)
init_db()

if "user" not in st.session_state:
    st.session_state["user"]=None

if not st.session_state["user"]:
    render_brand_header(login=True)
    st.markdown("<div class='login-kicker'>KİMYASAL ÜRETİM • KALİTE • STOK • İZLENEBİLİRLİK</div>",unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<div class='kc-section'>Yetkili Kullanıcı Girişi</div>",unsafe_allow_html=True)
        with st.form("login"):
            u=st.text_input("Kullanıcı adı",placeholder="Kullanıcı adınızı girin")
            p=st.text_input("Şifre",type="password",placeholder="••••••••")
            go=st.form_submit_button("GİRİŞ YAP",type="primary",use_container_width=True)
    if go:
        user=authenticate(u,p)
        if user:
            st.session_state["user"]=user
            audit(user["username"],"LOGIN","Giriş başarılı")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")
    st.caption("İlk kurulum: admin / 1234 veya operator / 1234 • Canlı kullanımdan önce varsayılan şifreleri değiştirin.")
    st.stop()

USER=st.session_state["user"]
ROLE=USER["role"]

head,logout=st.columns([5.5,1])
with head:
    render_brand_header(login=False)
    st.caption(f"v0.11 CLOUD • Kullanıcı: {USER['username']} • Rol: {ROLE}")
with logout:
    st.write("")
    if st.button("Çıkış",use_container_width=True):
        audit(USER["username"],"LOGOUT","Çıkış")
        st.session_state["user"]=None
        st.rerun()

if ROLE=="OPERATOR":
    tabs=st.tabs(["🏭 ÜRETİM","📦 Stok Durumu","🗂️ Parti Geçmişi"])
else:
    tabs=st.tabs(["📊 Patron Paneli","🏭 Üretim Konsolu","🧾 Reçeteler","📦 Hammadde Stok","🧾 Satın Alma / Tank","🛢️ Tanklar","📦 Mamul / WIP","⚖️ Terazi Ayarı","🏷️ Etiketleme / QR","🗂️ Parti Geçmişi","👥 Kullanıcı / Log"])


# ---------------- OPERATOR UI ----------------
if ROLE=="OPERATOR":
    with tabs[0]:
        st.subheader("🏭 Operatör Üretim Ekranı")
        ob=open_batches()
        if ob.empty:
            st.info("Aktif üretim partisi yok. Yeni partiyi patron/admin başlatır.")
        else:
            options=ob["batch_no"].tolist()
            active=st.selectbox("Parti",options,key="op_active_batch")
            render_command_production(active,operator=True)

    with tabs[1]:
        st.subheader("📦 Stok Durumu")
        s=stock_df()[["name","stock_kg"]].rename(columns={"name":"Hammadde","stock_kg":"Stok kg"})
        st.dataframe(s,use_container_width=True,hide_index=True)

    with tabs[2]:
        st.subheader("🗂️ Parti Geçmişi")
        st.dataframe(all_batches()[["batch_no","product","target_kg","created_at","status"]],
                     use_container_width=True,hide_index=True)

# ---------------- ADMIN UI ----------------
else:

    # ---- Patron Dashboard ----
    with tabs[0]:
        st.subheader('📊 Patron Paneli')
        st.caption('v0.11: Faz/operasyon tabanlı üretim, proses suyu, tank-stok ve parti izlenebilirliği.')
        mats=stock_df(); hist=all_batches()
        fg_dash=finished_goods_df(); wip_dash=wip_summary_df()
        c1,c2,c3,c4=st.columns(4)
        c1.metric('Ürün Yelpazesi',len(PRODUCTS))
        c2.metric('Hammadde Ana Stok',f"{mats['stock_kg'].sum():,.1f} kg")
        c3.metric('Mamul Stok',f"{fg_dash['stock_kg'].sum():,.1f} kg")
        c4.metric('Aktif WIP',len(wip_dash))
        low=low_stock_materials(5)
        if not low.empty:
            st.warning('5 kg altındaki hammaddeler')
            st.dataframe(low[['name','stock_kg','supplier']],use_container_width=True,hide_index=True)
        st.subheader('Son Partiler')
        if not hist.empty:
            h=hist.head(10).copy()
            h['Maliyet TL']=[batch_cost(x) for x in h['batch_no']]
            st.dataframe(h,use_container_width=True,hide_index=True)

    # ---- Production Console ----
    with tabs[1]:
        st.subheader("Yeni / Devam Eden Üretim")
        ob=open_batches()
        c1,c2=st.columns([1,1])
        with c1:
            new_product=st.selectbox("Yeni parti ürünü",list(PRODUCTS.keys()))
            new_kg=st.number_input("Hedef parti (kg)",min_value=0.1,value=1.0,step=0.5)
            new_note=st.text_input("Parti notu")
            if st.button("➕ Yeni parti başlat",type="primary"):
                no=create_batch(new_product,new_kg,new_note)
                st.session_state["active_batch"]=no
                st.success(f"Başlatıldı: {no}")
                st.rerun()
        with c2:
            options=ob["batch_no"].tolist() if not ob.empty else []
            active_default=st.session_state.get("active_batch")
            if active_default not in options:
                active_default=options[0] if options else None
            if options:
                index=options.index(active_default) if active_default in options else 0
                active=st.selectbox("Devam eden parti",options,index=index)
                st.session_state["active_batch"]=active
            else:
                active=None
                st.info("Devam eden parti yok.")

        if active:
            st.divider()
            render_command_production(active,operator=False)
            log=batch_log(active)
            if not log.empty:
                st.subheader("Gerçekleşen dozajlar")
                st.dataframe(log,use_container_width=True,hide_index=True)


    # ---- Recipes ----
    with tabs[2]:
        psel=st.selectbox("Ürün",list(PRODUCTS.keys()),key="recipe_product")
        kg=st.number_input("Hedef kg",0.1,10000.0,1.0,0.5,key="recipe_kg")
        d=recipe_df(psel,kg)
        mats=stock_df()[["name","unit_cost_tl"]]
        d=d.merge(mats,left_on="Hammadde",right_on="name",how="left")
        d["Tahmini TL"]=d["Hedef kg"]*d["unit_cost_tl"].fillna(0)
        st.info(f"{PRODUCTS[psel]['code']} | {PRODUCTS[psel]['platform']} | Hedef pH: {PRODUCTS[psel]['ph']}")
        with st.expander("📘 R04 ürün üretim prosedürü", expanded=False):
            st.dataframe(product_sop_table(psel),use_container_width=True,hide_index=True)
        with st.expander("🏗️ v0.11 FAZ MİMARİSİ / ISA-88 BENZERİ YÜRÜTME", expanded=True):
            st.dataframe(phase_architecture_df(psel),use_container_width=True,hide_index=True)
            wr=WATER_RULES.get(psel)
            if wr:
                st.info("💧 Proses suyu planı: "+wr.get("basis",""))
            st.caption("Önemli: faz mimarisi kaynak SOP'yi hammadde satırından ayırır. Karıştırma faz sonunda bir kez yapılır; ayrı ön karışım/transfer/kontrol/hold adımları ayrı fazdır.")
        st.dataframe(d[["Sıra","Hammadde","%","Hedef kg","Hedef g","unit_cost_tl","Tahmini TL"]],use_container_width=True,hide_index=True)
        st.metric("Tahmini hammadde maliyeti",f"{d['Tahmini TL'].sum():,.2f} TL")

    # ---- Stocks ----
    with tabs[3]:
        st.subheader("Hammadde ana stok")
        sdf=stock_df()
        edited=st.data_editor(
            sdf,use_container_width=True,hide_index=True,disabled=["name"],
            column_config={
                "name":"Hammadde",
                "stock_kg":st.column_config.NumberColumn("Stok kg",min_value=0.0,format="%.3f"),
                "unit_cost_tl":st.column_config.NumberColumn("TL/kg",min_value=0.0,format="%.2f"),
                "supplier":"Tedarikçi",
                "active_pct":st.column_config.NumberColumn("Aktif %", min_value=0.0, max_value=100.0, format="%.2f"),
                "note":"Not"
            }
        )
        if st.button("💾 Stok kartlarını kaydet",type="primary"):
            save_stock_editor(edited)
            st.success("Kaydedildi.")
        st.caption("Üretim konsolunda bir hammadde 'TAMAM' yapıldığında gerçek tartılan gram ana stoktan otomatik düşer.")


    # ---- Purchase / Raw Stock + Tank ----
    with tabs[4]:
        st.subheader("🧾 Hammadde Satın Alma → Otomatik Tank Girişi")
        st.info("Satın alma kaydı iki yerde birden tutulur: **Hammadde Ana Stok** + **Fiziksel Tank/Varil**. Tank numarası stok hareketine yazılır.")
        mats=stock_df()["name"].tolist()
        c1,c2=st.columns(2)
        with c1:
            rm=st.selectbox("Hammadde",mats,key="receipt_material")
            qty=st.number_input("Giriş miktarı kg",min_value=0.001,value=25.0,step=1.0)
            price=st.number_input("Alış TL/kg",min_value=0.0,value=0.0,step=1.0)
            supplier=st.text_input("Tedarikçi")
        with c2:
            existing=tank_options_for_material(rm)
            choices=["AUTO — uygun tankı doldur / gerekirse yeni tank aç"] + [
                f"{x['tank_name']} | {x['current_kg']:.2f}/{x['capacity_kg']:.2f} kg | boş {x['free_kg']:.2f} kg"
                for x in existing
            ]
            tank_choice=st.selectbox("Hammadde Tankı / Varil No",choices)
            auto_tank=tank_choice.startswith("AUTO")
            selected_tank=None if auto_tank else tank_choice.split(" | ")[0]
            default_cap=st.number_input("Yeni tank açılırsa kapasite (kg)",min_value=1.0,value=25.0,step=1.0,
                                        disabled=not auto_tank)
            lot=st.text_input("Tedarikçi lot / irsaliye no")
            rnote=st.text_area("Not")

        if existing:
            st.caption("Uygun tanklar: " + " • ".join(
                f"{x['tank_name']} (%{(x['current_kg']/x['capacity_kg']*100 if x['capacity_kg'] else 0):.0f})"
                for x in existing))
        else:
            st.warning(f"{rm} için tank yok. AUTO seçiliyse sistem otomatik **{next_tank_name()}** numarasıyla tank açacak.")

        if st.button("📥 STOĞA AL + TANKA YERLEŞTİR",type="primary",use_container_width=True):
            try:
                allocations=receive_stock_to_tank(rm,qty,price if price>0 else None,supplier,lot,rnote,
                                                   selected_tank,auto_tank,default_cap)
                alloc=", ".join(f"{n}: +{q:.3f} kg" for n,q in allocations)
                audit(USER["username"],"RAW_RECEIPT",f"{rm} +{qty} kg | {alloc}")
                st.success(f"✅ Ana stok + tank işlendi. {alloc}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.subheader("Son Hammadde Stok Hareketleri")
        sm=stock_movements_df()
        show=[c for c in ["created_at","material","movement_type","qty_kg","tank_name","ref","note"] if c in sm.columns]
        st.dataframe(sm[show].head(100),use_container_width=True,hide_index=True)

    # ---- Tanks ----
    with tabs[5]:
        st.subheader("🛢️ Hammadde Tankları / Varilleri")
        st.info("Başlangıçta doluluk manuel girilir. Yazılım aynı modeli load-cell, ultrasonik/radar veya Modbus sensörüne sonradan bağlayabilir.")
        mats=stock_df()["name"].tolist()
        with st.expander("➕ Tank / varil ekle",expanded=False):
            a,b,c,d=st.columns(4)
            tm=a.selectbox("Hammadde",mats,key="tank_material")
            tn=b.text_input("Tank adı",value=next_tank_name())
            cap=c.number_input("Kapasite kg",min_value=0.1,value=25.0)
            low=d.number_input("Düşük seviye alarmı %",min_value=1.0,max_value=90.0,value=15.0)
            cur=st.number_input("İlk mevcut miktar kg",min_value=0.0,value=0.0)
            if st.button("➕ Tank Ekle",type="primary"):
                con=db()
                con.execute("""INSERT INTO tanks(material,tank_name,capacity_kg,current_kg,mode,low_alarm_pct)
                               VALUES(?,?,?,?,?,?)""",(tm,tn,cap,min(cur,cap),"MANUEL",low))
                con.commit(); con.close()
                st.rerun()

        tdf=tanks_df()
        if tdf.empty:
            st.caption("Henüz tank tanımlanmadı.")
        else:
            total_cur=float(tdf["current_kg"].sum())
            total_cap=float(tdf["capacity_kg"].sum())
            avg=(total_cur/total_cap*100) if total_cap else 0
            low_count=0
            for _,r in tdf.iterrows():
                pct=(r["current_kg"]/r["capacity_kg"]*100) if r["capacity_kg"] else 0
                if pct<=r["low_alarm_pct"]: low_count+=1
            m1,m2,m3,m4=st.columns(4)
            m1.metric("Toplam Tank Stoku",f"{total_cur:,.1f} kg")
            m2.metric("Ortalama Doluluk",f"%{avg:.1f}")
            m3.metric("Düşük Seviyeli",f"{low_count} tank")
            m4.metric("Toplam Tank",len(tdf))

            st.subheader("Tanklar — Grafiksel Görünüm")
            rows=[r for _,r in tdf.iterrows()]
            for k in range(0,len(rows),4):
                cols=st.columns(4)
                for j,r in enumerate(rows[k:k+4]):
                    with cols[j]:
                        tank_card(r)

            st.subheader("Tank Listesi / Manuel Güncelleme")
            for _,r in tdf.iterrows():
                pct=(r["current_kg"]/r["capacity_kg"]*100) if r["capacity_kg"] else 0
                c1,c2,c3,c4=st.columns([2.2,2.6,1.4,1])
                c1.write(f"**{r['tank_name']}**")
                c1.caption(r["material"])
                c2.progress(min(max(pct/100,0),1),text=f"{r['current_kg']:.2f}/{r['capacity_kg']:.2f} kg — %{pct:.1f}")
                newcur=c3.number_input("Mevcut kg",0.0,float(r["capacity_kg"]),float(r["current_kg"]),0.1,
                                       key=f"tankedit_{r['id']}",label_visibility="collapsed")
                if c4.button("Kaydet",key=f"save_tank_{r['id']}"):
                    con=db()
                    con.execute("UPDATE tanks SET current_kg=? WHERE id=?",(newcur,int(r["id"])))
                    con.commit(); con.close()
                    st.rerun()
                if pct<=5:
                    st.error(f"🔴 {r['tank_name']} kritik seviye: %{pct:.1f}")
                elif pct<=r["low_alarm_pct"]:
                    st.warning(f"🟠 {r['tank_name']} düşük seviye: %{pct:.1f}")

    # ---- Finished Goods / WIP ----
    with tabs[6]:
        st.subheader("📦 Mamul Stoğu / Üretim Halindeki Stok (WIP)")
        st.info("Doğru stok mimarisi: **Hammadde → WIP / Üretim Halindeki Parti → Mamul / Satılabilir Ürün Stoğu**.")

        wip=wip_summary_df()
        fgdf=finished_goods_df()
        a,b,c,d=st.columns(4)
        a.metric("Aktif WIP Parti",len(wip))
        b.metric("WIP Hedef Toplam",f"{wip['target_kg'].sum() if not wip.empty else 0:,.2f} kg")
        c.metric("Mamul Toplam",f"{fgdf['stock_kg'].sum():,.2f} kg")
        d.metric("Mamul Hammadde Değeri",f"{(fgdf['stock_kg']*fgdf['unit_cost_tl']).sum():,.2f} TL")

        st.subheader("Üretim Halindeki Partiler (WIP)")
        if wip.empty: st.caption("Aktif üretim partisi yok.")
        else: st.dataframe(wip,use_container_width=True,hide_index=True)

        st.subheader("Mamul / Ürün Yelpazesi Stoğu")
        disp=fgdf.rename(columns={"product":"Ürün","stock_kg":"Stok kg","unit_cost_tl":"Ort. Hammadde Maliyeti TL/kg","note":"Not"})
        st.dataframe(disp,use_container_width=True,hide_index=True)

        completed=all_batches()
        eligible=completed[(completed["status"]=="TAMAMLANDI") & (completed["fg_received"]==0)] if (not completed.empty and "fg_received" in completed.columns) else completed.iloc[0:0]

        with st.expander("🏭 Tamamlanan partiyi mamul stoğa al",expanded=not eligible.empty):
            if eligible.empty:
                st.caption("Bekleyen tamamlanmış parti yok.")
            else:
                bno=st.selectbox("Parti",eligible["batch_no"].tolist(),key="fg_receive_batch")
                bb=get_batch(bno)
                actual_out=st.number_input("Gerçek mamul çıkış miktarı (kg)",min_value=0.001,value=float(bb["target_kg"]),step=0.1)
                fnote=st.text_input("Mamul giriş notu")
                if st.button("✅ MAMUL STOĞA AL",type="primary"):
                    try:
                        receive_finished_batch(bno,actual_out,fnote)
                        audit(USER["username"],"FG_RECEIPT",f"{bno} | {actual_out} kg")
                        st.success("Mamul stoğa alındı."); st.rerun()
                    except Exception as e: st.error(str(e))

        with st.expander("🚚 Mamul stoktan sevk / satış çıkışı"):
            psel=st.selectbox("Ürün",list(PRODUCTS.keys()),key="fg_issue_product")
            current=float(fgdf.loc[fgdf["product"]==psel,"stock_kg"].iloc[0]) if (fgdf["product"]==psel).any() else 0
            st.write(f"Mevcut mamul stok: **{current:.3f} kg**")
            q=st.number_input("Çıkış kg",min_value=0.001,value=1.0,step=0.1)
            ref=st.text_input("Fatura / sevk / müşteri referansı")
            note=st.text_input("Çıkış notu")
            if st.button("📤 MAMUL STOKTAN DÜŞ"):
                try:
                    issue_finished_goods(psel,q,ref,note)
                    audit(USER["username"],"FG_ISSUE",f"{psel} | -{q} kg")
                    st.success("Mamul stoktan düşüldü."); st.rerun()
                except Exception as e: st.error(str(e))

        st.subheader("Mamul Stok Hareketleri")
        mv=finished_goods_movements_df()
        if mv.empty: st.caption("Henüz mamul hareketi yok.")
        else: st.dataframe(mv.head(100),use_container_width=True,hide_index=True)

    # ---- Scale Settings ----
    with tabs[7]:
        st.subheader("Hassas terazi bağlantısı")
        st.write("Destek planı: **MANUEL → SIMULATOR → USB/RS-232 Serial → modele özel sürekli canlı okuma**")
        scale_modes=["MANUEL","SIMULATOR","SERIAL"]
        current_mode=setting("scale_mode","MANUEL")
        mode=st.radio(
            "Terazi modu",
            scale_modes,
            index=scale_modes.index(current_mode) if current_mode in scale_modes else 0,
            horizontal=True
        )
        port=st.text_input("Serial port",value=setting("serial_port","COM3"),
                           help="Windows örn. COM3, Linux örn. /dev/ttyUSB0")
        baud_values=[1200,2400,4800,9600,19200,38400,57600,115200]
        saved_baud=int(setting("baudrate","9600"))
        baud=st.selectbox("Baudrate",baud_values,
                          index=baud_values.index(saved_baud) if saved_baud in baud_values else 3)
        tol=st.number_input("Tolerans %",0.01,10.0,float(setting("tolerance_pct","0.50")),0.05)
        mintol=st.number_input("Minimum tolerans gram",0.01,100.0,float(setting("min_tolerance_g","1.0")),0.1)
        tare_cmd=st.text_input("TARE komutu (modele özel)",value=setting("tare_command",""),
                               placeholder=r"Örn: T\r\n")
        read_cmd=st.text_input("READ komutu (gerekiyorsa)",value=setting("scale_read_command",""),
                               placeholder=r"Örn: P\r\n")
        stable_window=st.number_input("Stabilite örnek sayısı",3,20,int(setting("stable_window","5")),1)
        stable_delta=st.number_input("Stabil sayılacak max-min farkı (g)",0.01,50.0,
                                     float(setting("stable_delta_g","0.5")),0.1)
        yellow_pct=st.number_input("Hedefe yaklaşma sarı zonu (%)",0.1,50.0,
                                   float(setting("yellow_zone_pct","5.0")),0.5)
        beep_on=st.checkbox("Hedef gramaja gelince sesli uyarı",
                            value=setting("auto_beep","1")=="1")

        if st.button("⚙️ Ayarları kaydet",type="primary"):
            set_setting("scale_mode",mode)
            set_setting("serial_port",port)
            set_setting("baudrate",baud)
            set_setting("tolerance_pct",tol)
            set_setting("min_tolerance_g",mintol)
            set_setting("tare_command",tare_cmd)
            set_setting("scale_read_command",read_cmd)
            set_setting("stable_window",stable_window)
            set_setting("stable_delta_g",stable_delta)
            set_setting("yellow_zone_pct",yellow_pct)
            set_setting("auto_beep","1" if beep_on else "0")
            st.success("Ayarlar kaydedildi.")

        if mode=="SIMULATOR":
            simulator_controls("settings_sim")
            st.write(f"Simülatör ağırlığı: **{st.session_state.get('sim_scale_g',0.0):,.2f} g**")
        elif mode=="SERIAL":
            if st.button("🧪 Terazi test oku"):
                g,raw=read_scale_once()
                st.write("Ham:",raw)
                st.write("Okunan:",None if g is None else f"{g:.2f} g")
        st.warning("Gerçek terazi marka/modeli geldiğinde bu generic Serial katmanı modele özel sürekli akış, stabil ağırlık biti ve otomatik TARE ile değiştirilecek.")

    # ---- Corporate Label / QR ----
    with tabs[8]:
        st.subheader("🏷️ Kurumsal Etiketleme / Parti QR")
        st.caption("KayaCar master etiket sistemi: ürün kimliği + parti/lot + QR. Güvenlik ve mevzuat metinleri kontrollü kaynak onayı sonrası eklenmelidir.")
        lc1,lc2=st.columns([1,1.05])
        with lc1:
            label_product=st.selectbox("Etiket ürünü",list(PRODUCTS.keys()),key="label_product")
            hist=all_batches()
            batch_options=[""]+(hist[hist["product"]==label_product]["batch_no"].tolist() if not hist.empty else [])
            label_batch=st.selectbox("Parti / Lot (opsiyonel)",batch_options,key="label_batch")
            pack=st.selectbox("Net miktar",["500 mL","1 L","5 L","20 kg","22 kg","Özel"],key="label_pack")
            if pack=="Özel":
                pack=st.text_input("Özel net miktar",value="1 L",key="label_pack_custom")
            st.markdown("**Etiket bilgileri**")
            st.code(batch_label_text(label_batch) if label_batch else f"KayaCar | {label_product} | {PRODUCTS[label_product]['code']}")
            html=label_print_html(label_product,label_batch,pack).encode("utf-8")
            st.download_button("🖨️ Baskı önizleme HTML indir",html,file_name=f"KayaCar_{PRODUCTS[label_product]['code']}_{label_batch or 'TASLAK'}.html",mime="text/html",use_container_width=True)
            if label_batch:
                png=qr_png_bytes(label_batch)
                if png:
                    st.image(png,width=180)
                    st.download_button("QR PNG indir",png,file_name=f"{label_batch}_QR.png",mime="image/png",use_container_width=True)
                else:
                    st.warning("qrcode paketi kurulu değil.")
        with lc2:
            st.markdown("**Ön etiket canlı önizleme**")
            st.markdown(label_preview_html(label_product,label_batch,pack),unsafe_allow_html=True)

        if BRAND_BOARD_PATH.exists():
            with st.expander("🎨 Marka / etiket referans panosu"):
                st.image(str(BRAND_BOARD_PATH),use_container_width=True)

    # ---- History ----
    with tabs[9]:
        st.subheader("🗂️ Parti Geçmişi")
        hist=all_batches()
        if hist.empty:
            st.info("Henüz parti geçmişi yok. İlk parti oluşturulduğunda kayıtlar burada görünecek.")
        else:
            st.dataframe(hist,use_container_width=True,hide_index=True)
            sel=st.selectbox("Parti detayı",hist["batch_no"].tolist(),key="history_batch_detail_v011")
            st.dataframe(batch_log(sel),use_container_width=True,hide_index=True)
            con=db()
            slog=pd.read_sql_query("SELECT stage_index,stage_title,event,detail,username,created_at FROM stage_log WHERE batch_no=? ORDER BY id",
                                   con,params=(sel,))
            con.close()
            if not slog.empty:
                st.subheader("Faz / Proses Olay Kaydı")
                st.dataframe(slog,use_container_width=True,hide_index=True)

    # ---- Users / Audit ----
    with tabs[10]:
        st.subheader("👥 Kullanıcı Yönetimi")
        st.dataframe(users_df(),use_container_width=True,hide_index=True)
        with st.expander("Yeni kullanıcı"):
            nu=st.text_input("Yeni kullanıcı adı")
            np=st.text_input("Yeni şifre",type="password")
            nr=st.selectbox("Rol",["OPERATOR","ADMIN"])
            if st.button("Kullanıcı ekle"):
                try:
                    add_user(nu,np,nr)
                    audit(USER["username"],"USER_CREATE",f"{nu} / {nr}")
                    st.success("Kullanıcı eklendi.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with st.expander("Şifre / rol değiştir"):
            ulist=users_df()["username"].tolist()
            eu=st.selectbox("Kullanıcı",ulist)
            ep=st.text_input("Yeni şifre",type="password",key="editpass")
            er=st.selectbox("Yeni rol",["ADMIN","OPERATOR"],key="editrole")
            active_user=st.checkbox("Aktif",value=True)
            if st.button("Kullanıcıyı güncelle"):
                update_user(eu,ep if ep else None,er,active_user)
                audit(USER["username"],"USER_UPDATE",eu)
                st.success("Güncellendi.")
        st.subheader("Audit Log")
        st.dataframe(audit_df().head(500),use_container_width=True,hide_index=True)

st.divider()
st.caption("KayaCar Kimyasal MES v0.11 CLOUD — Faz tabanlı üretim • Tank/Stok • Kurumsal Etiket/QR • Mobil uyumlu arayüz.")

