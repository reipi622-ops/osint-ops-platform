import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Pre-seeded known Middle East locations — priority order (most specific first)
# Each entry: key_lower -> (lat, lng, display_name)
KNOWN_LOCATIONS: dict[str, tuple[float, float, str]] = {

    # ── South Lebanon (active zone) ────────────────────────────────────────────
    "nabatieh": (33.3778, 35.4836, "Nabatieh"),
    "nabatiyeh": (33.3778, 35.4836, "Nabatieh"),
    "نبطية": (33.3778, 35.4836, "Nabatieh"),
    "نبطيه": (33.3778, 35.4836, "Nabatieh"),
    "nabatiehchannel": (33.3778, 35.4836, "Nabatieh"),

    "bint jbeil": (33.1180, 35.4314, "Bint Jbeil"),
    "bint jbail": (33.1180, 35.4314, "Bint Jbeil"),
    "بنت جبيل": (33.1180, 35.4314, "Bint Jbeil"),
    "bintjbeil": (33.1180, 35.4314, "Bint Jbeil"),

    "tyre": (33.2705, 35.2037, "Tyre"),
    "sur": (33.2705, 35.2037, "Tyre"),
    "صور": (33.2705, 35.2037, "Tyre"),

    "sidon": (33.5610, 35.3722, "Sidon"),
    "saida": (33.5610, 35.3722, "Sidon"),
    "صيدا": (33.5610, 35.3722, "Sidon"),

    "marjayoun": (33.3617, 35.5919, "Marjayoun"),
    "مرجعيون": (33.3617, 35.5919, "Marjayoun"),

    "khiam": (33.3431, 35.6122, "Khiam"),
    "الخيام": (33.3431, 35.6122, "Khiam"),

    "hasbaya": (33.3958, 35.6847, "Hasbaya"),
    "حاصبيا": (33.3958, 35.6847, "Hasbaya"),

    "qana": (33.2044, 35.3028, "Qana"),
    "قانا": (33.2044, 35.3028, "Qana"),

    "borj al-shaali": (33.2381, 35.2867, "Borj al-Shaali"),
    "brj al-shaali": (33.2381, 35.2867, "Borj al-Shaali"),
    "برج الشمالي": (33.2381, 35.2867, "Borj al-Shaali"),
    "برج الشامالي": (33.2381, 35.2867, "Borj al-Shaali"),

    "kafr kila": (33.1153, 35.5556, "Kafr Kila"),
    "كفركلا": (33.1153, 35.5556, "Kafr Kila"),
    "كفر كلا": (33.1153, 35.5556, "Kafr Kila"),

    "ayta al-sha'b": (33.1347, 35.4444, "Ayta al-Sha'b"),
    "عيتا الشعب": (33.1347, 35.4444, "Ayta al-Sha'b"),
    "عيتا": (33.1347, 35.4444, "Ayta al-Sha'b"),

    "yaroun": (33.1033, 35.4819, "Yaroun"),
    "يارون": (33.1033, 35.4819, "Yaroun"),

    "aitaroun": (33.0964, 35.4153, "Aitaroun"),
    "عيترون": (33.0964, 35.4153, "Aitaroun"),

    "maroun al-ras": (33.0786, 35.4250, "Maroun al-Ras"),
    "مارون الراس": (33.0786, 35.4250, "Maroun al-Ras"),

    "kfar shouba": (33.3764, 35.6914, "Kfar Shouba"),
    "كفرشوبا": (33.3764, 35.6914, "Kfar Shouba"),
    "كفر شوبا": (33.3764, 35.6914, "Kfar Shouba"),

    "tayr harfa": (33.1847, 35.3917, "Tayr Harfa"),
    "طير حرفا": (33.1847, 35.3917, "Tayr Harfa"),

    "houla": (33.0794, 35.5156, "Houla"),
    "حولا": (33.0794, 35.5156, "Houla"),

    "alma al-sha'b": (33.0894, 35.4056, "Alma al-Sha'b"),
    "علما الشعب": (33.0894, 35.4056, "Alma al-Sha'b"),

    "rmeish": (33.0692, 35.4011, "Rmeish"),
    "رميش": (33.0692, 35.4011, "Rmeish"),

    "debl": (33.0889, 35.4678, "Debl"),
    "ديبل": (33.0889, 35.4678, "Debl"),

    "aadeisse": (33.1089, 35.5411, "Aadeisse"),
    "عديسة": (33.1089, 35.5411, "Aadeisse"),

    "kfarhamam": (33.3431, 35.4831, "Kfarhamam"),
    "كفرحمام": (33.3431, 35.4831, "Kfarhamam"),

    "zebqin": (33.2700, 35.3553, "Zebqin"),
    "زبقين": (33.2700, 35.3553, "Zebqin"),

    "kafr tibnit": (33.3167, 35.4583, "Kafr Tibnit"),
    "كفرتبنيت": (33.3167, 35.4583, "Kafr Tibnit"),

    "haris": (33.3036, 35.4781, "Haris"),
    "حاريص": (33.3036, 35.4781, "Haris"),

    "shakra": (33.3297, 35.3644, "Shakra"),
    "شقرا": (33.3297, 35.3644, "Shakra"),

    "tyre district": (33.2705, 35.2037, "Tyre District"),
    "قضاء صور": (33.2705, 35.2037, "Tyre District"),

    "south lebanon": (33.2705, 35.2037, "South Lebanon"),
    "جنوب لبنان": (33.2705, 35.2037, "South Lebanon"),
    "الجنوب اللبناني": (33.2705, 35.2037, "South Lebanon"),
    "جنوبية": (33.2705, 35.2037, "South Lebanon"),

    # ── Lebanon ────────────────────────────────────────────────────────────────
    "beirut": (33.8938, 35.5018, "Beirut"),
    "بيروت": (33.8938, 35.5018, "Beirut"),
    "bekaa": (33.8462, 35.9018, "Bekaa Valley"),
    "البقاع": (33.8462, 35.9018, "Bekaa Valley"),
    "tripoli": (34.4333, 35.8500, "Tripoli"),
    "طرابلس": (34.4333, 35.8500, "Tripoli"),
    "baalbek": (34.0042, 36.2097, "Baalbek"),
    "بعلبك": (34.0042, 36.2097, "Baalbek"),
    "lebanon": (33.8547, 35.8623, "Lebanon"),
    "لبنان": (33.8547, 35.8623, "Lebanon"),
    "zahlé": (33.8500, 35.9017, "Zahlé"),
    "زحلة": (33.8500, 35.9017, "Zahlé"),

    # ── Northern Israel (border area) ──────────────────────────────────────────
    "kiryat shmona": (33.2078, 35.5706, "Kiryat Shmona"),
    "kiryat shemona": (33.2078, 35.5706, "Kiryat Shmona"),
    "קריית שמונה": (33.2078, 35.5706, "Kiryat Shmona"),
    "قريات شمونة": (33.2078, 35.5706, "Kiryat Shmona"),

    "metula": (33.2803, 35.5706, "Metula"),
    "מטולה": (33.2803, 35.5706, "Metula"),
    "مطلة": (33.2803, 35.5706, "Metula"),

    "shlomi": (33.0714, 35.1539, "Shlomi"),
    "שלומי": (33.0714, 35.1539, "Shlomi"),
    "شلومي": (33.0714, 35.1539, "Shlomi"),

    "nahariya": (33.0064, 35.0972, "Nahariya"),
    "נהריה": (33.0064, 35.0972, "Nahariya"),
    "نهاريا": (33.0064, 35.0972, "Nahariya"),

    "acre": (32.9228, 35.0681, "Akko"),
    "akko": (32.9228, 35.0681, "Akko"),
    "עכו": (32.9228, 35.0681, "Akko"),
    "عكا": (32.9228, 35.0681, "Akko"),

    "safed": (32.9646, 35.4969, "Safed"),
    "צפת": (32.9646, 35.4969, "Safed"),
    "صفد": (32.9646, 35.4969, "Safed"),

    "avivim": (33.1361, 35.4347, "Avivim"),
    "אביבים": (33.1361, 35.4347, "Avivim"),
    "أبيبيم": (33.1361, 35.4347, "Avivim"),

    "manara": (33.2308, 35.5622, "Manara"),
    "מנרה": (33.2308, 35.5622, "Manara"),
    "منارة": (33.2308, 35.5622, "Manara"),

    "golan": (33.0, 35.75, "Golan Heights"),
    "الجولان": (33.0, 35.75, "Golan Heights"),
    "הגולן": (33.0, 35.75, "Golan Heights"),

    # ── Gaza ──────────────────────────────────────────────────────────────────
    "gaza": (31.5017, 34.4668, "Gaza"),
    "غزة": (31.5017, 34.4668, "Gaza"),
    "gaza city": (31.5017, 34.4668, "Gaza City"),
    "مدينة غزة": (31.5017, 34.4668, "Gaza City"),
    "north gaza": (31.5500, 34.5000, "North Gaza"),
    "شمال غزة": (31.5500, 34.5000, "North Gaza"),
    "rafah": (31.2947, 34.2474, "Rafah"),
    "رفح": (31.2947, 34.2474, "Rafah"),
    "khan yunis": (31.3453, 34.3062, "Khan Yunis"),
    "خان يونس": (31.3453, 34.3062, "Khan Yunis"),
    "deir al-balah": (31.4228, 34.3519, "Deir al-Balah"),
    "دير البلح": (31.4228, 34.3519, "Deir al-Balah"),
    "beit lahia": (31.5547, 34.4900, "Beit Lahia"),
    "بيت لاهيا": (31.5547, 34.4900, "Beit Lahia"),
    "jabaliya": (31.5344, 34.4831, "Jabalia"),
    "جباليا": (31.5344, 34.4831, "Jabalia"),
    "beit hanoun": (31.5358, 34.5247, "Beit Hanoun"),
    "بيت حانون": (31.5358, 34.5247, "Beit Hanoun"),

    # ── West Bank ──────────────────────────────────────────────────────────────
    "jerusalem": (31.7683, 35.2137, "Jerusalem"),
    "القدس": (31.7683, 35.2137, "Jerusalem"),
    "west bank": (31.9522, 35.2332, "West Bank"),
    "الضفة الغربية": (31.9522, 35.2332, "West Bank"),
    "الضفة": (31.9522, 35.2332, "West Bank"),
    "ramallah": (31.9038, 35.2034, "Ramallah"),
    "رام الله": (31.9038, 35.2034, "Ramallah"),
    "nablus": (32.2211, 35.2544, "Nablus"),
    "نابلس": (32.2211, 35.2544, "Nablus"),
    "hebron": (31.5326, 35.0998, "Hebron"),
    "الخليل": (31.5326, 35.0998, "Hebron"),
    "jenin": (32.4667, 35.2999, "Jenin"),
    "جنين": (32.4667, 35.2999, "Jenin"),
    "tulkarm": (32.3116, 35.0286, "Tulkarm"),
    "طولكرم": (32.3116, 35.0286, "Tulkarm"),
    "jericho": (31.8557, 35.4638, "Jericho"),
    "أريحا": (31.8557, 35.4638, "Jericho"),
    "bethlehem": (31.7054, 35.2024, "Bethlehem"),
    "بيت لحم": (31.7054, 35.2024, "Bethlehem"),
    "qalqilya": (32.1886, 34.9700, "Qalqilya"),
    "قلقيلية": (32.1886, 34.9700, "Qalqilya"),

    # ── Israel ────────────────────────────────────────────────────────────────
    "israel": (31.0461, 34.8516, "Israel"),
    "إسرائيل": (31.0461, 34.8516, "Israel"),
    "tel aviv": (32.0853, 34.7818, "Tel Aviv"),
    "تل أبيب": (32.0853, 34.7818, "Tel Aviv"),
    "haifa": (32.7940, 34.9896, "Haifa"),
    "حيفا": (32.7940, 34.9896, "Haifa"),

    # ── Syria ────────────────────────────────────────────────────────────────
    "syria": (34.8021, 38.9968, "Syria"),
    "سوريا": (34.8021, 38.9968, "Syria"),
    "damascus": (33.5138, 36.2765, "Damascus"),
    "دمشق": (33.5138, 36.2765, "Damascus"),
    "aleppo": (36.2021, 37.1343, "Aleppo"),
    "حلب": (36.2021, 37.1343, "Aleppo"),

    # ── Jordan ───────────────────────────────────────────────────────────────
    "jordan": (31.9566, 35.9457, "Jordan"),
    "الأردن": (31.9566, 35.9457, "Jordan"),
    "amman": (31.9539, 35.9106, "Amman"),
    "عمّان": (31.9539, 35.9106, "Amman"),

    # ── Egypt ────────────────────────────────────────────────────────────────
    "egypt": (26.8206, 30.8025, "Egypt"),
    "مصر": (26.8206, 30.8025, "Egypt"),
    "cairo": (30.0444, 31.2357, "Cairo"),
    "القاهرة": (30.0444, 31.2357, "Cairo"),
    "sinai": (29.5, 34.0, "Sinai"),
    "سيناء": (29.5, 34.0, "Sinai"),
    "rafah crossing": (31.2810, 34.2200, "Rafah Crossing"),
    "معبر رفح": (31.2810, 34.2200, "Rafah Crossing"),

    # ── Yemen ────────────────────────────────────────────────────────────────
    "yemen": (15.5527, 48.5164, "Yemen"),
    "اليمن": (15.5527, 48.5164, "Yemen"),
    "sanaa": (15.3694, 44.191, "Sanaa"),
    "صنعاء": (15.3694, 44.191, "Sanaa"),
    "hodeidah": (14.7979, 42.9539, "Hodeidah"),
    "الحديدة": (14.7979, 42.9539, "Hodeidah"),

    # ── Iraq ─────────────────────────────────────────────────────────────────
    "iraq": (33.2232, 43.6793, "Iraq"),
    "العراق": (33.2232, 43.6793, "Iraq"),
    "baghdad": (33.3152, 44.3661, "Baghdad"),
    "بغداد": (33.3152, 44.3661, "Baghdad"),

    # ── Iran ─────────────────────────────────────────────────────────────────
    "iran": (32.4279, 53.6880, "Iran"),
    "إيران": (32.4279, 53.6880, "Iran"),
    "tehran": (35.6892, 51.3890, "Tehran"),
    "طهران": (35.6892, 51.3890, "Tehran"),
}


def extract_location(text: str) -> tuple[Optional[str], Optional[float], Optional[float]]:
    """
    Extract the most specific known location from text.
    Tries longer/more specific keys first to prefer precise matches.
    """
    text_lower = text.lower()

    # Sort keys by length descending so longer (more specific) names match first
    sorted_keys = sorted(KNOWN_LOCATIONS.keys(), key=len, reverse=True)

    for key in sorted_keys:
        # Try both case-insensitive ASCII and direct unicode match
        if key in text_lower or key in text:
            lat, lng, display = KNOWN_LOCATIONS[key]
            return display, lat, lng

    return None, None, None


def geocode_location(location_name: str) -> tuple[Optional[float], Optional[float]]:
    if not location_name:
        return None, None
    loc_lower = location_name.lower().strip()
    sorted_keys = sorted(KNOWN_LOCATIONS.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in loc_lower or loc_lower in key:
            lat, lng, _ = KNOWN_LOCATIONS[key]
            return lat, lng
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError

        geocoder = Nominatim(user_agent="osint-platform/1.0")
        time.sleep(1.1)
        loc = geocoder.geocode(location_name, timeout=5)
        if loc:
            return loc.latitude, loc.longitude
    except Exception as e:
        logger.warning(f"Geocoding failed for '{location_name}': {e}")
    return None, None
