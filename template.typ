// template.typ
#set page(
  paper: "us-letter",
  margin: (x: 1.1cm, y: 1.1cm),
)
#set text(
  font: ("Arial", "Liberation Sans"),
  size: 9pt,
  fill: rgb("#111111")
)

// Show rule to tighten spacing above and below section headings
#show heading: set block(above: 0.7em, below: 0.4em)

// Read the tailored data generated dynamically by our engine script
#let r = json("current_tailored_resume.json")

// Header Zone
#align(center)[
  #block(text(weight: "bold", size: 16pt)[#r.meta.name])
  #v(-3mm)
  #text(size: 8.5pt)[
    #r.meta.email | #r.meta.phone | #r.meta.github | #r.meta.linkedin
  ]
]

#v(-1mm)

// Education Zone
== Education
#line(length: 100%, stroke: 0.5pt + rgb("#cccccc"))
*#r.education.institute* #h(1fr) #r.education.dates \
#r.education.degree #h(1fr) #emph(r.education.metrics)

#v(-0.5mm)

// Skills Zone
== Technical Skills
#line(length: 100%, stroke: 0.5pt + rgb("#cccccc"))
*Languages & Concurrency:* #r.technical_skills.languages.join(", ") (#r.technical_skills.concurrency.join(", ")) \
*Backend & Databases:* #r.technical_skills.backend.join(", ") \
*Redis Technologies:* #r.technical_skills.redis.join(", ") \
*Tools & Security:* #r.technical_skills.tools.join(", ") | #r.technical_skills.security.join(", ") \

#v(-0.5mm)

// Experience Zone
== Experience
#line(length: 100%, stroke: 0.5pt + rgb("#cccccc"))
#for job in r.experience [
  *#job.title* -- #job.company #h(1fr) #emph(job.dates) \
  #v(-2mm)
  #list(
    marker: ([•],),
    ..job.bullets.map(b => text(size: 8.5pt)[#b])
  )
  #v(-0.5mm)
]

#v(-0.5mm)

// Dynamic Projects Zone
== Technical Projects
#line(length: 100%, stroke: 0.5pt + rgb("#cccccc"))
#for project in r.projects [
  *#project.title* (#project.tech) #h(1fr) #if "impact" in project [ #emph(project.impact) ] \
  #v(-2mm)
  #list(
    marker: ([•],),
    ..project.bullets.map(b => text(size: 8.5pt)[#b])
  )
  #v(-0.5mm)
]

#v(-0.5mm)

// Awards Zone
== Awards & Achievements
#line(length: 100%, stroke: 0.5pt + rgb("#cccccc"))
#for award in r.awards [
  *#award.title* \
  #v(-2.5mm)
  #text(size: 8.5pt)[#award.details]
  #v(-0.5mm)
]