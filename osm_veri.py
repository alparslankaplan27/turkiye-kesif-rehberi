# Türkiye Keşif Rehberi - OpenStreetMap verisini il il indirip ilçelere ayırır.
# GitHub Actions tarafından çalıştırılır; sonuçlar data/osm/<plaka>.json dosyalarına yazılır.
# Veri: © OpenStreetMap katkıda bulunanlar (ODbL).
import json, os, time, urllib.request, urllib.parse, datetime, sys

ILLER = {"1": "Adana", "2": "Adıyaman", "3": "Afyonkarahisar", "4": "Ağrı", "5": "Amasya", "6": "Ankara", "7": "Antalya", "8": "Artvin", "9": "Aydın", "10": "Balıkesir", "11": "Bilecik", "12": "Bingöl", "13": "Bitlis", "14": "Bolu", "15": "Burdur", "16": "Bursa", "17": "Çanakkale", "18": "Çankırı", "19": "Çorum", "20": "Denizli", "21": "Diyarbakır", "22": "Edirne", "23": "Elazığ", "24": "Erzincan", "25": "Erzurum", "26": "Eskişehir", "27": "Gaziantep", "28": "Giresun", "29": "Gümüşhane", "30": "Hakkari", "31": "Hatay", "32": "Isparta", "33": "Mersin", "34": "İstanbul", "35": "İzmir", "36": "Kars", "37": "Kastamonu", "38": "Kayseri", "39": "Kırklareli", "40": "Kırşehir", "41": "Kocaeli", "42": "Konya", "43": "Kütahya", "44": "Malatya", "45": "Manisa", "46": "Kahramanmaraş", "47": "Mardin", "48": "Muğla", "49": "Muş", "50": "Nevşehir", "51": "Niğde", "52": "Ordu", "53": "Rize", "54": "Sakarya", "55": "Samsun", "56": "Siirt", "57": "Sinop", "58": "Sivas", "59": "Tekirdağ", "60": "Tokat", "61": "Trabzon", "62": "Tunceli", "63": "Şanlıurfa", "64": "Uşak", "65": "Van", "66": "Yozgat", "67": "Zonguldak", "68": "Aksaray", "69": "Bayburt", "70": "Karaman", "71": "Kırıkkale", "72": "Batman", "73": "Şırnak", "74": "Bartın", "75": "Ardahan", "76": "Iğdır", "77": "Yalova", "78": "Karabük", "79": "Kilis", "80": "Osmaniye", "81": "Düzce"}
UCLAR = ["https://overpass-api.de/api/interpreter",
         "https://overpass.kumi.systems/api/interpreter",
         "https://overpass.private.coffee/api/interpreter"]
TARIHI = {"castle":"Kale","fort":"Kale","ruins":"Ören yeri","archaeological_site":"Arkeolojik alan","monument":"Anıt",
  "mosque":"Tarihî cami","church":"Tarihî kilise","tomb":"Türbe","city_gate":"Tarihî kapı","aqueduct":"Su kemeri",
  "bridge":"Tarihî köprü","building":"Tarihî yapı","caravanserai":"Kervansaray","citywalls":"Surlar","fountain":"Tarihî çeşme",
  "palace":"Saray","manor":"Konak","monastery":"Manastır","heritage":"Tarihî miras","castle_wall":"Surlar","hammam":"Hamam",
  "synagogue":"Sinagog","tower":"Tarihî kule","memorial":"Anıt"}
AKT = {"attraction":"Gezilecek yer","viewpoint":"Seyir noktası","theme_park":"Tema parkı","zoo":"Hayvanat bahçesi",
  "aquarium":"Akvaryum","park":"Park","nature_reserve":"Doğa koruma alanı","water_park":"Su parkı","beach_resort":"Plaj tesisi",
  "beach":"Plaj","waterfall":"Şelale","cave_entrance":"Mağara","peak":"Zirve"}
LIMIT = 30

def norm(t):
    t = t.replace("I", "ı").replace("İ", "i").lower()
    return t.translate(str.maketrans("çğıöşüâî", "cgiosuai"))

def sorgu(il):
    f = "(area.a)"
    return f"""[out:json][timeout:300];
area["boundary"="administrative"]["admin_level"="4"]["name"="{il}"]->.il;
rel["boundary"="administrative"]["admin_level"="6"](area.il)->.ds;
foreach.ds->.d(
  .d out tags;
  .d map_to_area->.a;
  (nwr["historic"]["name"]{f};
   nwr["tourism"~"^(museum|attraction|viewpoint|theme_park|zoo|aquarium)$"]["name"]{f};
   nwr["leisure"~"^(park|nature_reserve|water_park|beach_resort)$"]["name"]{f};
   nwr["natural"~"^(beach|waterfall|cave_entrance|peak)$"]["name"]{f};
   nwr["amenity"="marketplace"]["name"]{f};
   nwr["shop"="farm"]["name"]{f};);
  out center tags;
);"""

def indir(il):
    veri = urllib.parse.urlencode({"data": sorgu(il)}).encode()
    for tur in range(3):
        for u in UCLAR:
            try:
                req = urllib.request.Request(u, data=veri, headers={"User-Agent": "TurkiyeKesifRehberi/1.0 (github.com/alparslankaplan27/turkiye-kesif-rehberi)"})
                with urllib.request.urlopen(req, timeout=360) as r:
                    j = json.load(r)
                if j.get("remark") and "error" in j["remark"].lower():
                    raise RuntimeError(j["remark"][:120])
                return j.get("elements", [])
            except Exception as e:
                print(f"  {il}: {u} başarısız ({e}); yeniden denenecek", flush=True)
                time.sleep(20)
    return None

def sinifla(t):
    if t.get("amenity") == "marketplace": return "yoresel", "Pazar yeri"
    if t.get("shop") == "farm": return "yoresel", "Üretici satış noktası"
    if t.get("tourism") == "museum": return "tarihi", "Müze"
    h = t.get("historic")
    if h in TARIHI and (h != "memorial" or t.get("wikidata")): return "tarihi", TARIHI[h]
    for k in ("tourism", "leisure", "natural"):
        v = t.get(k)
        if v in AKT:
            if v == "peak" and not t.get("wikidata"): return None, None
            return "aktivite", AKT[v]
    return None, None

def isle(il, elemanlar):
    ilceler, simdiki = {}, None
    for e in elemanlar:
        t = e.get("tags", {})
        if e["type"] == "relation" and t.get("boundary") == "administrative" and t.get("admin_level") == "6":
            ad = t.get("name:tr") or t.get("name", "")
            simdiki = ilceler.setdefault(norm(ad), {"ad": ad, "yerler": {}})
            continue
        if simdiki is None or not t.get("name"): continue
        grup, tur = sinifla(t)
        if not grup: continue
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        if lat is None: continue
        wp = t["wikipedia"][3:] if t.get("wikipedia", "").startswith("tr:") else None
        puan = (3 if t.get("wikidata") else 0) + (2 if wp else 0) + (1 if t.get("tourism") else 0) + (1 if t.get("heritage") else 0)
        ad = t.get("name:tr") or t["name"]
        anahtar = grup + norm(ad)
        eski = simdiki["yerler"].get(anahtar)
        if not eski or eski[5] < puan:
            simdiki["yerler"][anahtar] = [grup, ad, tur, round(lat, 5), round(lon, 5), puan, wp]
    sonuc = {}
    for k, v in ilceler.items():
        liste = sorted(v["yerler"].values(), key=lambda x: (-x[5], x[1]))
        kes = []
        for g in ("tarihi", "aktivite", "yoresel"):
            kes += [x for x in liste if x[0] == g][:LIMIT]
        sonuc[k] = {"ad": v["ad"], "yerler": kes}
    return sonuc

def main():
    os.makedirs("data/osm", exist_ok=True)
    bugun = datetime.date.today().isoformat()
    hatali = []
    for kod, il in ILLER.items():
        print(f"{kod} {il} indiriliyor...", flush=True)
        el = indir(il)
        if el is None:
            hatali.append(il); continue
        ilceler = isle(il, el)
        with open(f"data/osm/{int(kod):02d}.json", "w", encoding="utf-8") as f:
            json.dump({"il": il, "guncel": bugun, "ilceler": ilceler}, f, ensure_ascii=False, separators=(",", ":"))
        print(f"  {len(ilceler)} ilçe, {sum(len(v['yerler']) for v in ilceler.values())} yer", flush=True)
        time.sleep(8)
    with open("data/osm/durum.json", "w", encoding="utf-8") as f:
        json.dump({"guncel": bugun, "hatali_iller": hatali}, f, ensure_ascii=False)
    print("Bitti. Hatalı iller:", hatali)

if __name__ == "__main__":
    main()
