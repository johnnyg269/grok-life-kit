# Building the "Grok Life Health" Shortcut

Build this once on an iPhone, test it, then share it as an iCloud link. Users add the link, answer three setup questions, and add one automation. Build on the iPhone: Health actions do not exist in Shortcuts on the Mac, and time-of-day automations can only be created on the iPhone.

Menu names below are for current iOS (17 and later). Wording shifts slightly between versions. Everything marked **Verify** is something to confirm on the device during the test run.

## What it sends

One POST to the bot's webhook with this JSON body:

```json
{
  "date": "2026-11-18",
  "steps": 6357,
  "weight": 183.4,
  "weight_unit": "lb",
  "sleep_hours": 7.2
}
```

| Field | Type | Meaning |
|---|---|---|
| `date` | text, `yyyy-MM-dd` | Today's date on the phone |
| `steps` | number | Steps so far today |
| `weight` | number | Latest body weight from Health in the last 2 days, in the unit Health shows |
| `weight_unit` | text, `lb` or `kg` | The unit of `weight` |
| `sleep_hours` | number | Hours asleep in roughly the last 24 hours |

Any field with no Health sample is sent as an empty string. The bot treats empty as "no data". The bot reads only these five fields and logs numbers from them; it ignores anything else.

## Build steps

### 0. Start clean

1. Open the Shortcuts app, tap the Shortcuts tab, tap **+**.
2. Tap the shortcut name at the top, choose **Rename**, and call it `Grok Life Health`.
3. Build it as a normal shortcut, not from inside an automation. The Health actions can be missing from the action list when you start inside an automation.
4. To add an action: tap the search field at the bottom, type the action name, tap the result.

### 1. Setup values (these become the import questions)

**Action 1: Text.** Type `PASTE_WEBHOOK_URL`.
**Action 2: Set Variable.** Name it `hookURL`.

**Action 3: Text.** Type `PASTE_SENDER_KEY`.
**Action 4: Set Variable.** Name it `hookKey`.

**Action 5: Text.** Type `lb`.
**Action 6: Set Variable.** Name it `wUnit`.

### 2. Today's date

**Action 7: Current Date.**
**Action 8: Format Date.** Date Format: **Custom**. Format String: `yyyy-MM-dd`.
**Action 9: Set Variable.** Name it `today`.

### 3. Steps

**Action 10: Find Health Samples.** Add filters:
- Type is **Steps**
- Start Date is **Today** (use "is Today", not "is in the last 1 day". The second is a rolling 24 hours and would reach into yesterday.)
- Sort by **Start Date**, order **Latest First** (sort order does not matter for a sum, but keep it consistent). Limit: off.

If you wear an Apple Watch, the phone and the watch can both record steps and the sum would count them twice. Add a filter **Source is** `iPhone` (or whichever source Health shows first under Browse, Activity, Steps, Data Sources & Access). **Verify:** the total should match the Steps number in the Health app.

**Action 11: Calculate Statistics.** Statistic: **Sum**. Input: **Health Samples** (the result of action 10). If Shortcuts chained the input to a different variable, tap the input and set it back to the Health Samples from action 10.
**Action 12: Set Variable.** Name it `steps`.

### 4. Weight

**Action 13: Find Health Samples.** Filters:
- Type is **Weight** (shown as Body Mass or Weight)
- Start Date is in the last **2** days
- Sort by **Start Date**, order **Latest First**
- Limit: **on**, **1** sample

**Action 14: Get Details of Health Samples.** Detail: **Value**. Input: the samples from action 13.
**Action 15: Get Numbers from Input.** Input: the result of action 14. This strips any unit text.
**Action 16: Set Variable.** Name it `weight`.

The weight unit is the one chosen at setup (`wUnit`). It must match the unit the Health app shows, or the number will be wrong. **Verify:** compare against the Health app on first run. Optional improvement: add a **Get Details of Health Samples** with **Unit** after action 13 and send that instead of `wUnit`, if your iOS version offers it.

### 5. Sleep

**Action 17: Find Health Samples.** Filters:
- Type is **Sleep Analysis**
- Start Date is in the last **1** day
- Value is any of **Asleep**, **Core**, **Deep**, **REM** (do not include In Bed or Awake). Older data shows only **Asleep**.
- If you wear a watch and also record sleep on the phone, add **Source is** the one you trust, or hours will double up.

**Action 18: Get Details of Health Samples.** Detail: **Duration**. Input: the samples from action 17.
**Action 19: Calculate Statistics.** Statistic: **Sum**.
**Action 20: Calculate** (the Calculate action, or Math): the sum, divided by **3600** if the result is in seconds. If the sum shows in minutes, divide by 60.
**Action 21: Round Number.** Round to **1 decimal**.
**Action 22: Set Variable.** Name it `sleep`.

**Verify:** the result should match Asleep time in the Health app for last night within a few minutes. Naps in the previous 24 hours are included. If the number is doubled, add the Source filter. If it is wrong by a factor of 60 or 3600, fix action 20.

### 6. Send it

**Action 23: Get Contents of URL.** Tap **Show More** and set:
- URL: the variable `hookURL`
- Method: **POST**
- Headers: add the sender-key header exactly as the routine panel shows it for the webhook (the panel names the header or the URL parameter to use). Set its value from the variable `hookKey`. If the panel shows a bearer token, the header is `Authorization` with the value `Bearer ` followed by `hookKey`. **Verify** against the panel text when you set it up.
- Request Body: **JSON**. Add the five fields:

| Key | Type | Value |
|---|---|---|
| `date` | Text | variable `today` |
| `steps` | Number | variable `steps` |
| `weight` | Number | variable `weight` |
| `weight_unit` | Text | variable `wUnit` |
| `sleep_hours` | Number | variable `sleep` |

Shortcuts may send numbers as text or as decimals. The bot accepts both.

**Action 24: Show Notification.** Title `Grok Life Health`, body `Sent to your coach`. This shows the user it ran, even when the automation runs without asking. Remove it if users find it noisy.

### 7. Test

1. Tap play. iOS asks for Health access. Allow **Steps**, **Weight** (Body Mass) and **Sleep**. Tap Allow for the web request when asked.
2. Check the three values against the Health app. Fix filters until they match.
3. Check the bot received it. A test from a computer proves the URL: send `curl -X POST <URL> -H 'Content-Type: application/json' -d '{"date":"2026-11-18","steps":1000}'` with the sender key header, then watch the routine's run history.
4. Run it a second time to confirm nothing breaks on repeat.

## Make it shareable

Do this on a clean copy so no personal webhook or key travels with the link.

1. Duplicate the finished shortcut and name the copy `Grok Life Health`.
2. In the copy, set Action 1 back to `PASTE_WEBHOOK_URL` and Action 3 to `PASTE_SENDER_KEY`. Leave Action 5 as `lb`.
3. Tap the shortcut's name, then the info button, then the **Setup** tab, then **Add Import Question**. Add one for each of the three Text actions:
   - Action 1: "Paste your Grok Life webhook URL."
   - Action 3: "Paste your Grok Life sender key."
   - Action 5: "Which weight unit does Apple Health show? Type lb or kg."
4. Under **Details**, add a short description: "Sends today's steps, latest weight and last night's sleep from Apple Health to your Grok Life."
5. Share: tap the Share button, then **Copy iCloud Link**. Paste the link into the skill (section 10.3 of `SKILL.md`).
6. Test the link on a second iPhone: add it, answer the three questions, run it, then confirm a payload arrives.

Notes:
- Shared shortcuts can only be re-shared safely if every personal value is removed. Re-check the Text actions before each re-share.
- When Apple changes an action name, update this guide and re-share. Old links keep working for people who already added them.
- Users are asked to type the unit, so a wrong answer is the most likely source of a bad weight. The bot's range check and its 5 lb jump check catch most of these.

## Personal automation (done by each user)

Shortcuts, Automation tab, **+** (New Automation), **Time of Day**.

1. Pick the time. Morning (about 8:00) brings weight and sleep. Evening (about 9:00 to 9:30 PM) brings final steps.
2. Repeat: **Daily**. Tap Next.
3. Add Action: **Run Shortcut**, then choose `Grok Life Health`. Tap Next.
4. Turn **Run Immediately** on (the switch labeled Ask Before Running must be off). Tap Done.
5. Optionally add a second automation for the other time.

Reliability notes:
- Health data is protected while the phone is locked. Choose a time the phone is usually unlocked or recently used, or samples can come back empty.
- Low Power Mode can stop automations from running.
- If an iOS update turns on "Ask Before Running" again, the automation will only send a notification until it is approved.

## Quick reference of the action list

1. Text `PASTE_WEBHOOK_URL`, Set Variable `hookURL`
2. Text `PASTE_SENDER_KEY`, Set Variable `hookKey`
3. Text `lb`, Set Variable `wUnit`
4. Current Date, Format Date `yyyy-MM-dd`, Set Variable `today`
5. Find Health Samples (Steps, Start Date is Today, source filter if needed), Calculate Statistics Sum, Set Variable `steps`
6. Find Health Samples (Weight, last 2 days, Latest First, Limit 1), Get Details Value, Get Numbers from Input, Set Variable `weight`
7. Find Health Samples (Sleep Analysis, last 1 day, asleep values), Get Details Duration, Calculate Statistics Sum, convert to hours, Round 1 decimal, Set Variable `sleep`
8. Get Contents of URL (`hookURL`, POST, sender-key header, JSON body with the five fields)
9. Show Notification
