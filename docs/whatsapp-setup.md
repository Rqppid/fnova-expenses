# WhatsApp receipts bot: setup (about 20 minutes, once)

What you get: send a receipt photo, PDF, Revolut statement (CSV is best) or FX confirmation to the
bot's WhatsApp number. Within seconds it replies "Got it"; within about 3 to 8 minutes it replies
"Logged: <vendor> <date> £<amount> <VAT> (row N), filed as <folder>/<file>.pdf". The nightly run
still happens for Gmail and OneDrive scans. Only Hamza's and Wahidullah's numbers are accepted.

Before this: GitHub repo (cloud-setup Part 3) and the tracker sync fix (keep the PC version) must
be done, because the bot is deployed from the repo and writes to OneDrive.

## 1. Meta app and the free test number
1. Go to https://developers.facebook.com/apps and log in with Facebook (any account you control;
   it does not post anything).
2. **Create app** > use case **Other** > app type **Business** > name `Fone Nova Receipts` >
   contact email fonenovaltd@gmail.com > Create. If asked for a Business portfolio, create one
   called `Fone Nova Ltd`.
3. In the app dashboard, find **WhatsApp** > **Set up**. Meta gives you a free **test number**.
4. Open **WhatsApp > API Setup**:
   - Under "To", click **Manage phone number list** and add **your mobile** and **Wahidullah's
     mobile**. Each of you gets a WhatsApp code to confirm.
   - Copy the **Phone number ID** (not the phone number) and send it to Claude.
   - Send the test number a "hello" from both phones so the chat exists.
5. **App settings > Basic**: click Show next to **App secret** and keep it for step 3.

## 2. A permanent access token (the one on the API Setup page dies after 24 hours)
1. https://business.facebook.com/settings > **Users > System users** > **Add** > name `receipts-bot`,
   role **Admin**.
2. **Assign assets** > Apps > `Fone Nova Receipts` > Full control. Also **WhatsApp accounts** >
   your test WhatsApp account > Full control.
3. **Generate new token** > app `Fone Nova Receipts` > expiry **Never** > tick
   `whatsapp_business_messaging` and `whatsapp_business_management` > Generate. Copy it now (shown once).

## 3. Vercel (Claude creates the project; you paste the secrets)
In the Vercel project `fonenova-intake` > Settings > Environment Variables, add:
| Name | Value |
|---|---|
| WA_TOKEN | the permanent token from step 2 |
| WA_APP_SECRET | the App secret from step 1.5 |
| WA_VERIFY_TOKEN | any long random word you make up (Claude needs it too, tell it) |
| WA_PHONE_NUMBER_ID | the Phone number ID from step 1.4 |
| WA_ALLOWED | `Hamza:44XXXXXXXXXX,Wahidullah:44XXXXXXXXXX` (your two mobiles, 44 then the number without the leading 0) |
| GOOGLE_TOKEN_JSON | same value as in the Claude cloud environment |
| MS_CLIENT_ID | `5260e8c6-8f4e-4565-bf67-cb16aec78746` |
| ROUTINE_TRIGGER_URL / ROUTINE_TRIGGER_TOKEN | from the routine's API trigger (Claude tells you where) |
The same WA_TOKEN, WA_PHONE_NUMBER_ID and WA_ALLOWED also go into the Claude cloud environment
(so the run can send the "Logged" replies).

## 4. Connect the webhook (Claude does this with you)
Meta > WhatsApp > Configuration > Webhook: Callback URL `https://<vercel-project>.vercel.app/api/whatsapp`,
Verify token = WA_VERIFY_TOKEN > Verify and save > Webhook fields > subscribe **messages**.

## Later: your own number instead of the test number
WhatsApp Manager > Phone numbers > Add (a number not on the WhatsApp app, e.g. a £1 SIM) > verify
by SMS > replace WA_PHONE_NUMBER_ID in Vercel and the Claude environment. Nothing else changes.

## Costs and limits
- Messages you send to the bot, and its replies within 24 hours, are free.
- Vercel's free Hobby plan is for non-commercial use; business use is meant for Pro (about $20/month).
- Each instant run uses your Claude plan. Bursts of photos are grouped into one run.
