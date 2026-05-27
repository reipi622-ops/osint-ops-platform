import logging
from datetime import datetime, timedelta
import random
from app.database import SessionLocal
from app import models
from app.services.deduplicator import compute_hash

logger = logging.getLogger(__name__)

SAMPLE_EVENTS = [
    {
        "title": "هجوم صاروخي على منطقة حدودية في الجنوب",
        "title_he": "התקפת טילים באזור הגבול בדרום",
        "description": "أفادت مصادر ميدانية بوقوع هجوم صاروخي استهدف منطقة حدودية في جنوب لبنان.",
        "description_he": "מקורות שטח דיווחו על התקפת טילים שכוונה לאזור הגבול בדרום לבנון.",
        "category": "military",
        "confidence": 0.89,
        "source_name": "Al Jazeera Arabic",
        "location_name": "South Lebanon",
        "lat": 33.2705,
        "lng": 35.2037,
        "original_lang": "ar",
        "days_ago": 0,
    },
    {
        "title": "مظاهرات أمام البرلمان تطالب بوقف إطلاق النار",
        "title_he": "הפגנות מול הפרלמנט הקוראות להפסקת אש",
        "description": "خرج مئات المتظاهرين أمام البرلمان مطالبين بوقف فوري لإطلاق النار.",
        "description_he": "מאות מפגינים יצאו מול הפרלמנט וקראו להפסקת אש מיידית.",
        "category": "political",
        "confidence": 0.85,
        "source_name": "BBC Arabic",
        "location_name": "Beirut",
        "lat": 33.8938,
        "lng": 35.5018,
        "original_lang": "ar",
        "days_ago": 0,
    },
    {
        "title": "وصول قافلة مساعدات إنسانية إلى غزة",
        "title_he": "שיירת סיוע הומניטארית הגיעה לעזה",
        "description": "وصلت قافلة مساعدات إنسانية تحمل أدوية وغذاء إلى قطاع غزة.",
        "description_he": "שיירת סיוע הומניטארית נושאת תרופות ומזון הגיעה לרצועת עזה.",
        "category": "humanitarian",
        "confidence": 0.91,
        "source_name": "Reuters World",
        "location_name": "Gaza",
        "lat": 31.5017,
        "lng": 34.4668,
        "original_lang": "ar",
        "days_ago": 1,
    },
    {
        "title": "غارات جوية تستهدف مواقع في شمال غزة",
        "title_he": "תקיפות אוויריות פוגעות באתרים בצפון עזה",
        "description": "شنّت طائرات حربية غارات على عدة مواقع في شمال قطاع غزة.",
        "description_he": "מטוסי קרב תקפו מספר אתרים בצפון רצועת עזה.",
        "category": "military",
        "confidence": 0.93,
        "source_name": "Al Jazeera Arabic",
        "location_name": "Gaza",
        "lat": 31.5017,
        "lng": 34.4668,
        "original_lang": "ar",
        "days_ago": 1,
    },
    {
        "title": "اجتماع طارئ لمجلس الأمن بشأن الأوضاع في المنطقة",
        "title_he": "ישיבת חירום של מועצת הביטחון בנוגע למצב באזור",
        "description": "عقد مجلس الأمن الدولي اجتماعاً طارئاً لمناقشة التطورات الأخيرة.",
        "description_he": "מועצת הביטחון הבינלאומית קיימה ישיבת חירום לדיון בהתפתחויות האחרונות.",
        "category": "political",
        "confidence": 0.87,
        "source_name": "Reuters World",
        "location_name": "Jerusalem",
        "lat": 31.7683,
        "lng": 35.2137,
        "original_lang": "ar",
        "days_ago": 2,
    },
    {
        "title": "إصابات في صفوف المدنيين جراء القصف في رفح",
        "title_he": "נפגעים אזרחיים כתוצאה מהפצצה ברפיח",
        "description": "أعلنت مصادر طبية عن سقوط عدد من المصابين في صفوف المدنيين جراء القصف.",
        "description_he": "מקורות רפואיים הודיעו על נפגעים בקרב אזרחים כתוצאה מהפצצה.",
        "category": "humanitarian",
        "confidence": 0.88,
        "source_name": "Al Jazeera Arabic",
        "location_name": "Rafah",
        "lat": 31.2947,
        "lng": 34.2474,
        "original_lang": "ar",
        "days_ago": 2,
    },
    {
        "title": "قوات الاحتلال تشن عملية في مخيم جنين",
        "title_he": "כוחות הכיבוש מבצעים מבצע במחנה הפליטים ג'נין",
        "description": "شنّت قوات الاحتلال عملية عسكرية في مخيم جنين للاجئين.",
        "description_he": "כוחות הכיבוש ביצעו מבצע צבאי במחנה הפליטים ג'נין.",
        "category": "military",
        "confidence": 0.90,
        "source_name": "Al Jazeera Arabic",
        "location_name": "Jenin",
        "lat": 32.4667,
        "lng": 35.2999,
        "original_lang": "ar",
        "days_ago": 3,
    },
    {
        "title": "الحوثيون يعلنون استهداف سفينة في البحر الأحمر",
        "title_he": "החות'ים מכריזים על תקיפת ספינה בים האדום",
        "description": "أعلن الحوثيون في اليمن استهداف سفينة شحن في البحر الأحمر.",
        "description_he": "החות'ים בתימן הכריזו על תקיפת ספינת מטען בים האדום.",
        "category": "military",
        "confidence": 0.86,
        "source_name": "Reuters World",
        "location_name": "Yemen",
        "lat": 15.5527,
        "lng": 48.5164,
        "original_lang": "ar",
        "days_ago": 3,
    },
    {
        "title": "مفاوضات وقف إطلاق النار تستأنف في القاهرة",
        "title_he": "משא ומתן על הפסקת אש מתחדש בקהיר",
        "description": "استُؤنفت المفاوضات المتعلقة بوقف إطلاق النار في غزة برعاية مصرية.",
        "description_he": "משא ומתן בנוגע להפסקת האש בעזה התחדש בחסות מצרים.",
        "category": "political",
        "confidence": 0.84,
        "source_name": "BBC Arabic",
        "location_name": "Cairo",
        "lat": 30.0444,
        "lng": 31.2357,
        "original_lang": "ar",
        "days_ago": 4,
    },
    {
        "title": "توزيع مساعدات غذائية على النازحين في خان يونس",
        "title_he": "חלוקת סיוע מזון לעקורים בח'אן יונס",
        "description": "قامت منظمات إنسانية بتوزيع مساعدات غذائية طارئة على النازحين.",
        "description_he": "ארגונים הומניטריים חילקו סיוע מזון חירום לעקורים.",
        "category": "humanitarian",
        "confidence": 0.92,
        "source_name": "Reuters World",
        "location_name": "Khan Yunis",
        "lat": 31.3453,
        "lng": 34.3062,
        "original_lang": "ar",
        "days_ago": 4,
    },
    {
        "title": "قصف يطال منازل في نابلس بالضفة الغربية",
        "title_he": "הפצצה פוגעת בבתים בשכם בגדה המערבית",
        "description": "تعرضت منازل في مدينة نابلس لقصف خلّف أضراراً مادية جسيمة.",
        "description_he": "בתים בעיר שכם הופצצו וספגו נזקים חומריים כבדים.",
        "category": "military",
        "confidence": 0.87,
        "source_name": "Al Jazeera Arabic",
        "location_name": "Nablus",
        "lat": 32.2211,
        "lng": 35.2544,
        "original_lang": "ar",
        "days_ago": 5,
    },
    {
        "title": "دمار واسع يطال البنية التحتية في رفح",
        "title_he": "הרס נרחב פוגע בתשתיות ברפיח",
        "description": "خلّفت العمليات العسكرية دماراً واسعاً في البنية التحتية بمدينة رفح.",
        "description_he": "הפעולות הצבאיות גרמו להרס נרחב בתשתיות העיר רפיח.",
        "category": "humanitarian",
        "confidence": 0.89,
        "source_name": "BBC Arabic",
        "location_name": "Rafah",
        "lat": 31.2947,
        "lng": 34.2474,
        "original_lang": "ar",
        "days_ago": 5,
    },
    {
        "title": "Israeli forces conduct operation in Tulkarm camp",
        "title_he": "כוחות ישראליים מבצעים מבצע במחנה טול כרם",
        "description": "Israeli military forces conducted an overnight operation in the Tulkarm refugee camp.",
        "description_he": "כוחות הצבא הישראלי ביצעו מבצע לילי במחנה הפליטים בטול כרם.",
        "category": "military",
        "confidence": 0.88,
        "source_name": "Times of Israel",
        "location_name": "Tulkarm",
        "lat": 32.3116,
        "lng": 35.0286,
        "original_lang": "en",
        "days_ago": 6,
    },
    {
        "title": "Aid convoy reaches northern Gaza after weeks of blockade",
        "title_he": "שיירת סיוע מגיעה לצפון עזה לאחר שבועות של מצור",
        "description": "A humanitarian aid convoy managed to deliver essential supplies to northern Gaza.",
        "description_he": "שיירת סיוע הומניטארי הצליחה לספק אספקה חיונית לצפון עזה.",
        "category": "humanitarian",
        "confidence": 0.90,
        "source_name": "Times of Israel",
        "location_name": "Gaza",
        "lat": 31.5017,
        "lng": 34.4668,
        "original_lang": "en",
        "days_ago": 6,
    },
    {
        "title": "اشتباكات في الخليل بين قوات الأمن والمسلحين",
        "title_he": "עימותים בחברון בין כוחות הביטחון לחמושים",
        "description": "اندلعت اشتباكات مسلحة في مدينة الخليل بين قوات الأمن الفلسطينية ومسلحين.",
        "description_he": "פרצו עימותים חמושים בעיר חברון בין כוחות הביטחון הפלסטיניים לחמושים.",
        "category": "military",
        "confidence": 0.86,
        "source_name": "Al Jazeera Arabic",
        "location_name": "Hebron",
        "lat": 31.5326,
        "lng": 35.0998,
        "original_lang": "ar",
        "days_ago": 7,
    },
]


def seed_sample_events() -> None:
    db = SessionLocal()
    try:
        if db.query(models.Event).count() > 0:
            return

        now = datetime.utcnow()
        source = db.query(models.Source).first()

        for item in SAMPLE_EVENTS:
            days_ago = item.pop("days_ago", 0)
            ts = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            event_hash = compute_hash(item["title"], item.get("description", ""))

            if db.query(models.Event).filter(models.Event.event_hash == event_hash).first():
                item["days_ago"] = days_ago  # restore
                continue

            event = models.Event(
                **{k: v for k, v in item.items()},
                event_hash=event_hash,
                is_duplicate=False,
                source_id=source.id if source else None,
                scraped_at=ts,
                created_at=ts,
                event_date=ts,
            )
            db.add(event)
            item["days_ago"] = days_ago  # restore for idempotency

        db.commit()
        logger.info("Seeded %d sample events", db.query(models.Event).count())
    except Exception as e:
        db.rollback()
        logger.error("Seed failed: %s", e)
    finally:
        db.close()
