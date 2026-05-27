import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Pre-seeded known Middle East locations (name_lower -> (lat, lng, display_name))
KNOWN_LOCATIONS: dict[str, tuple[float, float, str]] = {
    "gaza": (31.5017, 34.4668, "Gaza"),
    "غزة": (31.5017, 34.4668, "Gaza"),
    "rafah": (31.2947, 34.2474, "Rafah"),
    "رفح": (31.2947, 34.2474, "Rafah"),
    "khan yunis": (31.3453, 34.3062, "Khan Yunis"),
    "خان يونس": (31.3453, 34.3062, "Khan Yunis"),
    "jerusalem": (31.7683, 35.2137, "Jerusalem"),
    "القدس": (31.7683, 35.2137, "Jerusalem"),
    "west bank": (31.9522, 35.2332, "West Bank"),
    "الضفة الغربية": (31.9522, 35.2332, "West Bank"),
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
    "beirut": (33.8938, 35.5018, "Beirut"),
    "بيروت": (33.8938, 35.5018, "Beirut"),
    "lebanon": (33.8547, 35.8623, "Lebanon"),
    "لبنان": (33.8547, 35.8623, "Lebanon"),
    "south lebanon": (33.2705, 35.2037, "South Lebanon"),
    "جنوب لبنان": (33.2705, 35.2037, "South Lebanon"),
    "syria": (34.8021, 38.9968, "Syria"),
    "سوريا": (34.8021, 38.9968, "Syria"),
    "damascus": (33.5138, 36.2765, "Damascus"),
    "دمشق": (33.5138, 36.2765, "Damascus"),
    "aleppo": (36.2021, 37.1343, "Aleppo"),
    "حلب": (36.2021, 37.1343, "Aleppo"),
    "jordan": (31.9566, 35.9457, "Jordan"),
    "الأردن": (31.9566, 35.9457, "Jordan"),
    "amman": (31.9539, 35.9106, "Amman"),
    "عمّان": (31.9539, 35.9106, "Amman"),
    "egypt": (26.8206, 30.8025, "Egypt"),
    "مصر": (26.8206, 30.8025, "Egypt"),
    "cairo": (30.0444, 31.2357, "Cairo"),
    "القاهرة": (30.0444, 31.2357, "Cairo"),
    "sinai": (29.5, 34.0, "Sinai"),
    "سيناء": (29.5, 34.0, "Sinai"),
    "yemen": (15.5527, 48.5164, "Yemen"),
    "اليمن": (15.5527, 48.5164, "Yemen"),
    "sanaa": (15.3694, 44.191, "Sanaa"),
    "صنعاء": (15.3694, 44.191, "Sanaa"),
    "iraq": (33.2232, 43.6793, "Iraq"),
    "العراق": (33.2232, 43.6793, "Iraq"),
    "baghdad": (33.3152, 44.3661, "Baghdad"),
    "بغداد": (33.3152, 44.3661, "Baghdad"),
    "israel": (31.0461, 34.8516, "Israel"),
    "إسرائيل": (31.0461, 34.8516, "Israel"),
    "tel aviv": (32.0853, 34.7818, "Tel Aviv"),
    "تل أبيب": (32.0853, 34.7818, "Tel Aviv"),
    "haifa": (32.7940, 34.9896, "Haifa"),
    "حيفا": (32.7940, 34.9896, "Haifa"),
    "iran": (32.4279, 53.6880, "Iran"),
    "إيران": (32.4279, 53.6880, "Iran"),
    "tehran": (35.6892, 51.3890, "Tehran"),
    "طهران": (35.6892, 51.3890, "Tehran"),
}


def extract_location(text: str) -> tuple[Optional[str], Optional[float], Optional[float]]:
    text_lower = text.lower()
    for key, (lat, lng, display) in KNOWN_LOCATIONS.items():
        if key in text_lower or key in text:
            return display, lat, lng
    return None, None, None


def geocode_location(location_name: str) -> tuple[Optional[float], Optional[float]]:
    if not location_name:
        return None, None
    loc_lower = location_name.lower().strip()
    for key, (lat, lng, _) in KNOWN_LOCATIONS.items():
        if key in loc_lower or loc_lower in key:
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
