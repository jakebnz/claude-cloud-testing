"""Add a bookmark (outline) panel to the built report so viewers show a clickable index."""
import re, sys
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject, NullObject, NumberObject, FloatObject
from pypdf.generic import Fit

src, out = sys.argv[1], sys.argv[2]
reader = PdfReader(src)
texts = [p.extract_text() or '' for p in reader.pages]


def page_of(title):
    # page 1 carries the contents table, so only the overview itself matches there
    for i, t in enumerate(texts):
        if title in t and (i > 0 or title == 'Specialist device usage'):
            return i
    raise SystemExit(f'not found: {title}')


OUTLINE = [
    ('Overview', 'Specialist device usage', []),
    ('Term 3 by device group', 'Learner use by device group', [
        ('Summary and level of use', 'Learner use by device group'),
        ('Repeat use and weekly averages', 'Repeat use by device group')]),
    ('Usage by campus', 'Usage by campus', [
        ('Campus summary', 'Usage by campus'),
        ('Device groups by campus', 'Device groups by campus')]),
    ('Concurrent use and daily totals', 'Concurrent use and daily totals', []),
    ('Learner use by school week', 'Learner use by school week', []),
    ('Application use', 'Tracked applications', [
        ('Tracked applications and focus hours', 'Tracked applications'),
        ('Categories and other programs', 'Application categories and other programs'),
        ('Windows launch records', 'Windows launch records'),
        ('Mac applications', 'Mac applications')]),
    ('Hardware and six-month use', 'Hardware and six-month use', []),
]

writer = PdfWriter(clone_from=reader)


def top(i):
    # jump to the top of the page and keep the reader's zoom level
    return Fit.xyz(left=0, top=float(writer.pages[i].mediabox.top), zoom=0)


_add = writer.add_outline_item


def add_item(label, i, parent=None):
    return _add(label, i, parent=parent, fit=top(i))


writer.add_outline_item = add_item
for label, key, children in OUTLINE:
    parent = writer.add_outline_item(label, page_of(key))
    for clabel, ckey in children:
        writer.add_outline_item(clabel, page_of(ckey), parent=parent)

# Device register: one entry per device group, at the first page it appears on
reg_pages = [i for i, t in enumerate(texts) if 'Device-level learner use' in t]
reg = writer.add_outline_item('Term 3 device register', reg_pages[0])
groups = [('DigiTech COWs', 'DigiTech COW'), ('DigiTech Windows desktops', 'DigiTech desktop'),
          ('DVC COWs', 'DVC COW'), ('MacBooks', 'MacBook'), ('iMacs', 'iMac')]
for label, short in groups:
    for i in reg_pages:
        sub = re.search(r'Rows \d+-\d+ of 211 \| ([^\n]+)', texts[i])
        if sub and short in [g.strip() for g in sub.group(1).split(',')]:
            writer.add_outline_item(label, i, parent=reg)
            break
    else:
        raise SystemExit(f'register group not found: {short}')

# Make each row of the contents table on page 1 a link to its section
import pdfplumber
from pypdf.annotations import Link
with pdfplumber.open(src) as pdf:
    p1 = pdf.pages[0]
    lines = p1.extract_text_lines()
    height = p1.height
start = next(i for i, l in enumerate(lines) if l['text'].startswith('Section'))
for l in lines[start + 1:]:
    if l['top'] > height - 60:  # footer
        continue
    m = re.match(r'(.+?) (\d+)(?:-\d+)?$', l['text'])
    if not m:
        continue
    target = int(m.group(2)) - 1
    rect = (42, height - l['bottom'] - 5, 553, height - l['top'] + 5)
    writer.add_annotation(0, Link(rect=rect, target_page_index=target))
# pypdf stores a bare page number; local links need a page reference
for annot in writer.pages[0]['/Annots']:
    annot = annot.get_object()
    dest = annot.get('/Dest')
    if dest is not None and isinstance(dest[0], NumberObject):
        tgt = writer.pages[int(dest[0])]
        annot[NameObject('/Dest')] = ArrayObject([tgt.indirect_reference, NameObject('/XYZ'), NumberObject(0),
                                                 FloatObject(float(tgt.mediabox.top)), NumberObject(0)])

writer.page_mode = '/UseOutlines'  # open with the bookmarks panel showing
writer.create_viewer_preferences()
writer.viewer_preferences.display_doctitle = True
writer.add_metadata({'/Title': 'Specialist device usage - Term 3 2026'})
writer.write(out)
