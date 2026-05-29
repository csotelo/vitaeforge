{% set sidebar_keys = ["skills", "languages", "education", "certifications", "courses_&_certifications", "courses_and_certifications"] %}
{% if snake_case_section_title in sidebar_keys %}
#block(height: 0pt, clip: true)[
{% else %}
// ─── SECTION: {{ section_title }} ────────────────────────────────────────────
#v({{ design.section_titles.space_above }})
#block(width: 100%, below: 0pt)[
  #text(
    size: 13pt,
    weight: "regular",
    fill: rgb(198, 138, 42),
    font: "Raleway",
  )[{{ section_title }}]
  #v(0.05cm)
  #line(length: 100%, stroke: 0.6pt + rgb(225, 192, 125))
]
#v({{ design.section_titles.space_below }})
{% if entry_type == "ReversedNumberedEntry" %}
#reversed-numbered-entries(
  [
{% else %}
#block()[
{% endif %}
{% endif %}
