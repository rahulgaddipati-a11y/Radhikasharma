(function () {
  'use strict';

  /* ---------------- mobile menu ---------------- */
  var panel = document.getElementById('panel');
  var menubtn = document.getElementById('menubtn');
  var closebtn = document.getElementById('closebtn');
  var lastFocus = null;

  function focusable() {
    return Array.prototype.slice.call(
      panel.querySelectorAll('a[href], button:not([disabled])')
    ).filter(function (el) { return el.offsetParent !== null; });
  }

  function openPanel() {
    lastFocus = document.activeElement;
    panel.classList.add('open');
    menubtn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    var f = focusable();
    if (f.length) f[0].focus();
  }

  function closePanel() {
    if (!panel.classList.contains('open')) return;
    panel.classList.remove('open');
    menubtn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
    if (lastFocus) lastFocus.focus();
  }

  if (menubtn && panel) {
    menubtn.addEventListener('click', openPanel);
    closebtn.addEventListener('click', closePanel);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { closePanel(); return; }
      if (e.key !== 'Tab' || !panel.classList.contains('open')) return;
      // keep tabbing inside the open menu
      var f = focusable();
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }

  /* ---------------- knowledge category filter ---------------- */
  var pills = document.getElementById('pills');
  if (pills) {
    pills.addEventListener('click', function (e) {
      var a = e.target.closest('a[data-cat]');
      if (!a) return;
      e.preventDefault();
      var cat = a.getAttribute('data-cat');
      pills.querySelectorAll('a').forEach(function (x) { x.classList.toggle('on', x === a); });
      var shown = 0;
      document.querySelectorAll('#cards .card, .feature[data-cat]').forEach(function (c) {
        var cats = (c.getAttribute('data-cat') || '').split(' ');
        var hit = (cat === 'all') || cats.indexOf(cat) > -1;
        c.style.display = hit ? '' : 'none';
        if (hit) shown++;
      });
      document.getElementById('nocards').style.display = shown ? 'none' : 'block';
    });

    var reset = document.querySelector('[data-cat-reset]');
    if (reset) reset.addEventListener('click', function (e) {
      e.preventDefault();
      pills.querySelector('a[data-cat="all"]').click();
    });
  }

  /* ---------------- booking form ----------------
     Deliberately has no server side. The form builds a WhatsApp message and
     hands it to the patient's own WhatsApp to send, so nothing typed here is
     ever transmitted to, or stored by, this site. The chosen time is a
     REQUEST -- the clinic diary is not online, so availability is not checked
     and the appointment exists only once the clinic replies. */
  var bookform = document.getElementById('bookform');
  if (bookform) {
    var CLINIC_NUMBER = '919701864848';
    var date = document.getElementById('bf-date');

    // no past dates, and nothing more than three months out
    var today = new Date();
    var iso = function (d) { return d.toISOString().slice(0, 10); };
    date.min = iso(today);
    var horizon = new Date(today.getTime());
    horizon.setMonth(horizon.getMonth() + 3);
    date.max = iso(horizon);

    var slotInputs = Array.prototype.slice.call(
      bookform.querySelectorAll('input[name=slot]'));
    var slotNote = document.getElementById('slot-note');

    function sameDay(a, b) {
      return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() &&
             a.getDate() === b.getDate();
    }

    // A slot on today's date that has already started cannot be booked. Without
    // this you could sit down at 7pm and request this morning's 11:15.
    function refreshSlots() {
      var now = new Date();
      var isToday = date.value && sameDay(new Date(date.value + 'T00:00:00'), now);
      var minutesNow = now.getHours() * 60 + now.getMinutes();
      var left = 0;

      slotInputs.forEach(function (inp) {
        var gone = isToday && Number(inp.getAttribute('data-start')) <= minutesNow;
        inp.disabled = gone;
        if (gone && inp.checked) inp.checked = false;
        if (!gone) left++;
      });

      // slots this device has already requested, for the chosen date
      var mine = [];
      try {
        mine = JSON.parse(localStorage.getItem('alc.requested') || '[]')
          .filter(function (r) { return r.date === date.value; })
          .map(function (r) { return r.slot; });
      } catch (e) { /* storage unavailable */ }

      slotInputs.forEach(function (inp) {
        inp.closest('.slot').classList.toggle(
          'requested', mine.indexOf(inp.value) > -1 && !inp.disabled);
      });

      if (slotNote) {
        slotNote.hidden = !(isToday && left === 0);
      }
    }

    date.addEventListener('change', refreshSlots);
    refreshSlots();

    var again = document.getElementById('booked-again');
    if (again) again.addEventListener('click', function () {
      document.getElementById('booked').hidden = true;
      bookform.hidden = false;
      bookform.querySelectorAll('input[name=slot]').forEach(function (i) { i.checked = false; });
      refreshSlots();
      bookform.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    function fieldError(el, show, message) {
      var msg = el.closest('.field').querySelector('.err');
      if (msg) {
        if (message) msg.textContent = message;
        msg.hidden = !show;
      }
      if (show) el.setAttribute('aria-invalid', 'true');
      else el.removeAttribute('aria-invalid');
      return !show;
    }

    // clear an error as soon as the field is touched
    ['bf-name', 'bf-age', 'bf-mobile', 'bf-date'].forEach(function (id) {
      var el = document.getElementById(id);
      el.addEventListener('input', function () { fieldError(el, false); });
    });
    bookform.addEventListener('change', function (e) {
      if (e.target.name === 'slot') document.getElementById('err-slot').hidden = true;
    });

    bookform.addEventListener('submit', function (e) {
      e.preventDefault();

      var name = document.getElementById('bf-name');
      var age = document.getElementById('bf-age');
      var mobile = document.getElementById('bf-mobile');
      var slot = bookform.querySelector('input[name=slot]:checked');
      var firstBad = null;
      var ok = true;

      function check(el, valid, message) {
        if (!fieldError(el, !valid, message)) {
          ok = false;
          if (!firstBad) firstBad = el;
        }
      }

      check(name, name.value.trim() !== '');
      check(age, age.value !== '' && +age.value >= 0 && +age.value <= 120);
      // Indian mobile numbers are ten digits; tolerate spaces, dashes and +91
      check(mobile, /^\+?9?1?[\s-]?[6-9]\d{4}[\s-]?\d{5}$/.test(mobile.value.replace(/\s|-/g, '')),
            'Please give a ten-digit mobile number.');

      var dv = date.value;
      var chosen = dv ? new Date(dv + 'T00:00:00') : null;
      var midnight = new Date();
      midnight.setHours(0, 0, 0, 0);
      var past = chosen && chosen < midnight;
      var sunday = chosen && chosen.getDay() === 0;
      var dateMsg = 'Please choose a date.';
      if (past) dateMsg = 'That date has already passed — please pick a day from today onwards.';
      else if (sunday) dateMsg = 'The clinic is closed on Sundays — please pick another day.';
      check(date, !!dv && !past && !sunday, dateMsg);

      refreshSlots();                       // the clock may have moved mid-form
      if (slot && slot.disabled) slot = null;
      if (!slot) {
        var se = document.getElementById('err-slot');
        se.textContent = bookform.querySelector('input[name=slot]:not(:disabled)')
          ? 'Please pick a time.'
          : 'Today\u2019s appointments have finished — please choose another day.';
        se.hidden = false;
        ok = false;
        if (!firstBad) firstBad = bookform.querySelector('input[name=slot]:not(:disabled)') ||
                                  document.getElementById('bf-date');
      }

      if (!ok) {
        if (firstBad) firstBad.focus();
        return;
      }

      var val = function (id) { return document.getElementById(id).value.trim(); };
      var pretty = new Date(dv + 'T00:00:00').toLocaleDateString('en-GB',
        { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

      var lines = [
        "Appointment request — Dr. Radhika's Allergy & Lung Clinic",
        '',
        'Patient: ' + name.value.trim() + ', age ' + age.value.trim(),
        'For: ' + val('bf-who'),
        'Mobile: ' + mobile.value.trim()
      ];
      if (val('bf-city')) lines.push('Area: ' + val('bf-city'));
      lines.push('', 'Preferred: ' + pretty + ', ' + slot.value, '', 'About: ' + val('bf-about'));
      if (val('bf-note')) lines.push('Note: ' + val('bf-note'));

      var waUrl = 'https://wa.me/' + CLINIC_NUMBER + '?text=' +
                  encodeURIComponent(lines.join('\n'));
      window.open(waUrl, '_blank', 'noopener');

      // Remember it on THIS DEVICE only, so the same person is reminded rather
      // than silently re-requesting the same slot. It cannot affect anyone
      // else's view -- there is no shared state without a server.
      try {
        var key = 'alc.requested';
        var mine = JSON.parse(localStorage.getItem(key) || '[]')
          .filter(function (r) { return r.date >= new Date().toISOString().slice(0, 10); });
        mine.push({ date: dv, slot: slot.value });
        localStorage.setItem(key, JSON.stringify(mine));
      } catch (e) { /* private browsing, blocked storage -- not important */ }

      document.getElementById('booked-head').textContent =
        'Thank you, ' + name.value.trim().split(' ')[0] + '.';
      document.getElementById('booked-detail').innerHTML =
        'We have your request for <strong>' + pretty + '</strong> at <strong>' +
        slot.value + '</strong>.';
      document.getElementById('booked-wa').href = waUrl;
      var panel = document.getElementById('booked');
      panel.hidden = false;
      bookform.hidden = true;
      panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
      refreshSlots();
    });
  }

  /* ---------------- allergy self-check ----------------
     A sorting tool, not a diagnostic one. It scores the PATTERN of symptoms
     against the pattern allergy usually takes, and says only whether testing
     is likely to be worthwhile. It never names a condition and never tells
     anyone they do or do not have allergy. Runs entirely in the browser;
     nothing is recorded or transmitted. */
  var checkform = document.getElementById('checkform');
  if (checkform) {
    var QUESTIONS = [
      { q: 'Does your nose or do your eyes <b>itch</b>?',
        help: 'Itch is the single most useful clue. Infections rarely itch.',
        yes: 2 },
      { q: 'Do you sneeze in <b>runs</b> — five, ten, fifteen in a row?',
        help: 'Rather than an occasional one-off sneeze.',
        yes: 2 },
      { q: 'Is the discharge from your nose <b>clear and watery</b>?',
        help: 'As opposed to thick, yellow or green.',
        yes: 1, no: -1 },
      { q: 'Do symptoms reliably start in a <b>particular place, season or situation</b>?',
        help: 'The first hour after waking, while cleaning, outdoors, near an animal, in the monsoon.',
        yes: 2 },
      { q: 'Have symptoms been going on <b>more than six weeks</b>, or do they keep coming back?',
        help: 'Allergy recurs. A single cold resolves and does not return the same way.',
        yes: 1 },
      { q: 'Does anyone in your family have <b>allergy, asthma or eczema</b>?',
        help: 'Allergic conditions run strongly in families.',
        yes: 1 },
      { q: 'Have you had a <b>fever</b> with these symptoms?',
        help: 'Fever points towards infection, not allergy.',
        yes: -2 }
    ];

    var list = document.getElementById('q-list');
    QUESTIONS.forEach(function (item, i) {
      var f = document.createElement('fieldset');
      f.className = 'slots question';
      f.innerHTML =
        '<legend>' + (i + 1) + '. ' + item.q + '</legend>' +
        '<p class="hint" style="margin:0 0 12px">' + item.help + '</p>' +
        '<div class="slotgrid answers">' +
        '<label class="slot"><input type="radio" name="q' + i + '" value="yes"><span>Yes</span></label>' +
        '<label class="slot"><input type="radio" name="q' + i + '" value="no"><span>No</span></label>' +
        '<label class="slot"><input type="radio" name="q' + i + '" value="unsure"><span>Not sure</span></label>' +
        '</div>';
      list.appendChild(f);
    });

    var result = document.getElementById('result');

    checkform.addEventListener('submit', function (e) {
      e.preventDefault();

      var score = 0, answered = 0;
      QUESTIONS.forEach(function (item, i) {
        var picked = checkform.querySelector('input[name=q' + i + ']:checked');
        if (!picked) return;
        answered++;
        if (picked.value === 'yes') score += (item.yes || 0);
        else if (picked.value === 'no') score += (item.no || 0);
      });

      if (answered < QUESTIONS.length) {
        result.hidden = false;
        result.className = 'nutshell';
        result.innerHTML = '<span class="eyebrow">Almost there</span>' +
          '<p style="margin-top:10px">Please answer all ' + QUESTIONS.length +
          ' questions — "Not sure" counts as an answer.</p>';
        result.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }

      var head, body;
      if (score >= 6) {
        head = 'This has the shape of allergy';
        body = '<p>Itch, sneezing in runs, clear discharge and a symptom pattern tied to a place or a season together describe allergic rhinitis more often than anything else. That does not mean you have it — but it does mean <strong>testing is likely to tell you something useful</strong>, because there is a specific question for it to answer.</p>' +
               '<p>The next step is a consultation with skin prick testing, which is read and explained in the same visit.</p>';
      } else if (score >= 2) {
        head = 'Genuinely unclear from the pattern alone';
        body = '<p>Some of what you describe fits allergy and some of it does not. This is the commonest result, and it is exactly the situation a consultation is for — the history is more diagnostic than any single test, and a test ordered without one usually produces a list of positives that mean nothing.</p>' +
               '<p>Worth being seen. Whether you need testing at all is part of what gets decided.</p>';
      } else {
        head = 'This looks less like allergy';
        body = '<p>Fever, thick coloured discharge, no itch and no repeating pattern point away from allergy and towards infection, non-allergic rhinitis, or irritation from dust, smoke or pollution — none of which show up on an allergy test or respond to allergy treatment.</p>' +
               '<p>That is worth knowing, because it saves you paying for testing that would not have helped. If symptoms are persistent or troubling, they still deserve a proper look — they just may not be an allergy problem.</p>';
      }

      result.hidden = false;
      result.className = 'nutshell';
      result.innerHTML =
        '<span class="eyebrow">What this suggests</span>' +
        '<h3 style="margin:10px 0 14px;font-size:1.35rem">' + head + '</h3>' +
        body +
        '<p style="margin-top:16px;font-size:14px;color:var(--muted)"><strong>This is not a diagnosis and not medical advice.</strong> It is a description of how closely your answers match a typical pattern. Only a consultation can tell you what is actually going on.</p>' +
        '<div class="cta-row" style="margin-top:20px">' +
        '<a class="btn" href="/book/">Book an appointment</a>' +
        '<a class="btn ghost" href="/allergy-testing/">How testing works</a>' +
        '</div>';
      result.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  /* ---------------- plain-English glossary ----------------
     The clinical writing on this site is deliberately precise, which means it
     uses real terms. Rather than dilute it, the first appearance of each term
     on a page becomes a tappable button revealing a one-sentence explanation.
     Without JavaScript the text is untouched and still reads correctly. */
  var GLOSSARY = {
    'IgE': 'The antibody behind true, immediate allergy. A test looks for IgE against one specific thing — dust mite, peanut — to see whether your immune system is primed to react to it.',
    'IgG': 'A different antibody, which simply records what you have been exposed to. Making IgG to a food usually just means you eat that food.',
    'wheal': 'The raised pale bump, like a nettle sting, that comes up where a skin test is positive. Its width in millimetres is what gets measured.',
    'spirometry': 'A breathing test. You blow as hard and as long as you can into a tube, and it measures how much air you can move and how fast.',
    'FeNO': 'A test measuring nitric oxide in your breath. Higher levels suggest the particular kind of airway inflammation that responds well to inhaled steroids.',
    'reversibility': 'Spirometry done twice, before and after a reliever inhaler. If the numbers improve markedly the narrowing is reversible, which points towards asthma.',
    'bronchodilator': 'A reliever medicine that opens narrowed airways — the blue inhaler most people recognise.',
    'COPD': 'Chronic obstructive pulmonary disease: long-term airway narrowing that does not fully reverse, most often caused by smoking or years of smoke exposure.',
    'rhinitis': 'Inflammation of the lining of the nose — sneezing, blockage, running, itching.',
    'urticaria': 'Hives. Itchy raised welts that come up and fade again within hours.',
    'anaphylaxis': 'A severe allergic reaction affecting the whole body, coming on within minutes. It needs adrenaline immediately.',
    'eosinophil': 'A type of white blood cell involved in allergic inflammation. A raised count in the blood helps guide asthma treatment.',
    'bronchiectasis': 'Airways permanently widened and damaged, usually after infection, so mucus pools in them and chest infections keep returning.',
    'sublingual': 'Under the tongue — immunotherapy taken at home as drops or a tablet held under the tongue.',
    'subcutaneous': 'Under the skin — immunotherapy given as an injection at the clinic.',
    'allergen': 'The specific thing your immune system reacts to: a house dust mite, a pollen, a food, a drug.',
    'biologics': 'Injected treatments that block one specific step in the allergic pathway. Used in severe asthma when inhalers are not enough.',
    'peak flow': 'A simple handheld meter measuring how fast you can blow air out. Useful for tracking asthma at home day to day.',
    'montelukast': 'A tablet blocking one of the chemical messengers in allergic inflammation. Used in asthma and allergic rhinitis.',
    'antihistamine': 'A tablet blocking histamine, the chemical released during an allergic reaction. It relieves the symptom without changing the underlying allergy.',
    'histamine': 'The chemical released by immune cells during an allergic reaction — the cause of itch, swelling and a streaming nose.',
    'sensitisation': 'Having IgE against something: your immune system is primed to react, even though you may have no symptoms at all. Sensitisation is not the same as allergy.'
  };

  (function glossary() {
    var main = document.querySelector('main');
    if (!main) return;

    // longest first, so "peak flow" wins over "flow" and "IgE" is not eaten by a
    // shorter partial match
    var terms = Object.keys(GLOSSARY).sort(function (a, b) { return b.length - a.length; });
    var done = {};
    var SKIP = /^(A|BUTTON|H1|H2|H3|H4|CODE|LEGEND|LABEL|CITE|SUMMARY)$/;

    terms.forEach(function (term) {
      var re = new RegExp('(^|[^\\w-])(' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')(?![\\w-])',
                          term === term.toLowerCase() ? 'i' : '');
      var walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
        acceptNode: function (node) {
          if (done[term]) return NodeFilter.FILTER_REJECT;
          for (var el = node.parentElement; el && el !== main; el = el.parentElement) {
            if (SKIP.test(el.tagName) || el.classList.contains('gloss') ||
                el.classList.contains('nutshell')) return NodeFilter.FILTER_REJECT;
          }
          return re.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        }
      });

      var node = walker.nextNode();
      if (!node) return;
      var m = node.nodeValue.match(re);
      if (!m) return;

      var at = node.nodeValue.indexOf(m[2], m.index);
      var after = node.splitText(at);
      after.splitText(m[2].length);

      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'gloss';
      btn.setAttribute('aria-expanded', 'false');
      btn.textContent = after.nodeValue;

      var def = document.createElement('span');
      def.className = 'glossdef';
      def.hidden = true;
      def.textContent = GLOSSARY[term];

      after.parentNode.replaceChild(btn, after);

      // Append the definition INSIDE the paragraph, as its last child. A span is
      // valid phrasing content there, so this neither splits the sentence nor
      // sits between two <p> elements -- which would silently break the
      // ".prose p + p" rule that spaces paragraphs apart.
      var host = btn.closest('p, li');
      if (host) host.appendChild(def);
      else btn.parentNode.insertBefore(def, btn.nextSibling);

      btn.addEventListener('click', function () {
        var open = btn.getAttribute('aria-expanded') === 'true';
        btn.setAttribute('aria-expanded', open ? 'false' : 'true');
        def.hidden = open;
      });

      done[term] = true;
    });
  })();

  /* ---------------- editor invitations ----------------
     Netlify Identity sends invite and password-reset links to the site root
     with the token in the hash. Rather than load the Identity widget on every
     public page -- which would put a third-party script in front of patients,
     and make the privacy notice untrue -- forward those links to /admin/,
     where the widget actually lives. */
  if (/\b(invite_token|recovery_token|confirmation_token|email_change_token)=/
        .test(location.hash) && location.pathname !== '/admin/') {
    location.replace('/admin/' + location.hash);
  }

  /* ---------------- legacy #/hash URLs -> real paths ----------------
     The first version of this site was a single page with hash routes.
     Anything already shared on WhatsApp still points at #/immunotherapy
     and friends, so honour those links instead of dropping people home. */
  var LEGACY = {
    '#/': '/',
    '#/allergy-testing': '/allergy-testing/',
    '#/lung-tests': '/lung-tests/',
    '#/immunotherapy': '/immunotherapy/',
    '#/asthma-lung': '/asthma-lung/',
    '#/smoking-cessation': '/smoking-cessation/',
    '#/first-visit': '/first-visit/',
    '#/knowledge': '/knowledge/',
    '#/knowledge/dust-allergy': '/knowledge/dust-allergy/',
    '#/knowledge/igg-tests': '/knowledge/igg-tests/',
    '#/knowledge/homeopathy': '/knowledge/homeopathy/',
    '#/knowledge/post-tb': '/knowledge/post-tb/',
    '#/knowledge/child-nebuliser': '/knowledge/child-nebuliser/',
    '#/knowledge/parthenium': '/knowledge/parthenium/',
    '#/knowledge/monsoon-asthma': '/knowledge/monsoon-asthma/'
  };
  var target = LEGACY[location.hash];
  if (target && target !== location.pathname) location.replace(target);
})();
