# מדריך הגדרה ללקוח חדש — Multi-Channel Publisher

מסמך זה מרכז את **כל** מה שצריך להגדיר כשמשכפלים את הריפו ללקוח חדש: יצירת חשבונות, הרשאות, OAuth, ומשתני סביבה ב-Render. עברו על הסעיפים לפי הסדר.

> כל ערוץ הוא **אופציונלי** — אם הלקוח לא מפרסם ל-LinkedIn, אפשר לדלג על סעיף LinkedIn (ה-feature flag כבר כבוי כברירת מחדל). חובה: Google Sheets + Drive + Cloudinary + לפחות ערוץ פרסום אחד.

---

## 0. שכפול הריפו

- [ ] Fork או clone של הריפו ללקוח החדש (בדרך כלל ריפו פרטי נפרד לכל לקוח)
- [ ] עדכון `CLIENT_NAME` במסמכים פנימיים אם רלוונטי
- [ ] בדיקה ש-`render.yaml`, `Dockerfile`, `Dockerfile.web` נוכחים

---

## 1. Google Cloud — Service Account (חובה)

ה-Service Account משמש לקריאה מ-Google Sheets ולהורדת קבצים מ-Google Drive.

- [ ] יצירת פרויקט ב-[Google Cloud Console](https://console.cloud.google.com/) (או שימוש בקיים)
- [ ] הפעלת ה-APIs:
  - [ ] **Google Sheets API**
  - [ ] **Google Drive API**
  - [ ] **My Business Business Information API** (רק אם משתמשים ב-GBP)
  - [ ] **My Business Account Management API** (רק אם משתמשים ב-GBP)
- [ ] יצירת Service Account: `IAM & Admin → Service Accounts → Create`
- [ ] יצירת מפתח JSON: `Keys → Add Key → JSON` ושמירה (זה ה-`GOOGLE_SERVICE_ACCOUNT_JSON`)
- [ ] שיתוף ה-Spreadsheet של הלקוח עם כתובת המייל של ה-SA — הרשאת **Editor**
- [ ] שיתוף תיקיית ה-Drive שממנה הלקוח בוחר קבצים — הרשאת **Viewer** לפחות

**משתני סביבה שנוצרים בשלב הזה:**
- `GOOGLE_SERVICE_ACCOUNT_JSON` — כל ה-JSON כמחרוזת אחת
- `SPREADSHEET_ID` — מתוך URL של הגיליון: `docs.google.com/spreadsheets/d/<ID>/edit`
- `SHEET_NAME` — שם הטאב (ברירת מחדל `Sheet1`)
- `GOOGLE_DRIVE_FOLDER_ID` — מתוך URL של התיקייה ב-Drive

---

## 2. הכנת Google Sheet ללקוח (חובה)

- [ ] יצירת/שכפול גיליון לפי המבנה של `SHEET_COLUMNS` ב-`config_constants.py`
- [ ] עמודות חובה (לפי הסדר):
  `id, status, network, post_type, publish_at, caption, caption_ig, caption_fb, caption_gbp, caption_li, li_author_urn, gbp_post_type, cta_type, cta_url, google_location_id, hashtags, first_comment, drive_file_id, cover_file_id, cloudinary_url, source, result, error, retry_count, locked_at, processing_by, published_channels, failed_channels`
- [ ] שורת הכותרות תואמת בדיוק לשמות העמודות
- [ ] שיתוף הגיליון עם ה-Service Account (ראו סעיף 1)

---

## 3. Cloudinary (חובה — IG דורש URL ציבורי)

- [ ] יצירת חשבון ב-[Cloudinary](https://cloudinary.com/) (חינמי מספיק להתחלה)
- [ ] העתקת `Cloud Name`, `API Key`, `API Secret` מה-Dashboard

**משתני סביבה:**
- `CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME` (מועדף — שדה אחד)
- *או* `CLOUDINARY_CLOUD_NAME` + `CLOUDINARY_API_KEY` + `CLOUDINARY_API_SECRET`
- `CLOUDINARY_RETENTION_DAYS` — אופציונלי (ברירת מחדל 10)

---

## 4. Meta — Instagram + Facebook (אופציונלי)

דלגו אם הלקוח לא מפרסם ל-IG/FB.

- [ ] יצירת אפליקציה ב-[Meta for Developers](https://developers.facebook.com/)
- [ ] הוספת מוצרים: **Instagram Graph API** + **Pages API**
- [ ] חיבור עמוד הפייסבוק של הלקוח לאפליקציה
- [ ] חיבור חשבון IG Business לעמוד FB
- [ ] יצירת **System User token** ארוך טווח (מומלץ — לא פג)
- [ ] הרשאות נדרשות לטוקן:
  - `instagram_basic`
  - `instagram_content_publish`
  - `pages_manage_posts`
  - `pages_read_engagement`
  - `pages_show_list`

**משתני סביבה:**
- `IG_USER_ID` — מתקבל מ-`GET /me/accounts → ig_business_account`
- `IG_ACCESS_TOKEN`
- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN` (אפשר אותו טוקן אם יש לו את כל ההרשאות)
- `META_API_VERSION` — אופציונלי, ברירת מחדל `v21.0`

### 4.1 העברת אפליקציית Meta ל-Live mode (חובה)

אפליקציות חדשות נוצרות במצב **Development**. במצב הזה:
- ליד שם האפליקציה בפוסט מופיע סימן **"?"**
- פוסטים שפורסמו דרך האפליקציה **לא נראים בלינק חיצוני** ("This content isn't available at the moment") — גם אם בעמוד עצמו הם Public
- כדי שזה יעבוד תקין צריך להעביר את האפליקציה ל-**Live mode**, ולשם כך Meta דורשת **Privacy Policy URL** ציבורי

**שלבי המעבר:**

- [ ] לוודא שהפאנל פרוס ופעיל (סעיף 9)
- [ ] לוודא שעמוד הפרטיות נגיש בלי סיסמה: `https://<panel-domain>/privacy` (העמוד מובנה בקוד — לא נדרש דבר)
- [ ] **לעדכן בקוד את כתובת המייל ושם הלקוחה ב-`web_app.py`** (חיפוש `_PRIVACY_POLICY_HTML`) — כיום מוגדר ל-shiraagd@gmail.com
- [ ] ב-[Meta Developers Console](https://developers.facebook.com/) → האפליקציה → **Settings → Basic**:
  - להדביק את ה-URL בשדה **Privacy Policy URL**
  - לוודא שיש **App Icon** ו-**Category** (סטנדרט: "Business")
  - שמירה
- [ ] בראש הדף, לעבור על הטוגל **App Mode**: Development → **Live**
- [ ] לפרסם פוסט בדיקה דרך הפאנל ולוודא:
  - שה-"?" נעלם ליד שם האפליקציה
  - שהלינק לפוסט נפתח לכל מי שמקבל אותו (לא רק אדמינים)

> פוסטים שפורסמו לפני המעבר ל-Live עשויים להישאר מוגבלים — הדגל הוטמע ברגע הפרסום. רק פוסטים חדשים שיפורסמו אחרי המעבר יהיו פתוחים לחלוטין.

> אם Meta דורשת בנוסף **App Review** עבור `pages_manage_posts` — זה תהליך נפרד שלוקח מספר ימים, דורש סרטון use case ו-screencast. בדרך כלל לא נדרש כשמשתמשים ב-System User token עם Page admin.

---

## 5. Google Business Profile — GBP (אופציונלי)

דלגו אם הלקוח לא מפרסם ל-GBP. התחילו עם `GBP_ENABLED=false` עד שמסיימים בדיקות.

- [ ] בדיקה שה-APIs של GBP מופעלים בפרויקט (סעיף 1)
- [ ] בקשת access ל-GBP API ב-[GBP API Access Form](https://support.google.com/business/contact/api_default) (לוקח כמה ימים)
- [ ] יצירת **OAuth 2.0 Client ID** מסוג Desktop ב-`APIs & Services → Credentials`
- [ ] הוספת ה-scope `https://www.googleapis.com/auth/business.manage` למסך ההסכמה
- [ ] הרצת `python scripts/google_oauth.py` לקבלת `GBP_REFRESH_TOKEN`
- [ ] שליפת `GBP_ACCOUNT_ID` (פורמט `accounts/123456789`) — דרך ה-API או דרך הפאנל
- [ ] (אופציונלי) הגדרת `GBP_DEFAULT_LOCATION_ID` אם יש מיקום ברירת מחדל

**משתני סביבה:**
- `GBP_ACCOUNT_ID`
- `GBP_OAUTH_CLIENT_ID`
- `GBP_OAUTH_CLIENT_SECRET`
- `GBP_REFRESH_TOKEN`
- `GBP_DEFAULT_LOCATION_ID` — אופציונלי
- `GBP_ENABLED=false` בתחילה, להעלות ל-`true` אחרי בדיקות

---

## 6. LinkedIn (אופציונלי)

דלגו אם הלקוח לא מפרסם ל-LinkedIn.

- [ ] יצירת אפליקציה ב-[LinkedIn Developer Portal](https://developer.linkedin.com/)
- [ ] בקשת מוצר **Share on LinkedIn** (scope `w_member_social`) — או **Marketing Developer Platform** לפרסום מטעם Organization
- [ ] קבלת Client ID + Client Secret מטאב Auth
- [ ] הרצת `python scripts/linkedin_oauth.py` לקבלת `LI_REFRESH_TOKEN`
- [ ] שליפת `LI_AUTHOR_URN` — פורמט `urn:li:person:XXXXX` או `urn:li:organization:XXXXX`

**משתני סביבה:**
- `LI_OAUTH_CLIENT_ID`
- `LI_OAUTH_CLIENT_SECRET`
- `LI_REFRESH_TOKEN`
- `LI_AUTHOR_URN`
- `LI_ENABLED=false` בתחילה, להעלות ל-`true` אחרי בדיקות

---

## 7. Telegram — התראות (מומלץ)

- [ ] יצירת בוט דרך [@BotFather](https://t.me/BotFather) → קבלת `TELEGRAM_BOT_TOKEN`
- [ ] קבלת Chat ID דרך [@userinfobot](https://t.me/userinfobot) (או דרך `/getUpdates`)
- [ ] שליחת הודעה ראשונה לבוט מהמשתמש כדי שיוכל לשלוח חזרה

**משתני סביבה:**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` — אפשר רשימה מופרדת בפסיקים

---

## 8. Web Panel — סיסמאות

- [ ] בחירת סיסמה חזקה ל-`WEB_PANEL_SECRET` (חובה בפרודקשן — ללא זה הפאנל פתוח לכולם)
- [ ] (אופציונלי) `WEB_PANEL_DEV_SECRET` — סיסמה למצב מפתח שמציג file IDs מלאים

---

## 9. Render — דיפלוי

- [ ] חיבור הריפו ל-[Render](https://render.com/) דרך Blueprint (`render.yaml`)
- [ ] Render יזהה שני שירותים: `social-publisher-panel` (web) ו-`social-publisher` (cron כל 5 דק׳)
- [ ] הזנת **כל** ה-env vars שנאספו בסעיפים הקודמים (כולם `sync: false` — חייבים להיות מוזנים ידנית לכל לקוח)
- [ ] רשימת ה-env vars שצריך להזין בכל שירות:

  **משותפים לשני השירותים:**
  - `GOOGLE_SERVICE_ACCOUNT_JSON`, `SPREADSHEET_ID`, `SHEET_NAME`
  - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
  - `META_API_VERSION`, `IG_USER_ID`, `IG_ACCESS_TOKEN`, `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - `APP_BASE_URL`, `CLIENT_NAME`

  **רק ב-web (`social-publisher-panel`):**
  - `GOOGLE_DRIVE_FOLDER_ID`, `WEB_PANEL_SECRET`, `WEB_PANEL_DEV_SECRET`, `REPO_URL`

  **רק ב-cron (`social-publisher`):**
  - `CLOUDINARY_RETENTION_DAYS`, `PUBLISH_MAX_RETRIES`, `PUBLISH_RETRY_DELAY`

  **GBP (אם בשימוש — בשני השירותים):**
  - `GBP_ACCOUNT_ID`, `GBP_OAUTH_CLIENT_ID`, `GBP_OAUTH_CLIENT_SECRET`, `GBP_REFRESH_TOKEN`, `GBP_ENABLED`
  - `GBP_DEFAULT_LOCATION_ID` (אופציונלי)

  **LinkedIn (אם בשימוש — בשני השירותים):**
  - `LI_OAUTH_CLIENT_ID`, `LI_OAUTH_CLIENT_SECRET`, `LI_REFRESH_TOKEN`, `LI_AUTHOR_URN`, `LI_ENABLED`

> ה-`render.yaml` כולל את כל המשתנים (כולל GBP ו-LinkedIn) כ-`sync: false`, כך ש-Render רק *מצהיר* עליהם — הערכים בפועל מוזנים ב-Dashboard לכל לקוח. ערוצים שלא בשימוש פשוט נשארים ריקים, וה-feature flags (`GBP_ENABLED`, `LI_ENABLED`) שולטים אם הם נטענים בכלל.

- [ ] עדכון `APP_BASE_URL` לכתובת בפועל של ה-web service אחרי הדיפלוי הראשון
- [ ] בחירת region: `frankfurt` (קרוב לישראל)

---

## 10. אימות אחרי דיפלוי

- [ ] ה-cron רץ בלוגים ללא שגיאות אתחול (`python main.py`)
- [ ] ה-web panel נטען ודורש סיסמה
- [ ] בחירת קובץ מ-Drive מצליחה (אומת ש-`GOOGLE_DRIVE_FOLDER_ID` משותף ל-SA)
- [ ] שורת בדיקה בגיליון עם `status=READY` נתפסת ב-cron
- [ ] פוסט בדיקה IG/FB מתפרסם בהצלחה
- [ ] התראת טלגרם נשלחת על הצלחה/כשל
- [ ] (אם GBP) בדיקת פוסט GBP בודד אחרי `GBP_ENABLED=true`
- [ ] (אם LI) בדיקת פוסט LinkedIn בודד אחרי `LI_ENABLED=true`

---

## נספח: רשימת כל משתני הסביבה במערכת

| משתנה | חובה? | שירות |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | חובה | web + cron |
| `SPREADSHEET_ID` | חובה | web + cron |
| `SHEET_NAME` | חובה | web + cron |
| `GOOGLE_DRIVE_FOLDER_ID` | חובה | web |
| `CLOUDINARY_URL` *או* (`CLOUDINARY_CLOUD_NAME` + `CLOUDINARY_API_KEY` + `CLOUDINARY_API_SECRET`) | חובה | web + cron |
| `CLOUDINARY_RETENTION_DAYS` | אופציונלי | cron |
| `META_API_VERSION` | אופציונלי | web + cron |
| `IG_USER_ID`, `IG_ACCESS_TOKEN` | אם IG | web + cron |
| `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN` | אם FB | web + cron |
| `GBP_ACCOUNT_ID`, `GBP_OAUTH_CLIENT_ID`, `GBP_OAUTH_CLIENT_SECRET`, `GBP_REFRESH_TOKEN` | אם GBP | web + cron |
| `GBP_DEFAULT_LOCATION_ID` | אופציונלי | web + cron |
| `GBP_ENABLED` | אם GBP | web + cron |
| `LI_OAUTH_CLIENT_ID`, `LI_OAUTH_CLIENT_SECRET`, `LI_REFRESH_TOKEN`, `LI_AUTHOR_URN` | אם LI | web + cron |
| `LI_ENABLED` | אם LI | web + cron |
| `WEB_PANEL_SECRET` | חובה בפרודקשן | web |
| `WEB_PANEL_DEV_SECRET` | אופציונלי | web |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | מומלץ | web + cron |
| `APP_BASE_URL` | מומלץ | web + cron |
| `CLIENT_NAME` | מומלץ | web + cron |
| `REPO_URL` | אופציונלי | web |
| `PUBLISH_MAX_RETRIES`, `PUBLISH_RETRY_DELAY` | אופציונלי | cron |
| `FFMPEG_TIMEOUT`, `META_API_VERSION_WARN_DAYS`, `HEALTH_CACHE_TTL_SECONDS`, `HEALTH_NOTIFY_COOLDOWN_SECONDS` | אופציונלי | web + cron |
