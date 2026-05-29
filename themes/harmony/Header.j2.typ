{% set lang = locale.language_iso_639_1 %}
{% set L = {
  "details":  "Details"   if lang == "en" else "Contacto",
  "skills":   "Skills"    if lang == "en" else "Habilidades",
  "langs":    "Languages" if lang == "en" else "Idiomas",
} %}
{% set phone_display = cv.phone.replace("tel:", "").replace("-", " ") if cv.phone and cv.phone.startswith("tel:") else (cv.phone or "") %}
{% set website_str = cv.website | string if cv.website else "" %}
{% set website_display = website_str.replace("https://", "").replace("http://", "").rstrip("/") %}
// ─── SIDEBAR ─────────────────────────────────────────────────────────────────
#place(
  top + left,
  dx: -6.2cm,
  dy: -0.75cm,
  block(
    width: 5.9cm,
    height: 29.7cm,
    inset: (x: 0.4cm, top: 0.7cm, bottom: 0.5cm),
    fill: none,
  )[
    #set text(fill: rgb(60, 60, 60), font: "Raleway", size: 8pt)

    // ── PHOTO ─────────────────────────────────────────────────────────────
    #align(center)[
      #block(
        width: 2.2cm, height: 2.2cm,
        clip: true, radius: 50%,
        stroke: 1.5pt + rgb(215, 215, 215),
        fill: rgb(215, 215, 215),
      )[
{% if cv.photo %}
        #image("{{ cv.photo }}", width: 2.2cm, height: 2.2cm, fit: "cover")
{% else %}
        #align(center + horizon)[
          #stack(
            spacing: 0.1cm,
            circle(radius: 0.43cm, fill: rgb(165, 165, 165)),
            ellipse(width: 1.22cm, height: 0.65cm, fill: rgb(165, 165, 165)),
          )
        ]
{% endif %}
      ]
    ]

    #v(0.18cm)

    // ── NAME ──────────────────────────────────────────────────────────────
    #align(center)[
      #text(size: 13.5pt, weight: "bold", fill: rgb(30, 30, 30))[
        {{ cv.plain_name if cv.plain_name else cv.name }}
      ]
    ]
{% if cv.headline %}
    #v(0.05cm)
    #align(center)[
      #text(size: 8.5pt, fill: rgb(198, 138, 42))[{{ cv.headline }}]
    ]
{% endif %}

    #v(0.18cm)

    // ── SIDEBAR SECTION LABEL ─────────────────────────────────────────────
    #let sidebar-label(txt) = {
      text(size: 9.5pt, weight: "semibold", fill: rgb(198, 138, 42))[#txt]
      v(0.04cm)
      line(length: 100%, stroke: 0.5pt + rgb(225, 192, 125))
      v(0.09cm)
    }

    // ── DETAILS (contact) ──────────────────────────────────────────────────
    #sidebar-label[{{ L.details }}]
{% if cv.location %}
    #block(spacing: 0.1cm)[
      #text(weight: "bold", fill: rgb(40, 40, 40), size: 7.5pt)[Address]
      #linebreak()
      #text(fill: rgb(90, 90, 90), size: 7.5pt)[{{ cv.location }}]
    ]
{% endif %}
{% if phone_display %}
    #block(spacing: 0.1cm)[
      #text(weight: "bold", fill: rgb(40, 40, 40), size: 7.5pt)[Phone]
      #linebreak()
      #text(fill: rgb(90, 90, 90), size: 7.5pt)[#("{{ phone_display }}")]
    ]
{% endif %}
    #block(spacing: 0.1cm)[
      #text(weight: "bold", fill: rgb(40, 40, 40), size: 7.5pt)[Email]
      #linebreak()
      #text(fill: rgb(90, 90, 90), size: 7pt)[#("{{ cv.email }}")]
    ]
{% for sn in cv.social_networks or [] %}
{% if sn.network == "LinkedIn" %}
    #block(spacing: 0.1cm)[
      #text(weight: "bold", fill: rgb(40, 40, 40), size: 7.5pt)[LinkedIn]
      #linebreak()
      #text(fill: rgb(90, 90, 90), size: 7.5pt)[{{ sn.username }}]
    ]
{% elif sn.network == "GitHub" %}
    #block(spacing: 0.1cm)[
      #text(weight: "bold", fill: rgb(40, 40, 40), size: 7.5pt)[GitHub]
      #linebreak()
      #text(fill: rgb(90, 90, 90), size: 7.5pt)[{{ sn.username }}]
    ]
{% endif %}
{% endfor %}
{% if website_display %}
    #block(spacing: 0.1cm)[
      #text(weight: "bold", fill: rgb(40, 40, 40), size: 7.5pt)[Website]
      #linebreak()
      #text(fill: rgb(90, 90, 90), size: 7pt)[#("{{ website_display }}")]
    ]
{% endif %}

    // ── SKILLS ────────────────────────────────────────────────────────────
{% for section in cv.rendercv_sections %}
{% if section.snake_case_title == "skills" %}
    #v(0.15cm)
    #sidebar-label[{{ L.skills }}]
    {% for entry in section.entries %}
    {% if entry is string %}
    #block(spacing: 0.08cm)[#text(fill: rgb(70, 70, 70))[{{ entry }}]]
    {% else %}
    #block(spacing: 0.13cm)[
      #text(weight: "semibold", fill: rgb(40, 40, 40), size: 7.5pt)[{{ entry.label }}]
      #linebreak()
      #text(fill: rgb(100, 100, 100), size: 7pt)[{{ entry.details }}]
    ]
    {% endif %}
    {% endfor %}
{% endif %}
{% endfor %}

    // ── EDUCATION ─────────────────────────────────────────────────────────────
{% for section in cv.rendercv_sections %}
{% if section.snake_case_title == "education" %}
    #v(0.15cm)
    #sidebar-label[{{ "Education" if lang == "en" else "Educación" }}]
    {% for entry in section.entries or [] %}
    #block(spacing: 0.12cm)[
      #text(weight: "semibold", fill: rgb(40, 40, 40), size: 7.5pt)[{{ entry.institution }}]
      #linebreak()
      #text(fill: rgb(90, 90, 90), size: 7pt)[{{ entry.area }}]
      #linebreak()
      #text(fill: rgb(155, 150, 145), size: 7pt)[{{ entry.start_date }} – {{ entry.end_date }}]
    ]
    {% endfor %}
{% endif %}
{% endfor %}

    // ── LANGUAGES ─────────────────────────────────────────────────────────
{% for section in cv.rendercv_sections %}
{% if section.snake_case_title == "languages" %}
    #v(0.15cm)
    #sidebar-label[{{ L.langs }}]
    #let dots(lvl) = {
      let n = if lvl.contains("C2") or lvl.contains("Native") or lvl.contains("Nativo") { 5 }
        else if lvl.contains("C1") or lvl.contains("Advanced") { 4 }
        else if lvl.contains("B2") or lvl.contains("Upper") { 3 }
        else if lvl.contains("B1") or lvl.contains("Intermediate") { 2 }
        else { 1 }
      text(size: 8.5pt, fill: rgb(198, 138, 42))[#range(n).map(_ => "●").join("")]
      text(size: 8.5pt, fill: rgb(215, 215, 215))[#range(5 - n).map(_ => "●").join("")]
    }
    {% for entry in section.entries or [] %}
    {% if entry is string %}
    #block(spacing: 0.08cm)[#text(fill: rgb(70, 70, 70))[{{ entry }}]]
    {% else %}
    #block(spacing: 0.12cm)[
      #text(fill: rgb(40, 40, 40), size: 7.5pt)[{{ entry.label }}]
      #linebreak()
      #dots("{{ entry.details }}")
    ]
    {% endif %}
    {% endfor %}
{% endif %}
{% endfor %}

  ] // end sidebar block
)

// ─── RIGHT COLUMN ─────────────────────────────────────────────────────────────
#v(0.1cm)
