# 📡 Multi-Channel Publisher

**פרסום אוטומטי לאינסטגרם, פייסבוק, Google Business Profile ו-LinkedIn — מטבלת Google Sheets אחת.**

הרחבה של פרויקט **Social Publisher** המקורי: אותה ארכיטקטורה (Render + Sheets + Drive + Cloudinary), אבל עם **Channel Registry** מודולרי שמאפשר להוסיף ערוצים חדשים בלי לשנות את הליבה — ושני ערוצים חדשים שכבר נוספו: **Google Business Profile** ו-**LinkedIn**.

---

## ✨ מה חדש לעומת Social Publisher

| | Social Publisher (הישן) | Multi-Channel Publisher (הנוכחי) |
|---|---|---|
| ערוצי פרסום | IG + FB | IG + FB + **GBP** + **LinkedIn** |
| בחירת ערוצים | קבועה לפי `network=IG/FB` | שילובים חופשיים: `IG+FB+GBP+LI`, `ALL`, וכו' |
| ארכיטקטורה | פרסום מקודד ישירות ב-`main.py` | `channels/` + `ChannelRegistry` — הוספת ערוץ = קובץ אחד |
| סטטוס | `POSTED` / `ERROR` בלבד | `POSTED` / `PARTIAL` / `ERROR` — הצלחה חלקית מתועדת לכל ערוץ |
| נעילה | `IN_PROGRESS` | `PROCESSING` + `locked_at` + `processing_by` + timeout |
| Retry | פר-פוסט | **פר-ערוץ** עם סיווג שגיאות (retryable/non-retryable) |
| קבצי caption | `caption_ig`, `caption_fb` | + `caption`, `caption_gbp`, `caption_li` (עם fallback) |

> פירוט אפיון מלא: [`SPEC-multi-channel-publisher.md`](./SPEC-multi-channel-publisher.md).

---

## 🏗️ ארכיטקטורה

```
Render Cron Job (כל 5 דקות, UTC)        Render Web Service (Flask Panel)
        │                                            │
        ▼                                            ▼
     main.py ◄──── Google Sheets API ──────────► web_app.py
        │              (תור פוסטים)                  │
        │                                            │
        ├── Google Drive API ── הורדת מדיה (bytes)
        │
        ├── Cloudinary ─────── העלאה → URL ציבורי
        │
        ▼
  channels/registry.py  ◄── ChannelRegistry: validate_channels + publish_to_channels
        │
        ├── channels/meta_instagram.py     ── Meta Graph API (/media → /media_publish)
        ├── channels/meta_facebook.py      ── Meta Graph API (/photos, /videos)
        ├── channels/google_business.py    ── Google Business Profile API (localPosts)
        └── channels/linkedin.py           ── LinkedIn Community Management API (/rest/posts)
        │
        ▼
  Google Sheets API ── עדכון status / result / published_channels / failed_channels
```

### עיקרון מנחה
> **הוספת ערוץ חדש = קובץ Python חדש ב-`channels/` + רישום ב-`create_default_registry()`.**
> אין צורך לגעת ב-`main.py`, ב-UI או במבנה הטבלה (מלבד הוספת עמודת `caption_<channel>` אופציונלית).

---

## 📡 ערוצי פרסום

| ערוץ | `CHANNEL_ID` | API | מדיה נתמכת | סוגי פוסט | Feature Flag |
|------|--------------|-----|------------|-----------|--------------|
| Instagram | `IG` | Meta Graph API v21.0 | תמונה, וידאו (Reels), Carousel | `FEED`, `REELS` | תמיד מופעל |
| Facebook Page | `FB` | Meta Graph API v21.0 | תמונה, וידאו | `FEED`, `REELS` | תמיד מופעל |
| Google Business Profile | `GBP` | GBP API v4 (`localPosts`) | תמונה / טקסט בלבד | `STANDARD` (MVP) | `GBP_ENABLED=true` |
| LinkedIn | `LI` | LinkedIn REST `/rest/posts` | תמונה, וידאו, טקסט בלבד | `FEED` | `LI_ENABLED=true` |

**GBP** ו-**LinkedIn** מוגנים מאחורי feature flags — כבויים כברירת מחדל. הפעלה דורשת OAuth 2.0 (`refresh_token`) ולא Service Account.

---

## 📋 מבנה הטבלה (Google Sheets)

| עמודה | דוגמה | הסבר |
|---|---|---|
| `id` | 42 | מספר ייחודי |
| `status` | READY | `DRAFT` / `READY` / `PROCESSING` / `POSTED` / `PARTIAL` / `ERROR` |
| `network` | `IG+FB+GBP+LI` | ערוצי יעד — שילובים חופשיים או `ALL` |
| `post_type` | FEED | `FEED` / `REELS` / `TEXT` |
| `publish_at` | 2026-06-22 14:30 | שעון ישראל |
| `caption` | טקסט ברירת מחדל | fallback אחיד לכל ערוץ |
| `caption_ig` | טקסט לאינסטגרם | אופציונלי — דורס את `caption` |
| `caption_fb` | טקסט לפייסבוק | אופציונלי |
| `caption_gbp` | טקסט ל-GBP | אופציונלי. עד 1,500 תווים |
| `caption_li` | טקסט ל-LinkedIn | אופציונלי. עד 3,000 תווים |
| `li_author_urn` | `urn:li:person:ABC123` | חובה ל-LI אם אין `LI_AUTHOR_URN` ב-env |
| `gbp_post_type` | `STANDARD` | רק `STANDARD` נתמך ב-MVP |
| `cta_type` | `LEARN_MORE` | `LEARN_MORE` / `CALL` / `BOOK` (GBP) |
| `cta_url` | `https://...` | חובה אם יש `cta_type` |
| `google_location_id` | `locations/987654321` | חובה ל-GBP. ברמת שורה → מאפשר multi-location |
| `drive_file_id` | `1AbCdEf...` | מזהה Drive או URL ציבורי |
| `cover_drive_file_id` | `1XyZ...` | תמונת כיסוי ל-Reels (אופציונלי) |
| `cloudinary_url` | _(ימולא אוטומטית)_ | |
| `hashtags` | `#tag1 #tag2` | מצורף ל-first comment ב-IG, ל-caption ב-GBP/LI |
| `first_comment` | טקסט תגובה | תגובה אוטומטית אחרי הפרסום (IG/FB) |
| `source` | `ai-panel` | `manual` / `auto` / `ai-panel` |
| `result` | `IG:POSTED:1784... \| FB:POSTED:6152... \| GBP:ERROR:quota_exceeded` | תוצאה מפורטת פר-ערוץ |
| `published_channels` | `IG,FB` | ערוצים שהצליחו |
| `failed_channels` | `GBP` | ערוצים שנכשלו |
| `retry_count` | `0` | מספר ניסיונות חוזרים |
| `locked_at` | `2026-06-22T11:30:05Z` | זמן נעילה (UTC) |
| `processing_by` | `run_abc123def456` | מזהה ה-cron run שנעל |
| `error` | _(ימולא אוטומטית)_ | הודעת שגיאה מצרפית |

> מבנה מלא: `SHEET_COLUMNS` ב-[`config_constants.py`](./config_constants.py).

### לוגיקת fallback לכיתובים
1. אם יש `caption_<channel>` (למשל `caption_gbp`) → משתמשים בו
2. אחרת אם יש `caption` כללי → משתמשים בו
3. אחרת → validation error לפני הפרסום (הפוסט לא יוצא)

---

## 🚀 הגדרה ב-Render

המערכת רצה כשני שירותים ב-Render (Blueprint ב-[`render.yaml`](./render.yaml)):

1. **Web Service** (`social-publisher-panel`) — פאנל ניהול (Flask + Gunicorn)
2. **Cron Job** (`social-publisher`) — מריץ `python main.py` כל 5 דקות

**Region:** Frankfurt (הכי קרוב לישראל)
**Build:** Docker (`Dockerfile.web` לפאנל, `Dockerfile` ל-cron)

### Feature Flags
```env
GBP_ENABLED=true   # להפעלת Google Business Profile
LI_ENABLED=true    # להפעלת LinkedIn
```
ברירת מחדל: כבויים. ערוץ כבוי לא נטען ל-registry, ושורות עם `network=GBP` יסומנו כ-`ERROR` עם הודעה ברורה.

### הגדרה מלאה ללקוח חדש
ראה [`CLIENT_SETUP.md`](./CLIENT_SETUP.md) — צ׳קליסט עם כל החשבונות, ה-APIs, ה-OAuth וה-env vars לכל ערוץ.

---

## 🔑 משתני סביבה — סיכום

### תמיד נדרשים
- `GOOGLE_SERVICE_ACCOUNT_JSON` — JSON מלא של ה-SA (קריאה מ-Sheets + Drive)
- `SPREADSHEET_ID`, `SHEET_NAME`, `GOOGLE_DRIVE_FOLDER_ID`
- `CLOUDINARY_URL` (או `CLOUDINARY_CLOUD_NAME` + `CLOUDINARY_API_KEY` + `CLOUDINARY_API_SECRET`)
- `WEB_PANEL_SECRET` (להזדהות לפאנל)
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (להתראות)

### Meta (IG + FB)
- `META_API_VERSION` (ברירת מחדל `v21.0`)
- `IG_USER_ID`, `IG_ACCESS_TOKEN`
- `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`

### Google Business Profile (אופציונלי — אם `GBP_ENABLED=true`)
- `GBP_ACCOUNT_ID` — למשל `accounts/123456789`
- `GBP_DEFAULT_LOCATION_ID` — fallback אם השורה לא מספקת `google_location_id`
- `GBP_OAUTH_CLIENT_ID`, `GBP_OAUTH_CLIENT_SECRET`, `GBP_REFRESH_TOKEN`

### LinkedIn (אופציונלי — אם `LI_ENABLED=true`)
- `LI_OAUTH_CLIENT_ID`, `LI_OAUTH_CLIENT_SECRET`, `LI_REFRESH_TOKEN`
- `LI_AUTHOR_URN` — fallback אם השורה לא מספקת `li_author_urn`

---

## 📁 מבנה הפרויקט

```
multi-channel-publisher/
├── main.py                       # Cron entrypoint
├── web_app.py                    # Flask panel
├── config.py / config_constants.py
├── google_api.py                 # Sheets + Drive helpers
├── cloud_storage.py              # Cloudinary upload
├── media_processor.py            # Pillow normalization (image/video/cover)
├── meta_publish.py               # Meta Graph API helpers (משותף ל-IG/FB)
├── validator.py                  # RowValidator לפני publish
├── notifications.py              # Telegram alerts
├── publish_logger.py             # מובנה: correlation_id + structured logs
├── rss_probe.py
├── channels/
│   ├── __init__.py               # create_default_registry()
│   ├── base.py                   # BaseChannel + PublishResult
│   ├── registry.py               # ChannelRegistry
│   ├── meta_instagram.py         # IG channel
│   ├── meta_facebook.py          # FB channel
│   ├── google_business.py        # GBP channel
│   ├── google_auth.py            # GBP OAuth manager
│   ├── google_locations.py       # multi-location helpers
│   ├── linkedin.py               # LinkedIn channel
│   └── linkedin_auth.py          # LinkedIn OAuth manager
├── templates/index.html          # פאנל ניהול
├── static/                       # app.js + style.css
├── tests/
├── scripts/
├── render.yaml                   # Render Blueprint (web + cron)
├── Dockerfile / Dockerfile.web
├── requirements.txt
├── CLIENT_SETUP.md               # הגדרה ללקוח חדש (מלא)
├── SPEC-multi-channel-publisher.md
└── DEPLOYMENT_CHECKLIST.md
```

---

## 🔧 הרצה מקומית

```bash
# התקנת תלויות
pip install -r requirements.txt

# הגדרת env vars (אפשר עם python-dotenv + .env)
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
export SPREADSHEET_ID='...'
# ... שאר המשתנים (ראה למעלה)

# הרצת ה-cron פעם אחת (לבדיקה)
python main.py

# הרצת הפאנל מקומית
python web_app.py
# או: gunicorn web_app:app
```

הרצת הטסטים:
```bash
pytest tests/ -v
```

---

## ⚠️ נקודות חשובות

- **Timezone:** הטבלה בשעון ישראל, הקוד ממיר ל-UTC אוטומטית.
- **נעילה:** לפני פרסום סטטוס משתנה ל-`PROCESSING` + `locked_at` + `processing_by` → re-read לאימות. timeout משחרר שורות תקועות אחרי `LOCK_TIMEOUT_MINUTES` (ברירת מחדל 10) ומחזיר ל-`READY`.
- **Cloudinary חובה:** IG דורש URL ציבורי (לא Drive link). הקבצים פגי-תוקף אחרי `CLOUDINARY_RETENTION_DAYS` ימים.
- **זיהוי סוג קובץ:** אוטומטי לפי MIME מ-Drive — אין עמודה נפרדת.
- **PARTIAL:** אם חלק מהערוצים הצליחו וחלק נכשלו → `status=PARTIAL`, ה-`published_channels` וה-`failed_channels` מתעדכנים. retry ידני מהפאנל יפעל **רק על הערוצים שנכשלו** (לא יפרסם פעמיים).
- **GBP — תמיכה מוגבלת:** רק `STANDARD` ב-MVP. אין וידאו. multi-location דרך `google_location_id` ברמת שורה.
- **LinkedIn — Author URN חובה:** `urn:li:person:{id}` לפרופיל אישי או `urn:li:organization:{id}` לעמוד חברה. נקבע ברמת שורה (`li_author_urn`) או כברירת מחדל ב-env.
- **מגבלות API:** IG עד 100 פוסטים ב-24h; LinkedIn caption עד 3,000 תווים; GBP עד 1,500 תווים.

---

## 📚 קריאה נוספת

- [`SPEC-multi-channel-publisher.md`](./SPEC-multi-channel-publisher.md) — מסמך אפיון מלא + Technical Tasks
- [`CLIENT_SETUP.md`](./CLIENT_SETUP.md) — צ׳קליסט הגדרה ללקוח חדש (OAuth, APIs, env vars)
- [`DEPLOYMENT_CHECKLIST.md`](./DEPLOYMENT_CHECKLIST.md) — בדיקות לפני עלייה לפרודקשן
- [`DEVELOPMENT_ROADMAP.md`](./DEVELOPMENT_ROADMAP.md) — מפת פיתוח עתידית
- [`Additional channels Checklist.md`](./Additional%20channels%20Checklist.md) — איך מוסיפים ערוץ חדש
