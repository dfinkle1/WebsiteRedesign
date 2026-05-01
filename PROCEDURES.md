# Staff Procedures

This document describes workflows for AIM staff using the admin system.

---

## Homepage Feed

The homepage "Latest Updates" column is a **two-stream feed** that combines automatic news surfacing with manual control over announcements and pinned items.

**Location:** Admin → News → Homepage Feed Items

---

### How the Feed Works

The homepage shows up to **5 items**, drawn from two sources and merged:

**Stream 1 — News Articles (automatic)**
Any published news article with **"Is Featured"** checked appears in the feed automatically. You do not need to create a feed item — just publish the article and check the box.

**Stream 2 — Manual Feed Items**
Items you create explicitly in Admin → News → Homepage Feed Items. Use these for:
- Announcements with no backing article ("Call for Proposals open", grant awards, etc.)
- Pinning a specific article to the top of the feed
- Milestones, event callouts, or any custom content

**Merge order:**
1. Pinned manual items first (sorted by Pin Order lowest-first)
2. All remaining items (both auto-surfaced articles and unpinned manual items) sorted most-recent-first

---

### Publishing a News Article to the Feed

1. Go to Admin → News → News Articles → [Select or create article]
2. Check **"Is Featured"**
3. Set status to **Published**
4. Save — the article will appear in the homepage feed immediately

No further action needed. To remove it from the feed, uncheck "Is Featured" or unpublish the article.

---

### Creating a Manual Feed Item

Use this for standalone announcements or to pin/override an existing article's placement.

**Location:** Admin → News → Homepage Feed Items → Add

#### Option A — Standalone announcement (no article)

1. Leave **Linked Article** blank
2. Fill in:
   - **Title** — headline shown on the homepage
   - **Item Type** — News (blue), Announcement (amber), Event (green), Milestone (purple)
   - **Excerpt** — 1–2 sentence summary (max 300 characters)
   - **Body** — optional rich text shown below the excerpt
   - **URL** — where "Read more" links. Use `/path/` for internal, `https://` for external
   - **Image** — optional hero image
   - **Published At** — item won't appear until this date/time
   - **Pin Order** — see Ordering below
   - **Is Active** — uncheck to hide without deleting
3. Save

#### Option B — Linked to an existing article (e.g. to pin it)

1. Set **Linked Article** by searching for the article
2. Leave Title, Excerpt, Image, and URL **blank** — they will automatically use the article's values
3. Set a **Pin Order** to control placement
4. Save

When a manual item links to an article, that article is excluded from the automatic stream — it will not appear twice.

You can also selectively override fields: for example, set a custom Title while leaving Image blank (the article's image will be used).

---

### Ordering Items

| Scenario | How to control it |
|----------|-------------------|
| Pin an item to always appear first | Set Pin Order = 1 |
| Pin a second item below that | Set Pin Order = 2 |
| Let an item sort by date | Leave Pin Order blank |

Pinned items always appear before unpinned ones. Unpinned items (both manual and auto-surfaced articles) are sorted by date, most recent first.

---

### Editing and Deactivating Items

- **Temporarily hide a manual item:** Uncheck "Is Active" — it disappears from the homepage but stays in the database
- **Remove an auto-surfaced article from the feed:** Uncheck "Is Featured" on the article
- **Pin Order** and **Is Active** are editable inline directly from the feed items list view

---

### How Many Items Show

The homepage displays the top **5 items**. If more than 5 are active, only the top 5 by pin order then date are shown. Visitors can click "All news & newsletters →" to see everything.

---

### Troubleshooting

- **Article not appearing:** Confirm both "Is Published" and "Is Featured" are checked, and "Published At" is in the past
- **Manual item not appearing:** Check "Is Active" is checked and "Published At" is in the past
- **Item appearing twice:** A manual feed item is linked to the same article — the system deduplicates, so this shouldn't happen. If it does, check whether the linked article field is set correctly
- **Wrong order:** Verify Pin Order values — items without a Pin Order always appear after pinned ones
- **Broken link:** Make sure the URL starts with `/` for internal pages or `https://` for external

---

## News Articles

### Adding a Gallery/Slideshow to an Article

Articles can have multiple images displayed as a gallery slideshow.

**Location:** Admin → News → News Articles → [Select Article]

**Steps:**

1. Open the article in the admin
2. Scroll down to the "Article Images" section (below the main form)
3. Click "Add another Article Image" for each image you want to add
4. For each image:
   - Click the folder icon to select/upload an image from the media library
   - Add an optional caption (displayed below the image)
   - Set the order number (lower numbers appear first)
5. Save the article

**Display Behavior:**
- **1 image:** Displays as a single figure below the article body
- **2+ images:** Displays as a carousel/slideshow with:
  - Previous/Next arrows
  - Indicator dots
  - Thumbnail navigation below

**Notes:**
- The "Featured Image" is separate - it's the main hero image shown at the top
- Gallery images appear after the article body
- Captions are optional but recommended for accessibility

---

## Events

### Creating an Event

**Location:** Admin → Events → Add Event

**Required fields:**
- Title
- Start date/time
- Status (Draft, Published, Cancelled, Postponed)

**Event Types:**
- Public Lecture
- Workshop
- Conference
- Social Event
- Webinar
- Other

**Steps:**

1. Fill in the title and select event type
2. Set start date/time (end is optional)
3. Choose location type:
   - **In-person:** Enter venue name, address, city, region, country
   - **Online:** Check "Is online" and enter the meeting URL
4. Add content:
   - Short summary (appears in list views, max 300 chars)
   - Description (full HTML, appears on detail page)
   - Hero image
5. Set ticket/registration options:
   - Check "Is free" for free events, or enter a price
   - Add external ticket URL (Eventbrite, etc.) if applicable
   - Set capacity if limited
   - Check "Registration required" if free but requires signup
6. Set status to "Published" when ready to go live
7. Save

---

### Event Status Workflow

| Status | Meaning |
|--------|---------|
| **Draft** | Not visible to public |
| **Published** | Visible on events page |
| **Cancelled** | Shows "Cancelled" badge, tickets disabled |
| **Postponed** | Shows "Postponed" badge, tickets disabled |

---

### Viewing Events

The public events page (`/events/`) shows:

**Upcoming Events:**
- Card layout with image, badges, date/time
- Badges: event type, "Online" if virtual, "Free" if no cost

**Past Events:**
- Grouped by year with navigation
- Compact list format

---

### Event Detail Features

Each event page includes:

- Hero image (if set)
- Status badges (type, online, cancelled/postponed)
- Full description
- Location section (with Google Maps link for in-person, join link for online)
- Sidebar with:
  - Price/capacity info
  - Ticket/registration button
  - Date/time card with "Add to Calendar" (Google Calendar, iCal/Outlook)
  - Share buttons (Twitter, Facebook, Email)

---

### Calendar Integration

Events support calendar export:

- **Google Calendar:** Opens Google Calendar with event pre-filled
- **iCal/Outlook:** Downloads `.ics` file that can be imported

Both are accessible from the event detail page sidebar.

---

### Using Events on Other Pages

To display upcoming events in a sidebar or widget:

```django
{% load events_tags %}
{% upcoming_events limit=3 %}
```

This renders a compact list of the next 3 upcoming events.

---

## Enrollment Management

### Bulk Import Enrollments from CSV

Use this when you receive a list of participants from program organizers.

**Location:** Admin → Programs → [Select Program] → Actions → "Manage" (or go to program detail and click "Manage Enrollments")

**Steps:**

1. Go to the program's "Manage Enrollments" page
2. In the "Import Enrollments from CSV" section, paste CSV data with headers:
   ```
   first_name,last_name,email,funding
   John,Smith,john@example.com,full
   Jane,Doe,jane@example.com,partial
   ```
3. Click "Import Enrollments"
4. Imported enrollments appear in the "Pending Invites" section

**Notes:**
- Duplicate emails (already enrolled) are automatically skipped
- The `funding` column is optional
- Email addresses are normalized to lowercase

---

### Sending Invitation Emails

After importing enrollments, send invitation emails so participants can accept/decline.

**Steps:**

1. On the "Manage Enrollments" page, find the "Pending Invites" section
2. Check the boxes next to enrollments you want to invite (or use "Select All")
3. Click "Send Invites to Selected"
4. Emails are sent with accept/decline links
5. Sent invitations move to "Invited, Awaiting Response" section

**What recipients see:**
- Email with program title and dates
- "Accept Invitation" button (green)
- "Decline" button (gray)
- They must sign in with ORCID to accept

---

### Enrollment Status Tracking

The Manage Enrollments page shows three sections:

| Section | Meaning |
|---------|---------|
| **Pending Invites** | Imported but no email sent yet |
| **Invited, Awaiting Response** | Email sent, waiting for accept/decline |
| **Confirmed/Linked** | Linked to a person account (accepted) |

---

### When Someone Accepts an Invitation

1. Recipient clicks "Accept" link in email
2. They're prompted to sign in with ORCID (if not already)
3. Their enrollment is linked to their person account
4. They're redirected to enter logistics (travel dates, phone, etc.)
5. Enrollment moves to "Confirmed/Linked" section in admin

---

### When Someone Declines

1. Recipient clicks "Decline" link in email
2. They see a confirmation page
3. Enrollment is marked as declined (visible in applicants list)

---

## Program Management

### Creating a New Program

**Location:** Admin → Programs → Add Program

The `code` field is auto-generated - you don't need to enter it. Just fill in:
- Title (required)
- Type (Workshop, SQuaRE, etc.)
- Start/End dates
- Application mode and deadline

For SQuaREs, also set the **Meeting Number** (1st, 2nd, or 3rd meeting).

---

### Viewing Applicants

**Location:** Admin → Programs → [Select Program] → Actions → "Applicants"

Shows all enrollments with:
- Name, email, ORCID, institution
- Status (Accepted/Declined/Pending)
- Date of response

**Note:** Some enrollments may show "(not linked)" if they haven't accepted yet - these display the information from the CSV import.

---

### Exporting Data

From the program list or detail page:

- **CSV Export:** Exports all applicants with contact info and status
- **Emails:** Shows comma-separated list of accepted participants' emails
- **Name Badges:** Exports First Name, Last Name for badge printing

---

## Reimbursements

### Processing a Reimbursement Request

**Location:** Admin → Reimbursements → Reimbursement Requests

**Quick Filters:**
- Use "Needs Review" to see submitted requests awaiting review
- Use "Needs Payment" to see approved requests awaiting payment

---

### Review Workflow

1. **Open the request** from the list (click "Review" button or the ID)
2. **Check line items:**
   - Verify receipts are attached (click receipt links to view)
   - Check amounts match receipts
   - For foreign currency items, enter the exchange rate
3. **Add per diem** if participant is eligible:
   - Scroll to Expense Line Items
   - Fill in a new row: Category = "Meals / Per Diem", amount, date
   - These are automatically marked as "Staff Added"
4. **Take action:**
   - Click **"Approve Request"** - auto-fills approved amounts = requested amounts
   - Click **"Request Changes"** - sends back to participant with notes
   - Click **"Cancel Request"** - cancels the request

---

### Foreign Currency Expenses

When participants have expenses in foreign currencies (e.g., GBP flights from UK):

1. The currency is shown in the line item (e.g., "GBP")
2. Staff enters the **Exchange Rate** field
3. The **Amount Requested (USD)** should be the converted amount
4. A warning appears if conversion is needed before approval

**Tip:** Use [xe.com](https://xe.com) for current exchange rates.

---

### Marking as Paid

After a request is approved:

1. Process the payment (check or ACH)
2. Return to the request in admin
3. Click **"Mark as Paid"**
4. The request moves to "Paid" status

---

### Staff-Added Expenses

Staff can add expenses that participants don't submit themselves:

| Type | When to Add |
|------|-------------|
| **Per Diem** | Participant is eligible for meal allowance |
| **Mileage** | Participant drove and didn't claim it |
| **Other** | Any expense staff needs to add |

Staff-added items are marked with a "STAFF" badge and don't require receipts.

---

### Exporting for Finance

**Bulk Export:**
1. Select requests using checkboxes
2. Choose "Export selected to CSV" from Actions dropdown
3. Click "Go"

**Line Item Export:**
- Use "Export line items to CSV" to get detailed expense breakdown with currency info

---

### Reimbursement Statuses

| Status | Meaning |
|--------|---------|
| **Draft** | Participant is still filling out the form |
| **Submitted** | Ready for staff review |
| **Changes Needed** | Sent back to participant for corrections |
| **Approved** | Approved, waiting for payment |
| **Paid** | Payment has been processed |
| **Cancelled** | Request was cancelled |

---

## Donations

The donation system accepts one-time gifts via PayPal and sends automated tax receipts by email. Staff manage fund categories, view/search donations, resend receipts, export records, and process refunds — all from the admin.

---

### Initial Setup (Do Once)

Before the donation page goes live, two things must be configured:

#### 1. Organization Settings

**Location:** Admin → Donations → Organization Settings

Fill in:
- **Legal name** — e.g., "American Institute of Mathematics"
- **EIN** — e.g., "77-0378584" (appears on every receipt for IRS compliance)
- **Address** — full mailing address
- **Receipt footer** — optional extra text at the bottom of receipts (e.g., "No goods or services were provided in exchange for this gift.")

Only one row of Organization Settings exists. Click it to edit; you cannot add or delete it.

#### 2. PayPal Credentials

A developer must enter these in the server's `.env` file — staff do not manage these directly:
- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_WEBHOOK_ID`
- `PAYPAL_MODE` (set to `live` in production, `sandbox` for testing)

---

### Managing Fund Categories

**Location:** Admin → Donations → Donation Categories

Each fund (e.g., "General Fund", "Endowment") is a category that donors choose from on the donation page.

**To add a fund:**
1. Click "Add Donation Category"
2. Fill in:
   - **Name** — displayed to donors (e.g., "Endowment Fund")
   - **Slug** — auto-generated URL-safe identifier (do not change after creation)
   - **Description** — shown in the sidebar on the donation page explaining the fund's purpose
   - **Sort order** — lower numbers appear first in the list
   - **Is active** — uncheck to hide a fund from donors without deleting it
3. Save

**To remove a fund from the donation page:** Uncheck "Is active" and save. The fund remains in the database for historical records but donors can no longer select it.

---

### Viewing and Searching Donations

**Location:** Admin → Donations → Donations

**Columns shown:**
| Column | Meaning |
|--------|---------|
| Donor Name | Name entered at checkout |
| Donor Email | Email entered at checkout |
| Amount | Gift amount in USD |
| Category | Fund/designation chosen |
| Status | Current state (see table below) |
| Receipt Number | e.g., AIM-2025-00042 |
| Receipt Sent At | Timestamp receipt email was sent |
| Created At | When donor submitted the form |

**Donation Statuses:**
| Status | Meaning |
|--------|---------|
| **Pending** | Donor started checkout but PayPal hasn't confirmed payment yet |
| **Completed** | PayPal confirmed payment received |
| **Failed** | PayPal declined or connection error occurred |
| **Refunded** | Full refund was processed via admin |
| **Cancelled** | Donor clicked Cancel on the PayPal page |

**To find a specific donation:**
- Use the search bar — searches donor name, email, receipt number, or PayPal order ID
- Use the filters on the right: Status, Category, Date

---

### Resending a Receipt Email

Use this when a donor says they never received their receipt.

1. Find the donation(s) in the list
2. Check the box(es) next to them
3. Select "Resend receipt email to selected donors" from the Actions dropdown
4. Click "Go"

**Notes:**
- Only donations with **Completed** status will receive a receipt — others are skipped
- The receipt is re-sent to the original donor email address
- A message at the top will confirm how many were sent and how many were skipped

---

### Exporting Donations to CSV

Use this for finance reporting, audits, or donor records.

1. Select the donations you want to export (check boxes), or use the search/filter to narrow the list first
2. Select "Export selected donations to CSV" from Actions
3. Click "Go"
4. A CSV file downloads automatically

**CSV columns:** Receipt Number, Date, Donor Name, Donor Email, Amount, Currency, Fund, Status, PayPal Order ID, PayPal Capture ID, Goods/Services Provided, Receipt Sent At

**Tip:** To export all donations for a date range, use the "Created At" date filter on the right to narrow the list, then select all and export.

---

### Processing a Refund

Use this to issue a full refund through PayPal.

1. Find the completed donation in the admin list
2. Check the box next to it
3. Select "Process full refund via PayPal for selected donations" from Actions
4. Click "Go"

The system will:
- Call PayPal's API to issue the refund to the donor's original payment method
- Mark the donation status as **Refunded** in the database

**Important notes:**
- Only **Completed** donations can be refunded — pending/cancelled/already-refunded are skipped
- This issues a **full refund** — partial refunds must be done directly in the PayPal dashboard
- Refunds typically appear in the donor's account within 3–5 business days
- The system does **not** automatically email the donor about the refund — notify them separately
- If a refund fails (PayPal error), the donation stays as Completed and an error message is shown — try again or contact the developer

---

### Troubleshooting: Donor Didn't Receive Receipt

1. Search for their donation by email or name
2. Confirm status is **Completed** — if it shows Pending, the payment may not have cleared yet (wait a few minutes and refresh)
3. If Completed, use the "Resend receipt email" action (see above)
4. If the email still doesn't arrive, ask the donor to check spam/junk folders
5. Check the receipt email address is correct on the donation record

---

### Webhook Event Log

**Location:** Admin → Donations → Webhook Events

This is a technical audit log of all PayPal notifications received. Staff generally don't need to use this, but it can help diagnose issues.

| Column | Meaning |
|--------|---------|
| Event Type | e.g., PAYMENT.CAPTURE.COMPLETED |
| PayPal Event ID | Unique ID from PayPal |
| Processed | Whether the system acted on this event |
| Received At | Timestamp |
| Error? | Whether processing raised an error |

If a donation is stuck in Pending and you don't see a corresponding Completed webhook event, notify the developer — the webhook may be misconfigured.

---

## Time & Effort Reporting

The Time & Effort system lets AIM staff record and certify how their time was spent across grant-funded and indirect activities each pay period. It produces signed PDF reports suitable for federal grant compliance.

---

### Staff Types

| Type | Reporting cadence | How they report |
|------|-------------------|-----------------|
| **Salary** | 28-day windows (4 weeks) | Fill in hours by day per activity each week; generate a combined PDF at period end |
| **Hourly** | 14-day periods (2 weeks) | Same weekly form; one PDF per period |
| **Director** | 28-day windows | Enter percentages directly (no weekly timesheets); one PDF per period |

---

### Initial Admin Setup (Do Once Per Employee)

#### 1. Create a Staff Timesheet Profile

**Location:** Admin → Timeeffort → Staff Timesheet Profiles → Add

- **User** — link to the employee's Django user account
- **Staff Type** — Salary, Hourly, or Director
- **Supervisor** — the person with first-hand knowledge of their work (signs the paper PDF)
- **Title** — appears on generated PDFs
- **Is Active** — uncheck to remove from all dashboards

#### 2. Set Up the Reporting Calendar (One-time, already done)

**Location:** Admin → Timeeffort → Reporting Calendar

One calendar exists. If periods are missing, select it and run the action **"Generate reporting periods"**. This creates all 14-day periods and their weekly slots.

#### 3. Configure Activities

**Location:** Admin → Timeeffort → Activities

Activities are the rows that appear on weekly entry forms and in PDF reports.

| Field | Meaning |
|-------|---------|
| **Classification** | Direct, Indirect, Leave, or Unallowable |
| **Default Grant Code** | Pre-fills the grant code field (e.g. DMS-2425344) |
| **Valid From / Valid To** | Date range this grant is active. Leave blank for no restriction. Salary forms automatically hide expired activities. |
| **Is Active** | Uncheck to remove from all forms |
| **Is Holiday Activity** | Check on exactly one activity (e.g. "AIM Holiday"). This row is auto-filled on salary/hourly weekly forms for any week containing an AIM holiday. |
| **Sort Order** | Controls display order on forms and PDFs |

**Important:** Salary staff see all active direct activities and all active indirect/leave/unallowable activities. There is no "preset" toggle needed for salary — just keep the activity active.

#### 4. Configure AIM Holidays

**Location:** Admin → Timeeffort → AIM Holidays → Add

Add one row per holiday with the exact date. On any weekly form covering that date:
- Salary/hourly forms: the holiday activity row auto-appears with 8 hours pre-filled for that day
- Director reports: the holiday percentage is automatically subtracted from the Administrative allocation

The salary dashboard shows a yellow warning on any period card that contains holidays.

#### 5. Set Salary Indirect Defaults (Optional)

**Location:** Admin → Timeeffort → Salary Indirect Allocations → Add

For each salary employee, you can set weekly default hours for each indirect/leave/unallowable category. These pre-fill when the employee opens a new week for the first time. The employee can change them freely.

If no allocation is set, all indirect rows default to 0 — the employee fills them in manually.

---

### Salary Staff Workflow

#### Week-by-Week Entry

1. Staff go to **Staff Portal → Time & Effort**
2. Each 28-day period card shows progress (e.g. "2 of 4 weeks submitted")
3. Click a week button to open the weekly entry form
4. The form shows:
   - **Direct activities** — one row per active grant, with a grant code field and daily hour inputs
   - **Additional grants** — 2 free-text custom slots for supplemental grants
   - **Indirect / Leave / Unallowable** — pre-listed rows (Administrative, Sick/Personal, Vacation, etc.)
   - **Holiday row** — auto-appears with 8h pre-filled if there's a holiday that week
5. Enter hours for each day (Sun–Sat), then click **Save Draft** or **Submit Week**
6. Submitted weeks can still be edited — click the week button again. Re-editing resets the week to Draft; click Submit again to resubmit

**Carry-forward:** When opening a week that hasn't been touched yet, hours are pre-filled from the previous week. Holiday days are zeroed out automatically during carry-forward.

#### Copying the Previous Period

On the dashboard, each period card has a **"Copy Last Period"** button. This copies all 4 weeks from the prior 28-day window into the current one:
- Holiday lines are skipped
- Expired grants are skipped
- Holiday days in the current period are zeroed out

If the current period has holidays, a yellow warning appears on the card before you copy.

#### Generating the Final Report

Once all 4 weeks are submitted:

1. Click **Period Summary →** on the dashboard card
2. Click **Generate Final Report →**
3. The describe page shows each rolled-up activity line with a **Duties Description** field. These auto-populate from the most recent prior period — edit as needed.
4. Click **Generate PDF** — a combined PDF is created covering all 4 weeks plus a rollup table
5. Download the PDF from Period Summary

The PDF includes:
- 4 weekly grids (non-zero rows only)
- Rolled-up effort table (hours + % of time per activity)
- Employee electronic signature (ORCID authentication)
- Blank supervisor signature line

Regenerating is always allowed — just revisit the describe page and submit again.

---

### Hourly Staff Workflow

Same as salary but with 14-day periods (2 weeks). The final period report covers one 14-day period only.

---

### Director Workflow

1. Director goes to **Staff Portal → Time & Effort**
2. Each 28-day period card has an **Enter Report** button
3. Enter percentages for each activity (main grant, up to 4 extra grants, indirect categories)
4. Holiday percentages are automatically deducted from Administrative (5% per holiday)
5. Click **Save Draft** or **Submit**
6. After submission, **Download PDF** appears on the dashboard card

**Setting default allocations:** Directors can click **Manage Default Allocations** at the bottom of their dashboard to save their standard split. This pre-fills every new period.

---

### Admin: Reviewing and Approving Reports

**Location:** Admin → Timeeffort → Period Reports

After a report is submitted (status = Submitted):

1. Select the report(s) and choose **"Supervisor-approve selected submitted reports"** from Actions
2. After supervisor approval (status = Supervisor Approved), choose **"Mark selected supervisor-approved reports as Processed"**

To unlock a stuck report back to Draft: use **"Unlock selected reports back to Draft"** — use with care.

---

### Troubleshooting

**Holiday not auto-filling on weekly form**
- Check that an `Activity` with **Is Holiday Activity** checked exists and is active
- Check that the holiday date is entered under Admin → Timeeffort → AIM Holidays

**Indirect rows not appearing on salary form**
- Make sure the activity's **Classification** is Indirect, Leave, or Unallowable (not Direct)
- Make sure **Is Active** is checked

**"All weeks must be submitted" error on final report page**
- One or more weeks are in Draft. Go to Period Summary to see which weeks are outstanding.

**PDF not reflecting latest timesheet edits**
- Re-editing and resubmitting a week automatically invalidates the cached PDF. The next Generate Final Report rebuilds from the updated data.

**Grant activity not appearing on salary form**
- Check **Valid To** on the activity — if it's before the week's start date, it's hidden. Update or clear the date.

**Staff member not seeing their dashboard**
- Confirm a Staff Timesheet Profile exists for their user under Admin → Timeeffort → Staff Timesheet Profiles

---

## Troubleshooting

### "NoReverseMatch" or URL errors
- Clear the cache: In Django shell, run `from django.core.cache import cache; cache.clear()`

### Enrollment shows wrong person info
- The enrollment stores a "snapshot" of info at enrollment time
- If person updates their profile, enrollment snapshot doesn't change
- For linked enrollments, the current person info is shown

### Can't find an enrollment
- Check all three sections on Manage Enrollments page
- Use the Applicants view which shows all enrollments regardless of status
