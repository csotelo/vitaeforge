{% set mc_lines = entry.main_column.splitlines() | reject("equalto", "") | list %}
{% set dc_lines = entry.date_and_location_column.splitlines() | reject("equalto", "") | list %}
{% set header = mc_lines[0] if mc_lines | length > 0 else "" %}
{% set highlight_lines = mc_lines[1:] %}

{# Parse "#strong[Company], Position" into separate company and position #}
{% if "#strong[" in header %}
  {% set after_open = header.split("#strong[")[1] %}
  {% set company = after_open.split("]")[0] %}
  {% set after_close = after_open.split("], ") %}
  {% set position = after_close[1] if after_close | length > 1 else "" %}
{% else %}
  {% set company = "" %}
  {% set position = header %}
{% endif %}

{# Date first, location second — matching Harmonize layout #}
{% if dc_lines | length >= 2 %}
  {% set dc_text = dc_lines[1] + "   ·   " + dc_lines[0] %}
{% elif dc_lines | length == 1 %}
  {% set dc_text = dc_lines[0] %}
{% else %}
  {% set dc_text = "" %}
{% endif %}

#block(width: 100%, spacing: 0pt)[
  #text(
    weight: "bold",
    size: 10pt,
    fill: rgb(30, 30, 30),
  )[{{ position }}]#text(
    size: 10pt,
    fill: rgb(110, 110, 110),
  )[, {{ company }}]
{% if dc_text %}
  #v(0.09cm)
  #text(size: 8.5pt, fill: rgb(155, 150, 145))[{{ dc_text }}]
{% endif %}
{% for hl in highlight_lines %}
{% set content = hl[2:] if hl.startswith("- ") else hl %}
{% if content %}
  #v(0.1cm)
  #pad(left: 0.15cm)[
    #text(size: 9pt, fill: rgb(55, 55, 60))[{{ content }}]
  ]
{% endif %}
{% endfor %}
]
#v({{ design.sections.space_between_regular_entries }})
