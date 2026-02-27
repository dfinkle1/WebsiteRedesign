# Staff Procedures

This document describes workflows for AIM staff using the admin system.

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
