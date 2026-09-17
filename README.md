# Dr. Radhika's Allergy & Lung Clinic — website

Static site for [allergylungclinic.com](https://www.allergylungclinic.com/).
No framework, no database, no server to maintain: a small Python script
assembles plain HTML files, and a host serves them.

## Layout

```
src/layout.html      the shared page shell (head, header, menu, footer)
src/pages/*.html     the body of each page — this is where the words live
src/assets/          stylesheet, script, icons, share image
build.py             stitches layout + pages -> dist/
dist/                the built site (generated; not committed)
```

## Building

```bash
python3 build.py            # writes dist/
python3 build.py --serve    # builds, then serves it on http://localhost:8000
```

No dependencies beyond the Python standard library.

## The editor at /admin/

Writers sign in at `https://www.allergylungclinic.com/admin/` with an email
address and password, write in a normal editor, and save. **Saving does not
publish.** `publish_mode: editorial_workflow` in `src/admin/config.yml` turns
each save into a pull request for review; nothing reaches the live site until
an article is deliberately published. Every page carries Dr. Radhika's
medical registration number, so publishing under her name stays hers to
authorise.

Turning it on, once, in Netlify:

1. **Identity** → *Enable Identity*.
2. **Identity → Registration** → set to **Invite only**, or anyone could sign
   themselves up.
3. **Identity → Services → Git Gateway** → *Enable Git Gateway*. This is what
   lets the editor write to the repository without each writer having a GitHub
   account.
4. **Identity → Emails → Invitation template** → point the link at
   `{{ .SiteURL }}/admin/#invite_token={{ .Token }}`. The default template
   links to the site root, where nothing is listening: the Identity widget is
   loaded on `/admin/` and nowhere else, so an invitee lands on the home page
   with no way to set a password. The **Recovery** template needs the same
   change, or password resets dead-end in the same place.
5. **Identity → Invite users** → add the marketing team's email addresses.

If Netlify Identity is not offered on this site — Netlify has been retiring it
for newer sites — the alternative is Decap's GitHub backend, which works the
same way but requires each writer to have a GitHub account with access to the
repository. Only the `backend:` block at the top of `config.yml` changes.

The editor is `noindex`, disallowed in `robots.txt`, and linked from nowhere.
It is also the only part of the site that loads third-party software: the
public pages stay free of it, which is what the privacy notice promises.

## Day to day in the editor

**Signing in.** `https://www.allergylungclinic.com/admin/`, one *Login with
Netlify Identity* button, email and password. Nothing on the site links there,
so it is worth a bookmark. If the page hangs, wait nine seconds: it prints what
failed — whether the CMS loaded, whether Identity loaded, what `config.yml`
returned — instead of spinning forever. That text is the thing to send on; a
screenshot of a blank page says nothing.

**What is editable.** Knowledge articles, and nothing else. The service pages,
prices, contact details and the booking form live in `src/pages/*.html` and
need a code change. A writer can publish an article without being able to
reword the asthma page by accident.

Most fields explain themselves in the editor. Two do not:

- **Web address** becomes `/knowledge/that-slug/` for good. Changing it after
  publication breaks every link anyone has already shared.
- **Feature this article at the top** belongs to one article at a time. If
  several carry it the newest wins, and the others quietly stop being
  featured.

Images are dragged into the body. They are stored in `src/assets/uploads/` and
served from `/assets/uploads/`, which the build copies across whole.

**Saving, and publishing.** Saving never touches the live site. Each article
becomes a branch — `cms/posts/<slug>` — and a pull request, and moves across
three columns in the editor: Draft, In review, Ready. Publishing merges the
pull request; Netlify rebuilds, and the article is live a couple of minutes
later.

Those columns are a process, not a permission. Anyone invited can move their
own article to Ready and publish it, because `main` accepts any merge. If
approval is meant to be required rather than expected, protect `main` on
GitHub with *require a pull request review before merging*: the Publish button
then fails for anyone who cannot approve, and the article waits in its pull
request until someone signs off.

A reasonable first run: invite one person, have them write a throwaway article
and leave it in Draft, and check that it shows up as an open pull request
without anything appearing on the live site. That exercises Identity, Git
Gateway and the workflow in one go, and nothing is at risk if a step is wrong.

## Writing a post

Posts live in `src/posts/` as Markdown, one file per article. Adding a file is
all that is needed to publish: the page, its card on the Knowledge index, the
sitemap entry and the structured data are all generated from it.

The front matter carries the furniture; the body is ordinary Markdown:

```
---
slug: "dust-allergy"          # becomes /knowledge/dust-allergy/
date: "2026-09-08"            # ISO, used for ordering and structured data
updated: "8 September 2026"   # shown under the title
title: "Is it dust allergy, or something else?"
description: "..."            # the Google result and the WhatsApp card
card_label: "Living in Hyderabad"
card_summary: "..."           # the blurb on the Knowledge index
byline: "Dr. Radhika Sharma · 8 September 2026"
tags: [hyderabad, allergy]    # drives the category filter
featured: true                # optional; one post leads the index
nutshell:                     # optional "in a nutshell" box
  - "A point."
cta:                          # optional buttons at the end
  - label: "Book allergy testing"
    href: "/book/"
    style: solid              # or ghost
sources:                      # optional reference list
  - "A citation."
---

## An ordinary heading

Body text in Markdown. Inline HTML is allowed, which is how the pull quotes
and callout boxes in the existing articles are kept.
```

The build fails loudly if a post is missing a required field or two posts share
a slug, so a broken post never reaches the site.

## Editing content

Page text lives in `src/pages/`. To change the immunotherapy page, edit
`src/pages/immunotherapy.html` and rebuild — the header, footer and menu come
from `src/layout.html` and are applied to every page automatically.

Page titles, meta descriptions and URLs are in the `P` and `ARTICLES` tables
near the top of `build.py`. Adding a page means adding a fragment in
`src/pages/` and one row to the relevant table; the sitemap updates itself.

## Booking

`/book/` collects a few details and hands them to WhatsApp. It has no server
side: the form builds a message, opens `wa.me` with it pre-filled, and the
patient presses send from their own WhatsApp. Nothing is POSTed, nothing is
stored, and the clinic's number stays usable in the normal WhatsApp app.

Automated confirmations *to* the patient would need the WhatsApp Business Cloud
API, which requires a second phone number dedicated to it (a number registered
to the API can no longer be used in the WhatsApp app), Meta business
verification, and message templates approved by Meta. That trade was considered
and declined; if it is ever revisited, the privacy notice needs rewriting first,
because patient data would then pass through a server.

The handler is in `src/assets/site.js`; the clinic number is the
`CLINIC_NUMBER` constant there and in the `wa.me` links in `src/layout.html`.

## Why booking has no live availability

Considered and deliberately declined, September 2026. A booking service
(Cal.com, Zoho Bookings) would prevent two patients requesting the same slot.
It was not adopted for three reasons, the third being the important one:

1. Website availability is only true if the website *is* the clinic diary.
   Phone bookings and walk-ins would diverge from it within days.
2. Patient name, number and reason for visiting would move to a third-party
   processor. The privacy notice currently says, accurately, that nothing is
   collected at all.
3. **Auto-confirmation has a clinical cost here.** Patients must stop
   antihistamines five days before allergy testing. The current flow lets the
   clinic see the request and say "not tomorrow -- stop your cetirizine and
   come Monday". A system that confirms automatically books them in while
   still medicated, and the test is unreadable.

The problem actually being solved is two people wanting the same slot, which
the clinic already resolves in its WhatsApp reply. Revisit if collisions
become weekly rather than occasional.

## Policies

`/privacy/` and `/terms/` are linked from the footer of every page. They
describe what the site actually does — no analytics, no cookies, no database,
Google Fonts as the only third-party request. **If the site ever starts
collecting anything, both pages must be updated before that ships.**

## Deploying

The site is a folder of static files. Any static host works.

**Netlify or Cloudflare Pages** (recommended — free tier, HTTPS included,
redeploys on every push): connect this repository and use

- build command: `python3 build.py`
- publish directory: `dist`

`netlify.toml` already sets this, plus cache and security headers.

**GitHub Pages**: `.github/workflows/deploy.yml` builds and publishes on every
push to the default branch. Enable it under Settings → Pages → Source →
GitHub Actions.

After the first deploy, point the `allergylungclinic.com` DNS at the host and
enable HTTPS.

## Still to do

These need information only the clinic has:

- **A higher-resolution photograph.** The current `src/assets/portrait.webp` is
  400×533, cropped from the only source available. It is sharp enough at the
  size it is displayed, but soft on high-density screens. If a larger original
  exists, crop it 3:4 and replace the file — nothing else needs changing.
- **Fee range.** `priceRange` is omitted from `CLINIC_SCHEMA` rather than
  guessed at. Add it if the clinic is willing to publish a band.
- **Google Business Profile.** Claim it if not already done; for a local clinic
  it typically drives more patients than organic search.
- **Analytics.** Nothing is installed and nothing tracks visitors today. If you
  want visit numbers, add a privacy-friendly tag (Plausible, Fathom) or GA4 to
  `src/layout.html`.
- **A privacy policy**, once anything on the site collects data. Note also that
  the pages currently pull webfonts from Google, which discloses visitor IP
  addresses to Google; self-hosting the two font files removes that.
- **A medico-legal read-through.** The copy is factual and restrained, but NMC
  advertising rules constrain what a registered physician may publish. Worth an
  hour of a healthcare lawyer's time before launch.
