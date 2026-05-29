{% set mc_lines = entry.main_column.splitlines() | reject("equalto", "") | list %}
{% set dc_lines = entry.date_and_location_column.splitlines() | reject("equalto", "") | list %}
{% set degree_line = mc_lines[0] if mc_lines | length > 0 else "" %}
{% set highlight_lines = mc_lines[1:] %}

{% if dc_lines | length >= 2 %}
  {% set dc_text = dc_lines[1] + "   ·   " + dc_lines[0] %}
{% elif dc_lines | length == 1 %}
  {% set dc_text = dc_lines[0] %}
{% else %}
  {% set dc_text = "" %}
{% endif %}

#block(width: 100%, spacing: 0pt)[
  #text(weight: "bold", size: 10pt, fill: rgb(30, 30, 30))[{{ degree_line }}]
{% if dc_text %}
  #v(0.09cm)
  #text(size: 8.5pt, fill: rgb(155, 150, 145))[{{ dc_text }}]
{% endif %}
{% for hl in highlight_lines %}
{% set content = hl[2:] if hl.startswith("- ") else hl %}
{% if content %}
  #v(0.1cm)
  #pad(left: 0.15cm)[
    #text(size: 9pt, fill: rgb(55, 55, 60))[• #h(0.1cm){{ content }}]
  ]
{% endif %}
{% endfor %}
]
#v({{ design.sections.space_between_regular_entries }})
