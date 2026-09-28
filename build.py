#!/usr/bin/env python3
"""Build the static site for Dr. Radhika's Allergy & Lung Clinic.

Reads src/layout.html + src/pages/*.html and writes a deployable tree to
dist/. Every page gets a real URL of its own, its own <title>, description,
canonical and structured data.

    python3 build.py            # -> dist/
    python3 build.py --serve    # build, then serve dist/ on :8000
"""

import glob
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import date, datetime

SITE = "https://www.allergylungclinic.com"
CLINIC = "Dr. Radhika's Allergy & Lung Clinic"
PHONE = "+91-97018-64848"
BUILT = date.today().isoformat()

SRC, PAGES, DIST = "src", "src/pages", "dist"

ADDRESS = {
    "@type": "PostalAddress",
    "streetAddress": "2nd Floor, Youniq, Above Labonel Fine Baking, 1335/A, Road No. 45, Jubilee Hills",
    "addressLocality": "Hyderabad",
    "addressRegion": "Telangana",
    "postalCode": "500033",
    "addressCountry": "IN",
}

PHYSICIAN = {
    "@type": "Physician",
    "name": "Dr. Radhika Sharma",
    "medicalSpecialty": ["Allergy", "Pulmonary"],
    "alumniOf": "Christian Medical College, Vellore",
    "hasCredential": [
        "MD, Respiratory Medicine",
        "Diploma in Allergy & Asthma (D.A.A), CMC Vellore",
        "Fellowship in Interventional Pulmonology",
    ],
    "image": SITE + "/assets/portrait.webp",
    # The same doctor is searched for under all of these words. Listing them
    # here is a statement of what she treats, not a claim of extra services.
    "knowsAbout": [
        "Allergy testing", "Allergen immunotherapy", "Allergic rhinitis",
        "Chronic urticaria", "Food allergy", "Drug allergy", "Atopic eczema",
        "Asthma", "COPD", "Bronchiectasis", "Chronic cough",
        "Post-tuberculosis lung disease", "Pulmonary function testing",
        "Sleep-disordered breathing", "Smoking cessation",
        "Pneumonia", "Bronchitis", "Interstitial lung disease",
        "Pulmonary hypertension", "Pulmonary embolism", "Lung cancer screening",
    ],
}

CLINIC_SCHEMA = {
    "@context": "https://schema.org",
    "@type": "MedicalClinic",
    "name": CLINIC,
    "url": SITE + "/",
    "telephone": PHONE,
    "image": SITE + "/assets/og.png",
    "medicalSpecialty": ["Allergy", "Pulmonary"],
    "address": ADDRESS,
    "hasMap": "https://maps.google.com/?q=Youniq,+Road+No.+45,+Jubilee+Hills,+Hyderabad+500033",
    # Decoded from the clinic's Google Business Profile Plus Code 7J9WCCG5+6C
    # (short form CCG5+6C). Verified by re-encoding: the point round-trips to the
    # same code, in a 14m cell on Road No. 45.
    "geo": {"@type": "GeoCoordinates", "latitude": 17.425562, "longitude": 78.408563},
    "openingHoursSpecification": [{
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "opens": "11:00",
        "closes": "18:00",
    }],
    # Only services the site itself describes. A clinic's structured data is
    # read as a claim about what it does, so it lists nothing the pages do not.
    "availableService": [
        {"@type": "MedicalTest", "name": "Skin prick allergy testing"},
        {"@type": "MedicalTest", "name": "Specific IgE blood testing"},
        {"@type": "MedicalTest", "name": "Component-resolved allergy diagnostics"},
        {"@type": "MedicalTest", "name": "Spirometry with bronchodilator reversibility"},
        {"@type": "MedicalTest", "name": "FeNO (exhaled nitric oxide) testing"},
        {"@type": "MedicalTest", "name": "Six-minute walk test"},
        {"@type": "MedicalTest", "name": "Drug and food allergy evaluation"},
        {"@type": "MedicalTherapy", "name": "Allergen immunotherapy"},
        {"@type": "MedicalTherapy", "name": "Smoking cessation programme"},
        {"@type": "MedicalTherapy", "name": "Sleep apnoea and snoring assessment"},
        {"@type": "MedicalTest", "name": "Lung cancer screening"},
        {"@type": "MedicalProcedure", "name": "Bronchoscopy"},
    ],
    "areaServed": [
        {"@type": "Place", "name": "Jubilee Hills, Hyderabad"},
        {"@type": "City", "name": "Hyderabad"},
    ],
    "employee": PHYSICIAN,
}

# slug -> (url path, source fragment, <title>, meta description, nav section)
P = [
    ("/", "home",
     CLINIC,
     "Consultant-led allergy testing, immunotherapy, asthma and lung care in Jubilee Hills, "
     "Hyderabad. Proper testing first, then treatment aimed at the cause.",
     "/"),

    ("/allergy-testing/", "allergy-testing",
     "Allergy Testing · " + CLINIC,
     "Skin prick testing and specific IgE blood tests in Jubilee Hills, Hyderabad — read against "
     "your history and explained in the same visit by Dr. Radhika Sharma.",
     "/allergy-testing/"),

    ("/lung-tests/", "lung-tests",
     "Breathing & Lung Tests · " + CLINIC,
     "Spirometry with reversibility, FeNO and lung function testing in Jubilee Hills, Hyderabad. "
     "What each breathing test measures, and what the numbers actually mean.",
     "/lung-tests/"),

    ("/immunotherapy/", "immunotherapy",
     "Immunotherapy · " + CLINIC,
     "Allergen immunotherapy in Jubilee Hills, Hyderabad: the only treatment that changes the allergy rather than "
     "masking it. Who it suits, what it involves, and when the answer is no.",
     "/immunotherapy/"),

    ("/asthma-lung/", "asthma-lung",
     "Asthma & Lung Disorders · " + CLINIC,
     "Asthma, COPD, bronchiectasis and post-infective airway disease, seen by a chest specialist "
     "in Jubilee Hills, Hyderabad. Measured rather than guessed "
     "at — consultant respiratory care in Jubilee Hills, Hyderabad.",
     "/asthma-lung/"),

    ("/smoking-cessation/", "smoking-cessation",
     "Smoking Cessation · " + CLINIC,
     "A smoking cessation programme in Jubilee Hills, Hyderabad. Come and talk about tobacco "
     "whether or not you have decided to stop — medication and support, no lecture.",
     "/"),

    ("/first-visit/", "first-visit",
     "Your First Visit · " + CLINIC,
     "What happens at your first appointment: allow about an hour, stop antihistamines five days "
     "before allergy testing, and bring earlier reports. Jubilee Hills, Hyderabad.",
     "/"),

    ("/knowledge/", "knowledge",
     "Knowledge & Updates · " + CLINIC,
     "Plain explanations of allergy, asthma and lung disease from Dr. Radhika Sharma, MD — written "
     "in clinic, with the Hyderabad detail that general websites leave out.",
     "/knowledge/"),

    ("/about/", "about",
     "About Dr. Radhika Sharma · Allergy & Lung Clinic",
     "Dr. Radhika Sharma, MD (Respiratory Medicine), Diploma in Allergy & Asthma from CMC Vellore. "
     "Consultant Pulmonologist and Allergy Specialist in Jubilee Hills, Hyderabad.",
     "/about/"),

    ("/sleep/", "sleep",
     "Sleep Apnoea & Snoring · " + CLINIC,
     "Snoring, daytime tiredness and sleep apnoea assessed in Jubilee Hills, Hyderabad. "
     "How sleep-disordered breathing is diagnosed, and what CPAP and the alternatives involve.",
     "/sleep/"),

    ("/allergy-check/", "allergy-check",
     "Is It Allergy? A Two-Minute Check · " + CLINIC,
     "Seven questions about the pattern of your symptoms, to tell you whether allergy testing "
     "is likely to be worth your time. Not a diagnosis \u2014 a sorting tool.",
     "/allergy-testing/"),

    ("/book/", "book",
     "Book an Appointment · " + CLINIC,
     "Book an appointment at Dr. Radhika's Allergy & Lung Clinic, Jubilee Hills, Hyderabad. "
     "Fill in the form and it opens WhatsApp with your details ready to send.",
     "/"),

    ("/privacy/", "privacy",
     "Privacy Notice · " + CLINIC,
     "What this website does with your information: no accounts, no tracking, no database. "
     "The booking form sends nothing to us \u2014 you send it yourself from your own WhatsApp.",
     "/"),

    ("/terms/", "terms",
     "Terms & Medical Disclaimer · " + CLINIC,
     "General information, not medical advice. Reading this site does not create a "
     "doctor-patient relationship. Emergency guidance and practitioner registration details.",
     "/"),

    ("/contact/", "contact",
     "Contact & Directions · " + CLINIC,
     "Dr. Radhika's Allergy & Lung Clinic, 2nd Floor Youniq, Road No. 45, Jubilee Hills, Hyderabad "
     "500033. Mon–Sat, 11 am – 6 pm. Book on WhatsApp: +91 97018 64848.",
     "/contact/"),
]

POSTS = "src/posts"


def load_posts():
    """Read src/posts/*.md -- front matter plus Markdown body.

    One file is one article. Nothing else needs editing to publish: the page,
    its entry on the Knowledge index, the sitemap and the structured data are
    all produced from here.
    """
    import markdown as md_lib
    import yaml

    posts = []
    for path in sorted(glob.glob(os.path.join(POSTS, "*.md"))):
        raw = open(path, encoding="utf-8").read()
        if not raw.startswith("---"):
            raise SystemExit("%s is missing its front matter block" % path)
        _, front, body = raw.split("---", 2)
        post = yaml.safe_load(front) or {}

        missing = [k for k in ("slug", "title", "description", "date", "card_label",
                               "card_summary") if not post.get(k)]
        if missing:
            raise SystemExit("%s is missing: %s" % (path, ", ".join(missing)))

        # The editor writes the publication date unquoted, so YAML hands it
        # back as a date object, while the posts written by hand quote it and
        # come back as a string. Sorting a mix of the two is a TypeError, and a
        # date object cannot be serialised into the page's structured data
        # either. One ISO string from here on, however the file was written.
        stamp = post["date"]
        if isinstance(stamp, datetime):
            stamp = stamp.date()
        if isinstance(stamp, date):
            post["date"] = stamp.isoformat()
        else:
            stamp = str(stamp).strip()
            try:
                date.fromisoformat(stamp)
            except ValueError:
                raise SystemExit(
                    "%s has a publication date this build cannot read: %r.\n"
                    "It has to look like 2026-09-28." % (path, post["date"]))
            post["date"] = stamp

        # The editor's description box is several lines tall, so a writer can
        # press Enter in it. That newline would otherwise be carried into the
        # meta description and the structured data, where it means nothing.
        post["description"] = " ".join(post["description"].split())

        # no "smarty": converting the storage format must not quietly restyle
        # the doctor's punctuation
        post["html"] = md_lib.markdown(
            body.strip(), extensions=["extra", "sane_lists"])
        post["path"] = "/knowledge/%s/" % post["slug"]
        post["source"] = path
        posts.append(post)

    slugs = [p["slug"] for p in posts]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("two posts share a slug")
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def render_article(post):
    """Assemble one article from its front matter and Markdown body."""
    out = ['<section class="first"><div class="wrap">',
           '  <div class="prose" style="max-width:74ch">',
           '    <p class="crumb"><a href="/knowledge/">Knowledge</a> \u203a %s</p>'
           % esc_text(post["card_label"]),
           '    <h1 style="font-size:clamp(2rem,4.4vw,3rem);margin-top:16px">%s</h1>'
           % post["title"],
           '    <p class="artmeta">Dr. Radhika Sharma, MD (Respiratory Medicine), '
           'D.A.A (CMC Vellore) \u00b7 <b>Last updated %s</b></p>' % esc_text(post["updated"])]

    if post.get("nutshell"):
        out.append('    <div class="nutshell">')
        out.append('      <span class="eyebrow">In a nutshell</span>')
        out.append("      <ul>")
        out += ["        <li>%s</li>" % b for b in post["nutshell"]]
        out.append("      </ul>")
        out.append("    </div>")
    out.append("  </div>")
    out.append("</div></section>")

    out.append('<section><div class="wrap"><div class="prose" style="max-width:74ch">')
    out.append(post["html"])

    if post.get("cta"):
        out.append('  <div class="cta-row" style="margin-top:40px">')
        for c in post["cta"]:
            cls = "btn ghost" if c.get("style") == "ghost" else "btn"
            out.append('    <a class="%s" href="%s">%s</a>' % (cls, c["href"], c["label"]))
        out.append("  </div>")

    out.append('  <div class="refs">')
    out.append("    <h4>Sources</h4>")
    for r in post.get("sources", []):
        out.append("    <p>%s</p>" % r)
    out.append('    <p style="margin-top:12px">General information, not a substitute for '
               "consultation. Reviewed by Dr. Radhika Sharma, September 2026.</p>")
    out.append("  </div>")
    out.append("</div></div></section>")
    return "\n".join(out)


def fingerprint_assets():
    """Copy assets to dist, giving site.css and site.js content-hashed names.

    Without this the filenames never change, so the long immutable cache
    header served for /assets/* pins every returning visitor to whichever
    stylesheet they downloaded first -- new HTML, year-old CSS.
    """
    src_dir = os.path.join(SRC, "assets")
    out_dir = os.path.join(DIST, "assets")
    shutil.copytree(src_dir, out_dir)

    renamed = {}
    for name in ("site.css", "site.js"):
        path = os.path.join(out_dir, name)
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()[:10]
        stem, ext = os.path.splitext(name)
        hashed = "%s.%s%s" % (stem, digest, ext)
        os.rename(path, os.path.join(out_dir, hashed))
        renamed["/assets/" + name] = "/assets/" + hashed
    return renamed


def esc_text(s):
    """Escape text destined for HTML content (not an attribute)."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc(s):
    """Escape for an HTML attribute value."""
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def schema_for(path, title, desc, art_date=None):
    if path in ("/", "/contact/"):
        return CLINIC_SCHEMA
    if path == "/about/":
        doc = dict(PHYSICIAN)
        doc.update({"@context": "https://schema.org", "url": SITE + path,
                    "address": ADDRESS, "telephone": PHONE, "worksFor": {
                        "@type": "MedicalClinic", "name": CLINIC, "url": SITE + "/"}})
        return doc
    if art_date:
        return {
            "@context": "https://schema.org",
            "@type": "MedicalWebPage",
            "headline": title.split(" · ")[0],
            "description": desc,
            "url": SITE + path,
            "datePublished": art_date,
            "dateModified": art_date,
            "inLanguage": "en",
            "author": PHYSICIAN,
            "publisher": {"@type": "MedicalClinic", "name": CLINIC, "url": SITE + "/"},
            "breadcrumb": {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Knowledge",
                     "item": SITE + "/knowledge/"},
                    {"@type": "ListItem", "position": 3, "name": title.split(" · ")[0]},
                ],
            },
        }
    return {
        "@context": "https://schema.org",
        "@type": "MedicalWebPage",
        "name": title.split(" · ")[0],
        "description": desc,
        "url": SITE + path,
        "inLanguage": "en",
        "about": {"@type": "MedicalClinic", "name": CLINIC, "url": SITE + "/"},
    }


def mark_nav(html, section):
    """Give the current section's nav link its underline, and aria-current."""
    def sub(m):
        href = m.group(1)
        if href != section:
            return m.group(0)
        return '<a href="%s" class="on" aria-current="page">' % href
    return re.sub(r'<a href="(/[\w/-]*)">', sub, html)


FEATURE_ART = ('<div class="art"><svg width="150" height="150" viewBox="0 0 150 150" '
    'fill="none" aria-hidden="true"><circle cx="75" cy="75" r="52" stroke="#006E7A" '
    'stroke-width="1" opacity=".5"/><circle cx="75" cy="75" r="34" stroke="#006E7A" '
    'stroke-width="1" opacity=".7"/><circle cx="75" cy="75" r="16" fill="#006E7A" '
    'opacity=".18"/><circle cx="46" cy="58" r="3" fill="#006E7A"/><circle cx="104" cy="63" '
    'r="4" fill="#006E7A" opacity=".7"/><circle cx="92" cy="103" r="2.5" fill="#006E7A"/>'
    '<circle cx="55" cy="98" r="3.5" fill="#006E7A" opacity=".6"/></svg></div>')


# The Knowledge filter buttons are built from the tags the articles actually
# carry. A tag nobody uses leaves no empty button behind, and a tag a writer
# invents in the editor gets a button without anyone editing this file. The map
# only exists for the five whose button says something other than the tag.
TAG_LABELS = {
    "allergy": "Allergy",
    "lungs": "Asthma & Lungs",
    "tests": "Tests Explained",
    "hyderabad": "Living in Hyderabad",
    "parents": "For Parents",
}
TAG_ORDER = ["allergy", "lungs", "tests", "hyderabad", "parents"]


def tag_label(tag):
    """The button text for a tag, made readable if it is a new one."""
    if tag in TAG_LABELS:
        return TAG_LABELS[tag]
    words = tag.replace("-", " ").strip()
    return words[:1].upper() + words[1:]


def knowledge_filters(posts):
    """The filter row: All, the five familiar tags in their usual order, then
    anything new in alphabetical order so it cannot jump the queue."""
    used = set()
    for post in posts:
        for tag in post.get("tags") or []:
            used.add(tag)

    out = ['<a href="/knowledge/" class="on" data-cat="all">All</a>']
    for tag in [t for t in TAG_ORDER if t in used] + \
               sorted(t for t in used if t not in TAG_LABELS):
        out.append('<a href="/knowledge/" data-cat="%s">%s</a>'
                   % (esc(tag), esc_text(tag_label(tag))))
    return "\n        ".join(out)


def knowledge_cards(posts):
    """The Knowledge index, built from the posts themselves.

    Publishing is one file in src/posts/: the article page, this listing entry,
    the sitemap and the structured data all follow from it.
    """
    feature = next((p for p in posts if p.get("featured")), posts[0] if posts else None)
    out = []

    if feature:
        out.append('<a class="feature" href="%s" data-cat="%s">'
                   % (feature["path"], " ".join(feature.get("tags", []))))
        out.append("  " + FEATURE_ART)
        out.append('  <div class="body">')
        out.append('    <span class="cat">%s</span>' % esc_text(feature["card_label"]))
        out.append("    <h3>%s</h3>" % feature["title"])
        out.append("    <p>%s</p>" % feature["card_summary"])
        out.append('    <p class="artmeta" style="margin-top:22px">%s</p>'
                   % (feature.get("byline") or "Dr. Radhika Sharma"))
        out.append("  </div>")
        out.append("</a>")

    rest = [p for p in posts if p is not feature]
    if rest:
        out.append('<div class="cards" id="cards">')
        for post in rest:
            out.append('  <a class="card" href="%s" data-cat="%s">'
                       % (post["path"], " ".join(post.get("tags", []))))
            out.append('    <span class="cat">%s</span>' % esc_text(post["card_label"]))
            out.append("    <h3>%s</h3>" % post["title"])
            out.append("    <p>%s</p>" % post["card_summary"])
            out.append('    <span class="meta">%s</span>'
                       % (post.get("byline") or "Dr. Radhika Sharma"))
            out.append("  </a>")
        out.append("</div>")
    return "\n".join(out)


def render(layout, path, frag, title, desc, section, art_date=None, body=None):
    if body is None:
        body = open(os.path.join(PAGES, frag + ".html"), encoding="utf-8").read()
    canonical = SITE + path
    html = layout
    for key, val in [
        ("{{TITLE}}", esc(title)),
        ("{{OG_TITLE}}", esc(title.split(" · ")[0] if path != "/" else title)),
        ("{{DESCRIPTION}}", esc(desc)),
        ("{{CANONICAL}}", canonical),
        ("{{BASE}}", SITE),
        ("{{OG_TYPE}}", "article" if art_date else "website"),
        ("{{SCHEMA}}", json.dumps(schema_for(path, title, desc, art_date),
                                  ensure_ascii=False, separators=(",", ":"))),
    ]:
        html = html.replace(key, val)
    html = html.replace("{{BODY}}", body)      # last: body may contain braces
    html = mark_nav(html, section)

    out = os.path.join(DIST, path.strip("/"), "index.html") if path != "/" \
        else os.path.join(DIST, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(html)
    return out, len(html)


def render_404(layout):
    body = open(os.path.join(PAGES, "404.html"), encoding="utf-8").read()
    html = layout
    for key, val in [
        ("{{TITLE}}", esc("Page not found · " + CLINIC)),
        ("{{OG_TITLE}}", esc("Page not found")),
        ("{{DESCRIPTION}}", esc("That page isn't here. Everything on the site is one click away.")),
        ("{{CANONICAL}}", SITE + "/404.html"),
        ("{{BASE}}", SITE),
        ("{{OG_TYPE}}", "website"),
        ("{{SCHEMA}}", json.dumps({"@context": "https://schema.org", "@type": "WebPage",
                                   "name": "Page not found"}, separators=(",", ":"))),
    ]:
        html = html.replace(key, val)
    html = html.replace("{{BODY}}", body)
    # a 404 must not be indexed whatever URL served it
    html = html.replace("<title>", '<meta name="robots" content="noindex">\n<title>', 1)
    open(os.path.join(DIST, "404.html"), "w", encoding="utf-8").write(html)


def write_extras(paths):
    urls = "".join(
        '  <url><loc>%s%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq>'
        '<priority>%s</priority></url>\n'
        % (SITE, p, BUILT, "monthly" if p != "/" else "weekly", "1.0" if p == "/" else "0.8")
        for p in paths)
    open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % urls)

    open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: %s/sitemap.xml\n" % SITE)

    open(os.path.join(DIST, "site.webmanifest"), "w", encoding="utf-8").write(json.dumps({
        "name": CLINIC,
        "short_name": "Allergy & Lung Clinic",
        "start_url": "/",
        "display": "browser",
        "background_color": "#FDFBF7",
        "theme_color": "#FDFBF7",
        "icons": [
            {"src": "/assets/icon-180.png", "sizes": "180x180", "type": "image/png"},
            {"src": "/assets/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }, indent=2) + "\n")


def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    layout = open(os.path.join(SRC, "layout.html"), encoding="utf-8").read()
    for plain, hashed in fingerprint_assets().items():
        layout = layout.replace(plain, hashed)

    posts = load_posts()

    written = []
    for path, frag, title, desc, section in P:
        page_body = None
        if frag == "knowledge":
            page_body = open(os.path.join(PAGES, "knowledge.html"), encoding="utf-8") \
                .read().replace("<!-- POSTS -->", knowledge_cards(posts)) \
                .replace("<!-- FILTERS -->", knowledge_filters(posts))
        out, n = render(layout, path, frag, title, desc, section, body=page_body)
        written.append(path)
        print("  %-34s %6d  %s" % (path, n, out))
    for post in posts:
        out, n = render(layout, post["path"], None,
                        post["title"] + " \u00b7 Knowledge", post["description"],
                        "/knowledge/", post["date"], body=render_article(post))
        written.append(post["path"])
        print("  %-34s %6d  %s" % (post["path"], n, out))

    write_extras(written)

    # the staff editor, served as-is (it is a React app, not a built page)
    admin_src = os.path.join(SRC, "admin")
    if os.path.isdir(admin_src):
        shutil.copytree(admin_src, os.path.join(DIST, "admin"))

    # 404 gets the full shell, so a stray URL still shows the nav and the phone number
    render_404(layout)

    print("\n%d pages -> %s/" % (len(written), DIST))

    if "--serve" in sys.argv:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIST)
        print("serving %s/ on http://localhost:8000 — Ctrl-C to stop" % DIST)
        try:
            http.server.HTTPServer(("", 8000), handler).serve_forever()
        except KeyboardInterrupt:
            print()


if __name__ == "__main__":
    main()
