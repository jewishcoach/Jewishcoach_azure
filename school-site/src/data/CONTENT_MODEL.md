# מודל תוכן — אתר בית הספר

## בסיס (חומרים חדשים — PDFים)

הטקסטים, המסרים והמסלולים באתר נשענים על הדפים שהוכנו מחדש:

| עמוד | מקור |
|------|------|
| `/` | דף הבית לאפליקציה.pdf |
| `/programs/personal` | דף מסלול אישי |
| `/programs/find-coach` | מסלול אימון אישי |
| `/programs/certified-coaches` | מסלול השלמה למאמנים |
| `/book` | דף הספר |
| `/contact` | דף צור קשר |
| `/try-ai` | תכנון מוצר (לא מהישן) |

**לא** מחליפים טקסטים אלה בתוכן מהאתר הישן.

## השלמה (רק מה שחסר בחדש) — `קובץאתרישן.xml`

| עמוד | מקור ישן | הערה |
|------|----------|------|
| `/insights` | פוסטים (מאמרים) | 24 מאמרים |
| `/testimonials` | המלצות + עיתונות | לא ב-PDFים החדשים |
| `/about` | טקסט קצר חדש + קישור ל-`/legacy` | ביוגרפיה מלאה ב-zיכרון |

## לא משחזרים מהישן (כי יש בחדש או מיושן)

- אימון אישי (עמוד WP) → יש `/programs/personal` + `/find-coach`
- קורס בסיסי / השתלמויות → עד שייכנסו ל-PDFים החדשים
- טלפונים ותאריכי קורס 2017

## After re-extracting from WordPress XML, mirror media locally (while old site is still up):
#   python3 scripts/mirror_legacy_media.py
# Full archive from XML (optional): python3 scripts/mirror_legacy_media.py --all-xml
