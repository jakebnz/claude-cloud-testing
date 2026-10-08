import json, sys
from datetime import date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, NextPageTemplate, PageBreak, Flowable, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.pdfgen import canvas as pdfcanvas

OUT = sys.argv[1]
rows = json.load(open(sys.argv[2]))

NAVY = colors.HexColor('#163447')
TEAL = colors.HexColor('#16807A')
INK = colors.HexColor('#1F2D3A')
MUTED = colors.HexColor('#5B6B78')
STRIPE = colors.HexColor('#EEF3F5')
TOTAL = colors.HexColor('#E3F0EE')
RULE = colors.HexColor('#D3DCE2')
TILE = colors.HexColor('#EAF4F3')
SEQ = ['#0E5E5A', '#3C9C95', '#9DD0CA', '#D5DCE1']  # Regular, Occasional, One day, Not used

PW, PH = A4
LM = RM = 15 * mm
TM, BM = 22 * mm, 20 * mm

# ---------- styles ----------
def ps(name, **kw):
    base = {} if 'parent' in kw else dict(fontName='Helvetica', fontSize=9.5, leading=12.5, textColor=INK)
    base.update(kw)
    return ParagraphStyle(name, **base)

KICK = ps('kick', fontName='Helvetica-Bold', fontSize=8, textColor=TEAL, leading=10, spaceAfter=4)
H1 = ps('h1', fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=NAVY, spaceAfter=4)
SUB = ps('sub', fontSize=10, leading=13, textColor=MUTED, spaceAfter=14)
H2 = ps('h2', fontName='Helvetica-Bold', fontSize=12.5, leading=15, textColor=NAVY, spaceBefore=14, spaceAfter=7)
BODY = ps('body')
NOTE = ps('note', fontSize=8, leading=10.5, textColor=MUTED, spaceBefore=5)
TH = ps('th', fontName='Helvetica-Bold', fontSize=8.5, leading=10.5, textColor=colors.white)
THR = ps('thr', parent=TH, alignment=TA_RIGHT)
TD = ps('td', fontSize=9, leading=11.5)
TDR = ps('tdr', parent=TD, alignment=TA_RIGHT)
TDB = ps('tdb', parent=TD, fontName='Helvetica-Bold')
TDBR = ps('tdbr', parent=TDB, alignment=TA_RIGHT)
TILE_N = ps('tn', fontName='Helvetica-Bold', fontSize=26, leading=30, textColor=TEAL)
TILE_L = ps('tl', fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=INK)
TILE_S = ps('ts', fontSize=8, leading=10, textColor=MUTED)


def fmt(n):
    return f'{n:,}' if isinstance(n, int) else n


def table(head, body, widths, num_cols=(), total=False, font=9, pad=5, bold_first=False, head_lines=1, bold_rows=(),
          bold_cells=(), hpad=6):
    """head: list of str, body: list of lists. num_cols: indices right-aligned."""
    cur = -1

    def cell(v, ci, is_head, is_total):
        if isinstance(v, Flowable):
            return v
        txt = fmt(v)
        if is_head:
            return Paragraph(txt, THR if ci in num_cols else TH)
        st = ps('c', fontSize=font, leading=font + 2.5,
                fontName='Helvetica-Bold' if (is_total or (bold_first and ci == 0) or cur in bold_rows
                                              or (cur, ci) in bold_cells) else 'Helvetica',
                alignment=TA_RIGHT if ci in num_cols else TA_LEFT)
        return Paragraph(str(txt), st)
    data = [[cell(v, i, True, False) for i, v in enumerate(head)]]
    n = len(body)
    bold_rows = {b % n for b in bold_rows}
    bold_cells = {(b[0] % n, b[1]) for b in bold_cells}
    for ri, r in enumerate(body):
        is_t = total and ri == n - 1
        cur = ri
        data.append([cell(v, i, False, is_t) for i, v in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), pad), ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
        ('TOPPADDING', (0, 0), (-1, 0), pad + 2), ('BOTTOMPADDING', (0, 0), (-1, 0), pad + 2),
        ('LEFTPADDING', (0, 0), (-1, -1), hpad), ('RIGHTPADDING', (0, 0), (-1, -1), hpad),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, RULE),
    ]
    for ri in range(1, len(data)):
        if ri % 2 == 1:
            style.append(('BACKGROUND', (0, ri), (-1, ri), STRIPE))
    if total:
        style += [('BACKGROUND', (0, -1), (-1, -1), TOTAL), ('LINEABOVE', (0, -1), (-1, -1), 0.8, NAVY)]
    t.setStyle(TableStyle(style))
    return t


CW = PW - LM - RM  # content width portrait


def cols(*fr, width=CW):
    s = sum(fr)
    return [width * f / s for f in fr]


# ---------- page furniture ----------
class Footer(Flowable):
    """Zero-size flowable that sets the footer note for the page it lands on."""
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.width = self.height = 0

    def draw(self):
        self.canv._footnote = self.text


class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._saved = []
        self._footnote = ''

    def showPage(self):
        self._saved.append((dict(self.__dict__), self._footnote))
        self._startPage()

    def save(self):
        n = len(self._saved)
        for state, note in self._saved:
            self.__dict__.update(state)
            self._furniture(n, note)
            super().showPage()
        super().save()

    def _furniture(self, total, note):
        w, h = self._pagesize
        self.setFillColor(TEAL)
        self.rect(LM, h - 13 * mm, 9 * mm, 1.3 * mm, stroke=0, fill=1)
        self.setFont('Helvetica-Bold', 7.5)
        self.setFillColor(MUTED)
        self.drawString(LM + 12 * mm, h - 13 * mm, 'ROLLESTON COLLEGE  /  SPECIALIST DEVICES')
        self.setFont('Helvetica', 7.5)
        self.drawRightString(w - RM, h - 13 * mm, '9 OCTOBER 2026')
        self.setStrokeColor(RULE)
        self.setLineWidth(0.5)
        self.line(LM, 13 * mm, w - RM, 13 * mm)
        self.setFont('Helvetica', 7)
        self.drawString(LM, 9 * mm, note or '')
        self.setFont('Helvetica-Bold', 7.5)
        self.setFillColor(INK)
        self.drawRightString(w - RM, 9 * mm, f'{self._pageNumber:02d} / {total:02d}')


def heading(kicker, title, sub=None):
    out = [Paragraph(kicker.upper(), KICK), Paragraph(title, H1)]
    out.append(Paragraph(sub, SUB) if sub else Spacer(1, 10))
    return out


# ---------- data ----------
GROUPS = ['DigiTech COWs', 'DigiTech Windows desktops', 'DVC COWs', 'MacBooks', 'iMacs']
GMAP = {'DigiTech COW': 'DigiTech COWs', 'DigiTech desktop': 'DigiTech Windows desktops',
        'DVC COW': 'DVC COWs', 'MacBook': 'MacBooks', 'iMac': 'iMacs'}
SHORT = {'DigiTech COWs': 'DigiTech COW', 'DigiTech Windows desktops': 'DigiTech desktop',
         'DVC COWs': 'DVC COW', 'MacBooks': 'MacBook', 'iMacs': 'iMac'}
for r in rows:
    r['g'] = GMAP[r['group']]
LEVELS = ['Regular', 'Occasional', 'One day', 'Not used']
WEEKS_T3 = 10


def dkey(s):
    d, m, y = s.split('/')
    return (y, m, d)


def agg(rs):
    used = [r for r in rs if r['logins'] > 0]
    lasts = [r['last'] for r in rs if r['last'] != '-']
    return dict(n=len(rs), used=len(used), logins=sum(r['logins'] for r in rs),
                days=sum(r['days'] for r in rs),
                # school-day weekly rates, summed from the per-device figures
                lpw=round(sum(r['lpw'] for r in rs), 1), dpw=round(sum(r['dpw'] for r in rs), 1),
                last=max(lasts, key=dkey) if lasts else '-',
                lv={k: sum(r['cat'] == k for r in rs) for k in LEVELS})


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '-'


# Learner accounts per group (Term 3 and six months), from the source OU-group tables.
# Merged groups are the sum of their OU-group counts.
T3_LEARNERS = {'DigiTech COWs': (81 + 112, True), 'DigiTech Windows desktops': (2 + 16 + 3, True),
               'DVC COWs': (34 + 21 + 51, True)}
SIX = {  # devices used, learners (sum of OU counts), logins
    'DigiTech COWs': (16 + 18, 109 + 163, 359 + 1625),
    'DigiTech Windows desktops': (1 + 9 + 1, 5 + 36 + 5, 9 + 124 + 5),
    'DVC COWs': (16 + 14 + 27, 84 + 47 + 95, 687 + 678 + 363),
}
SIX_MAC = (56, 179, 997)
total_t3 = agg(rows)
assert total_t3['n'] == 211 and total_t3['used'] == 139 and total_t3['logins'] == 2581

story = []

# =============== Page 1: overview ===============
story += [Footer('Term 3 and six-month reporting windows'),
          Paragraph('DATA OVERVIEW', KICK), Paragraph('Specialist device usage', H1),
          Paragraph('Learner logons, concurrent use and application use  |  Term 3 2026 and six-month reporting window', SUB),
          Paragraph('<b>Term 3:</b> 20 July - 25 September 2026 (50 school days, 10 school weeks)', BODY),
          Paragraph('<b>Six months:</b> 25 March - 25 September 2026 (110 school days, 23 school weeks)', BODY),
          Spacer(1, 14)]


def tile(n, label, sub):
    return [Paragraph(n, TILE_N), Spacer(1, 2), Paragraph(label, TILE_L), Spacer(1, 3), Paragraph(sub, TILE_S)]


tw = (CW - 2 * 10) / 3
tiles = Table([[tile('366', 'Learner accounts', 'Term 3'), '', tile('139 / 211', 'Devices used by learners', 'Term 3'), '',
                tile('2,581', 'Learner logins', 'Term 3')]],
              colWidths=[tw, 10, tw, 10, tw])
tiles.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), TILE), ('BACKGROUND', (2, 0), (2, 0), TILE),
                           ('BACKGROUND', (4, 0), (4, 0), TILE), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 12), ('TOPPADDING', (0, 0), (-1, -1), 12),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 14)]))
story += [tiles, Paragraph('Reporting-period summary', H2)]
story.append(table(['Measure', 'Term 3', 'Six months'], [
    ['Devices in scope', 211, 211],
    ['Devices used by learners', 139, 158],
    ['Unique learner accounts', 366, 469],
    ['Total learner logins', 2581, 4847],
    ['Average devices used per school week', '68.7', '60.0'],
    ['Average learner logins per school week', '257.7', '210.2'],
    ['Peak simultaneous learner sessions', '32', '33'],
    ['Most recent learner login', '25/09/26, 2:45 pm', '25/09/26, 2:45 pm'],
], cols(5, 2, 2), num_cols=(1, 2)))
story.append(Paragraph('Contents', H2))
contents = [
    ['Term 3 use by device group and level of use', '2-3'],
    ['Usage by campus', '4-5'],
    ['Concurrent use and daily totals', '6'],
    ['Learner use by school week', '7'],
    ['Application use', '8-11'],
    ['Hardware and six-month use by device group', '12'],
    ['Term 3 device register', '13-20'],
]
story.append(table(['Section', 'Page'], contents, cols(8, 1), num_cols=(1,), pad=4))
story.append(PageBreak())

# =============== Page 2: groups ===============
story += [Footer('Calculated from the Term 3 device register')]
story += heading('Term 3 2026', 'Learner use by device group',
                 '20 July - 25 September 2026  |  50 school days  |  10 school weeks')

story.append(Paragraph('Level-of-use definitions', H2))
story.append(table(['Level of use', 'Definition'], [
    ['Regular', 'Learner use on school days in at least 50% of the school weeks in the period'],
    ['Occasional', 'Learner use on two or more days, below that share'],
    ['One day', 'Learner use on a single day'],
    ['Not used', 'No learner logon recorded'],
], cols(1.3, 5), bold_first=True, pad=4))

story.append(Paragraph('Summary by device group', H2))
body = []
for g in GROUPS:
    a = agg([r for r in rows if r['g'] == g])
    if g in T3_LEARNERS:
        ln = f'{T3_LEARNERS[g][0]}*'
    elif g == 'MacBooks':
        ln = '179 (Macs)'
    else:
        ln = ''
    body.append([g, a['n'], a['used'], pct(a['used'], a['n']), ln, a['logins'],
                 f"{a['lpw']:.1f}", a['days'], a['last']])
body.append(['All devices', 211, 139, pct(139, 211), 366, 2581, f"{total_t3['lpw']:.1f}",
             total_t3['days'], '25/09/26'])
t = table(['Device group', 'Devices', 'Used', '% used', 'Learner accounts', 'Learner logins', 'Logins per school week',
           'Device-<br/>days', 'Last learner login'], body,
          cols(3.0, 1.25, 0.9, 1.0, 1.35, 1.2, 1.15, 1.1, 1.35), num_cols=(1, 2, 3, 4, 5, 6, 7, 8), total=True,
          font=8.5)
# MacBook / iMac learner count spans both rows
t.setStyle(TableStyle([('SPAN', (4, 4), (4, 5)), ('VALIGN', (4, 4), (4, 5), 'MIDDLE')]))
story.append(t)
story.append(Paragraph(
    '* Sum of the learner counts for each OU in the group; a learner who used devices in more than one of these OUs is '
    'counted once per OU. MacBook and iMac learner accounts are reported as one figure (179). '
    'Device-days is the total number of separate days each device in the group was used.', NOTE))

story.append(Paragraph('Level of use by device group', H2))
body = []
for g in GROUPS:
    a = agg([r for r in rows if r['g'] == g])
    body.append([g] + [a['lv'][k] for k in LEVELS] + [a['n']])
body.append(['All devices'] + [total_t3['lv'][k] for k in LEVELS] + [211])
body.append(['Share of all devices'] + [pct(total_t3['lv'][k], 211) for k in LEVELS] + ['100%'])
t = table(['Device group'] + LEVELS + ['Total'], body, cols(3.3, 1.3, 1.3, 1.3, 1.3, 1.1), num_cols=(1, 2, 3, 4, 5),
          font=8.5, bold_rows=(-2, -1))
t.setStyle(TableStyle([('BACKGROUND', (0, -2), (-1, -1), TOTAL), ('LINEABOVE', (0, -2), (-1, -2), 0.8, NAVY)]))
story.append(t)
story.append(PageBreak())

# =============== Page 3: days used and weekly averages ===============
story += [Footer('Calculated from the Term 3 device register')]
story += heading('Term 3 2026', 'Repeat use by device group',
                 'Separate school days each device was used by learners')
BUCKETS = [('0', 0, 0), ('1', 1, 1), ('2-5', 2, 5), ('6-10', 6, 10), ('11-20', 11, 20), ('21+', 21, 999)]
body = []
for g in GROUPS + ['All devices']:
    rs = rows if g == 'All devices' else [r for r in rows if r['g'] == g]
    body.append([g] + [sum(lo <= r['days'] <= hi for r in rs) for _, lo, hi in BUCKETS] + [len(rs)])
story.append(Paragraph('Devices by number of days used', H2))
story.append(table(['Device group'] + [b[0] for b in BUCKETS] + ['Total'], body,
                   cols(3.3, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0), num_cols=range(1, 8), total=True, font=8.5))

story.append(Paragraph('Average use per device per school week', H2))
body = []
for g in GROUPS + ['All devices']:
    rs = rows if g == 'All devices' else [r for r in rows if r['g'] == g]
    a = agg(rs)
    u = [r for r in rs if r['logins'] > 0]
    body.append([g, f"{a['lpw'] / a['n']:.2f}", f"{a['dpw'] / a['n']:.2f}",
                 f"{a['lpw'] / len(u):.2f}", f"{a['dpw'] / len(u):.2f}"])
story.append(table(['Device group', 'Logins / week<br/>(all devices)', 'Days / week<br/>(all devices)',
                    'Logins / week<br/>(used devices)', 'Days / week<br/>(used devices)'], body,
                   cols(3.3, 1.6, 1.6, 1.6, 1.6), num_cols=(1, 2, 3, 4), total=True, font=8.5))

story.append(PageBreak())

# =============== Pages 4-5: campus ===============
CAMPUSES = ['Junior', 'Senior']
camp = {c: [r for r in rows if r['campus2'] == c] for c in CAMPUSES}
ca = {c: agg(camp[c]) for c in CAMPUSES}
n_ou = {c: sum(r['camp_src'] == 'OU' for r in camp[c]) for c in CAMPUSES}

story += [Footer('Calculated from the Term 3 device register  |  Campus from campus OU, otherwise recorded location')]
story += heading('Campus usage', 'Usage by campus',
                 f"Term 3 2026  |  {ca['Junior']['n']} Junior and {ca['Senior']['n']} Senior devices with a campus "
                 f"recorded by OU membership or device location")


def camp_row(label, f):
    return [label] + [f(c) for c in CAMPUSES]


J, S = ca['Junior'], ca['Senior']
body = [
    camp_row('Devices', lambda c: ca[c]['n']),
    camp_row('Devices used by learners', lambda c: ca[c]['used']),
    camp_row('Share of devices used', lambda c: pct(ca[c]['used'], ca[c]['n'])),
    camp_row('Learner logins', lambda c: ca[c]['logins']),
    camp_row('Learner logins per device', lambda c: f"{ca[c]['logins'] / ca[c]['n']:.1f}"),
    camp_row('Learner logins per device per week', lambda c: f"{ca[c]['lpw'] / ca[c]['n']:.2f}"),
    camp_row('Learner logins per used device', lambda c: f"{ca[c]['logins'] / ca[c]['used']:.1f}"),
    camp_row('Device-days (separate days used, all devices)', lambda c: ca[c]['days']),
    camp_row('Average days used per device', lambda c: f"{ca[c]['days'] / ca[c]['n']:.1f}"),
    camp_row('Average days used per used device', lambda c: f"{ca[c]['days'] / ca[c]['used']:.1f}"),
    camp_row('Most recent learner login', lambda c: ca[c]['last']),
]
story.append(Paragraph('Campus summary', H2))
story.append(table(['Measure', 'Junior', 'Senior'], body, cols(5, 1.6, 1.6), num_cols=(1, 2), font=9, pad=4))

# stacked level-of-use bars
story.append(Paragraph('Level of use by campus (share of devices)', H2))


class LevelBars(Flowable):
    def __init__(self, width):
        super().__init__()
        self.width, self.height = width, 108

    def draw(self):
        c = self.canv
        lab_w = 92
        bar_w = self.width - lab_w
        # legend
        x = lab_w
        c.setFont('Helvetica', 8)
        for k, col in zip(LEVELS, SEQ):
            c.setFillColor(colors.HexColor(col))
            c.roundRect(x, self.height - 9, 9, 9, 1.5, stroke=0, fill=1)
            c.setFillColor(INK)
            c.drawString(x + 13, self.height - 8, k)
            x += 13 + c.stringWidth(k, 'Helvetica', 8) + 18
        for i, cname in enumerate(CAMPUSES):
            a = ca[cname]
            y = self.height - 48 - i * 40
            c.setFillColor(INK)
            c.setFont('Helvetica-Bold', 9)
            c.drawString(0, y + 10, cname)
            c.setFont('Helvetica', 7.5)
            c.setFillColor(MUTED)
            c.drawString(0, y + 0.5, f"{a['n']} devices")
            x = lab_w
            for k, col in zip(LEVELS, SEQ):
                v = a['lv'][k]
                w = bar_w * v / a['n']
                if v == 0:
                    continue
                c.setFillColor(colors.HexColor(col))
                c.rect(x, y, max(w - 2, 0.5), 24, stroke=0, fill=1)
                label = f"{100 * v / a['n']:.0f}%"
                if w > 28:
                    c.setFillColor(colors.white if k in ('Regular', 'Occasional') else INK)
                    c.setFont('Helvetica-Bold', 8.5)
                    c.drawCentredString(x + (w - 2) / 2, y + 8.5, label)
                x += w


story.append(LevelBars(CW))
body = [[k] + [f"{ca[c]['lv'][k]}  ({pct(ca[c]['lv'][k], ca[c]['n'])})" for c in CAMPUSES] for k in LEVELS]
body.append(['Total', f"{J['n']}", f"{S['n']}"])
story.append(Spacer(1, 6))
story.append(table(['Level of use', 'Junior devices', 'Senior devices'], body, cols(5, 1.6, 1.6), num_cols=(1, 2),
                   total=True, font=9, pad=4))
story.append(PageBreak())

# page 5: by group within campus
story += [Footer('Calculated from the Term 3 device register  |  Campus from campus OU, otherwise recorded location')]
story += heading('Campus usage', 'Device groups by campus',
                 'Term 3 2026  |  Devices with a campus recorded by OU membership or device location')
body = []
group_rows = []
for c in CAMPUSES:
    first = True
    for g in GROUPS:
        rs = [r for r in camp[c] if r['g'] == g]
        if not rs:
            continue
        a = agg(rs)
        body.append([c if first else '', g, a['n'], a['used'], pct(a['used'], a['n']), a['logins'],
                     f"{a['lpw'] / a['n']:.2f}", a['days'], a['lv']['Regular'], a['last']])
        first = False
    a = ca[c]
    body.append(['', f'{c} total', a['n'], a['used'], pct(a['used'], a['n']), a['logins'],
                 f"{a['lpw'] / a['n']:.2f}", a['days'], a['lv']['Regular'], a['last']])
    group_rows.append(len(body))
bc = [(e - 1, ci) for e in group_rows for ci in range(1, 10)]
starts = [1] + [e + 1 for e in group_rows[:-1]]
bc += [(s0 - 1, 0) for s0 in starts]
t = table(['Campus', 'Device group', 'Devices', 'Used', '% used', 'Learner logins', 'Logins / device / week',
           'Device-<br/>days', 'Regular', 'Last learner login'], body,
          cols(1.25, 3.1, 1.15, 0.85, 0.95, 1.2, 1.25, 1.2, 1.15, 1.2), num_cols=range(2, 10), font=8.5, pad=4,
          bold_cells=bc, hpad=4.5)
st = []
prev = 1
for i, end in enumerate(group_rows):
    st.append(('BACKGROUND', (0, prev), (-1, end), colors.white))
    for rr in range(prev, end):
        if (rr - prev) % 2 == 0:
            st.append(('BACKGROUND', (1, rr), (-1, rr), STRIPE))
    st += [('BACKGROUND', (1, end), (-1, end), TOTAL), ('LINEABOVE', (1, end), (-1, end), 0.8, NAVY),
           ('LINEBELOW', (0, end), (-1, end), 1.2, NAVY)]
    prev = end + 1
t.setStyle(TableStyle(st))
story.append(Paragraph('Learner use by device group and campus', H2))
story.append(t)

story.append(Paragraph('Level of use by device group and campus', H2))
body = []
for g in GROUPS:
    line = [g]
    for c in CAMPUSES:
        rs = [r for r in camp[c] if r['g'] == g]
        if rs:
            a = agg(rs)
            line += [a['n'], pct(a['lv']['Regular'], a['n']), pct(a['lv']['Occasional'] + a['lv']['One day'], a['n']),
                     pct(a['lv']['Not used'], a['n'])]
        else:
            line += ['-', '-', '-', '-']
    body.append(line)
t = table(['Device group', 'Jnr devices', 'Jnr regular', 'Jnr occ. / one day', 'Jnr not used',
           'Snr devices', 'Snr regular', 'Snr occ. / one day', 'Snr not used'], body,
          cols(2.9, 1, 1, 1.15, 1, 1, 1, 1.15, 1), num_cols=range(1, 9), font=8.5, pad=4)
t.setStyle(TableStyle([('LINEAFTER', (4, 0), (4, -1), 1, colors.white), ('LINEAFTER', (4, 1), (4, -1), 1, RULE)]))
story.append(t)
story.append(Paragraph('Percentages are shares of the devices in that group and campus. '
                       'Application-use records are reported for the whole fleet (pages 8-11).', NOTE))
story.append(PageBreak())

# =============== Page 6: concurrent ===============
story += [Footer('Concurrent-use and class-period data, school days only')]
story += heading('Concurrent use', 'Concurrent use and daily totals', 'School days only')
two = lambda a, b: Paragraph(f'<b>{a}</b><br/><font color="#5B6B78" size="8">{b}</font>', TD)
story.append(table(['Measure', 'Term 3', 'Six months'], [
    ['Peak simultaneous learner sessions', two('32', '11 Aug, 11:11 am'), two('33', '7 May, 12:27 pm')],
    ['Peak devices in one class period', two('32', '11 Aug, P2'), two('35', '7 May, P3')],
    ['Peak devices used in one school day', two('52', '11 Aug'), two('57', '28 Apr')],
    ['Class periods analysed', '200', '440'],
], cols(4, 2, 2), pad=5))
story.append(Paragraph('Term 3: average / maximum devices in use by class period', H2))
story.append(table(['Weekday', 'P1', 'P2', 'P3', 'P4'], [
    ['Monday', '8.5 / 21', '14.3 / 29', '12.0 / 18', '9.4 / 30'],
    ['Tuesday', '9.1 / 19', '14.8 / 32', '11.5 / 31', '10.0 / 20'],
    ['Wednesday', '11.7 / 26', '13.3 / 17', '9.4 / 26', '11.2 / 20'],
    ['Thursday', '8.6 / 19', '13.0 / 26', '14.0 / 26', '11.9 / 19'],
    ['Friday', '7.2 / 18', '9.9 / 22', '10.8 / 22', '10.6 / 21'],
    ['All school days', '9.0 / 26', '13.1 / 32', '11.5 / 31', '10.6 / 30'],
], cols(2.4, 1.5, 1.5, 1.5, 1.5), num_cols=(1, 2, 3, 4), total=True))
story.append(Paragraph('Five busiest class periods in Term 3', H2))
story.append(table(['Date', 'Period', 'Time', 'Devices in use'], [
    ['11 Aug 2026', 'P2', '10:10-11:25', 32], ['18 Aug 2026', 'P3', '12:00-13:15', 31],
    ['17 Aug 2026', 'P4', '13:55-15:10', 30], ['31 Aug 2026', 'P2', '10:10-11:25', 29],
    ['8 Sep 2026', 'P2', '10:10-11:25', 27],
], cols(2.4, 1.2, 2.2, 1.6), num_cols=(3,)))
story.append(PageBreak())

# =============== Page 7: weekly ===============
story += [Footer('Weekly learner activity, school days only')]
story += heading('Weekly activity', 'Learner use by school week', 'School days only  |  Term 3 weeks shaded')
weeks = [('23 Mar', 3, 40, 101, 48, 15), ('30 Mar', 4, 37, 98, 39, 14), ('20 Apr', 5, 59, 147, 68, 30),
         ('27 Apr', 4, 62, 197, 74, 30), ('4 May', 5, 58, 196, 66, 35), ('11 May', 5, 57, 237, 74, 30),
         ('18 May', 5, 53, 187, 56, 25), ('25 May', 5, 67, 214, 71, 27), ('1 Jun', 4, 61, 183, 59, 30),
         ('8 Jun', 5, 58, 226, 65, 29), ('15 Jun', 5, 46, 109, 52, 15), ('22 Jun', 5, 47, 188, 62, 30),
         ('29 Jun', 5, 49, 175, 57, 27), ('20 Jul', 5, 85, 268, 103, 21), ('27 Jul', 5, 71, 225, 82, 25),
         ('3 Aug', 5, 72, 254, 104, 26), ('10 Aug', 5, 85, 276, 134, 32), ('17 Aug', 5, 62, 292, 120, 31),
         ('24 Aug', 5, 62, 277, 113, 26), ('31 Aug', 5, 59, 310, 123, 29), ('7 Sep', 5, 63, 243, 117, 27),
         ('14 Sep', 5, 60, 205, 101, 24), ('21 Sep', 5, 68, 227, 111, 19)]
t = table(['Week of 2026', 'School days', 'Devices used', 'Learner logins', 'Unique learners',
           'Peak devices in a period'], [list(w) for w in weeks], cols(1.6, 1, 1.1, 1.1, 1.1, 1.3),
          num_cols=range(1, 6), font=8.5, pad=3)
st = [('BACKGROUND', (0, 1), (-1, len(weeks)), colors.white)]
for i in range(len(weeks)):
    if i >= 13:
        st.append(('BACKGROUND', (0, i + 1), (-1, i + 1), TOTAL))
t.setStyle(TableStyle(st))
story.append(t)
story.append(Paragraph('Login totals', H2))
story.append(table(['Period', 'School days', 'Weekends / holidays', 'All days'],
                   [['Term 3', 2577, 4, 2581], ['Six months', 4835, 12, 4847]], cols(2.4, 1.4, 1.6, 1.4),
                   num_cols=(1, 2, 3)))
story.append(PageBreak())

# =============== Pages 8-10: applications ===============
CAT_ROWS = [  # category, uses T3, learners T3, Win h T3, uses 6m, learners 6m, Win h 6m, Mac h T3, Mac h 6m
    ('Higher-spec', 71, 98, '134.2', 124, 143, '705.2', '0.0', '0.0'),
    ('Mid-spec creative', 48, 47, '35.3', 74, 68, '39.5', '0.0', '0.0'),
    ('Browser/Office', 270, 247, '175.9', 355, 389, '337.8', '714.8', '722.3'),
    ('Light utility', 65, 45, '34.7', 118, 100, '57.6', '0.0', '0.0'),
    ('Total', 454, 437, '380.1', 671, 700, '1,140.1', '714.8', '722.3'),
]
TRACKED = {  # app: installed, dev T3, learners T3, Win h T3, dev 6m, learners 6m, Win h 6m, last used
    'Higher-spec': [
        ('Autodesk Fusion', 76, 30, 27, '45.3', 69, 61, '573.6', '24/09/26'),
        ('Blender', 53, 22, 61, '68.1', 30, 69, '72.3', '16/09/26'),
        ('Roblox', 18, 10, 6, '15.8', 14, 8, '52.2', '24/09/26'),
        ('Roblox Studio', 14, 9, 4, '5.0', 11, 5, '7.1', '21/09/26')],
    'Mid-spec creative': [
        ('Audacity', 112, 2, 2, '0.1', 9, 6, '0.7', '18/08/26'),
        ('GIMP', 51, 0, 0, '0.0', 3, 1, '0.0', '26/06/26'),
        ('Inkscape', 52, 2, 3, '0.0', 5, 5, '0.2', '17/08/26'),
        ('Minecraft Education', 52, 29, 22, '26.4', 31, 26, '26.7', '09/10/26'),
        ('PrusaSlicer', 60, 14, 19, '8.8', 22, 28, '11.9', '08/09/26'),
        ('Scribus', 52, 1, 1, '0.0', 4, 2, '0.0', '03/08/26')],
    'Browser/Office': [
        ('Adobe Reader DC', 112, 4, 3, '0.0', 29, 16, '0.7', '15/09/26'),
        ('Chrome', 112, 125, 142, '91.4', 145, 214, '186.0', '29/09/26'),
        ('Firefox', 112, 12, 10, '1.8', 23, 15, '2.8', '25/09/26'),
        ('Microsoft 365 Apps', 53, 4, 2, '0.0', 7, 3, '0.0', '18/09/26'),
        ('Microsoft Edge', 112, 67, 90, '82.6', 92, 141, '148.3', '09/10/26'),
        ('Safari', 0, 58, 0, '0.0', 59, 0, '0.0', '25/09/26')],
    'Light utility': [
        ('7-Zip', 112, 0, 0, '0.0', 1, 0, '0.0', '15/04/26'),
        ('Notepad++', 112, 10, 2, '1.1', 15, 13, '6.7', '04/09/26'),
        ('PyScripter', 91, 21, 23, '29.7', 24, 28, '31.7', '25/09/26'),
        ('Python', 49, 22, 14, '0.1', 24, 19, '0.1', '25/09/26'),
        ('RDWorks', 59, 9, 5, '3.8', 32, 31, '11.9', '24/09/26'),
        ('Solitaire', 0, 0, 0, '0.0', 13, 4, '7.3', '26/06/26'),
        ('VLC', 112, 3, 1, '0.0', 9, 5, '0.0', '25/09/26')],
}
# reconcile against the source totals
_all = [a for v in TRACKED.values() for a in v]
assert sum(a[2] for a in _all) == 454 and sum(a[3] for a in _all) == 437 and sum(a[5] for a in _all) == 671
assert sum(a[6] for a in _all) == 700
assert abs(sum(float(a[4]) for a in _all) - 380.1) < 0.15 and abs(sum(float(a[7]) for a in _all) - 1140.1) < 0.15
for cat, n, l, h, n6, l6, h6, _, _ in CAT_ROWS[:-1]:
    v = TRACKED[cat]
    assert sum(a[2] for a in v) == n and sum(a[3] for a in v) == l and sum(a[5] for a in v) == n6, cat
    assert abs(sum(float(a[4]) for a in v) - float(h)) < 0.15 and abs(sum(float(a[7]) for a in v) - float(h6)) < 0.15, cat

story += [Footer('Tracked applications  |  T3: 20 Jul - 25 Sep 2026  |  6m: 25 Mar - 25 Sep 2026')]
story += heading('Application use', 'Tracked applications',
                 'Devices used: Windows and Mac devices with a dated record. Learners: learner accounts with a dated record. '
                 'Win focus hours: Windows UserAssist foreground time for learner entries last used in the period, '
                 'cumulative since each profile was created.')
body, cat_rows = [], []
for cat, apps in TRACKED.items():
    body.append([cat] + [''] * 8)
    cat_rows.append(len(body))
    body += [list(a) for a in apps]
body.append(['Total', '', 454, 437, '380.1', 671, 700, '1,140.1', ''])
t = table(['Application', 'Installed on', 'Devices used T3', 'Learners T3', 'Win focus hours T3', 'Devices used 6m',
           'Learners 6m', 'Win focus hours 6m', 'Last used'], body,
          cols(2.5, 1, 1, 1, 1.1, 1, 1, 1.1, 1.15), num_cols=range(1, 9), total=True, font=8.3, pad=2.6, hpad=4.5,
          bold_rows=[r - 1 for r in cat_rows])
st = [('BACKGROUND', (0, 1), (-1, len(body) - 1), colors.white)]
for r in cat_rows:
    st += [('SPAN', (0, r), (-1, r)), ('BACKGROUND', (0, r), (-1, r), TILE), ('TEXTCOLOR', (0, r), (-1, r), TEAL)]
t.setStyle(TableStyle(st))
story.append(t)
story.append(PageBreak())

story += [Footer('Windows application records  |  T3: 20 Jul - 25 Sep 2026  |  6m: 25 Mar - 25 Sep 2026')]
story += heading('Application use', 'Application categories and other programs',
                 'Category totals for the tracked applications, and other programs started by learner accounts')
story.append(Paragraph('Application use by category', H2))
story.append(table(['Category', 'Device uses T3', 'Learners T3', 'Win focus hours T3', 'Device uses 6m',
                    'Learners 6m', 'Win focus hours 6m', 'Mac hours T3', 'Mac hours 6m'],
                   [list(r) for r in CAT_ROWS], cols(2.3, 1, 1, 1.1, 1, 1, 1.1, 1, 1), num_cols=range(1, 9),
                   total=True, font=8.5, pad=4, hpad=4.5))
story.append(Paragraph('Higher-spec: Autodesk Fusion, Blender, Roblox, Roblox Studio. Mid-spec creative: Audacity, GIMP, '
                       'Inkscape, Minecraft Education, PrusaSlicer, Scribus. Browser/Office: Adobe Reader DC, Chrome, '
                       'Firefox, Microsoft 365 Apps, Microsoft Edge, Safari. Light utility: 7-Zip, Notepad++, PyScripter, '
                       'Python, RDWorks, Solitaire, VLC. Mac hours: Jamf foreground time within the period, all accounts.',
                       NOTE))
LAUNCH = [('Autodesk Fusion', 183, 556, 30, 66), ('Blender', 130, 189, 22, 30), ('Roblox', 0, 0, 7, 9),
          ('Roblox Studio', 0, 0, 9, 10), ('Audacity', 2, 11, 2, 8), ('GIMP', 0, 5, 0, 3), ('Inkscape', 3, 12, 2, 5),
          ('Minecraft Education', 177, 204, 29, 31), ('PrusaSlicer', 0, 0, 13, 22), ('Scribus', 1, 3, 1, 4),
          ('Adobe Reader DC', 12, 168, 3, 26), ('Chrome', 2806, 4291, 69, 91), ('Firefox', 81, 141, 12, 21),
          ('Microsoft 365 Apps', 1, 4, 2, 4), ('Microsoft Edge', 2607, 4811, 65, 90), ('Safari', 0, 0, 0, 0),
          ('7-Zip', 0, 0, 0, 0), ('Notepad++', 20, 90, 10, 14),
          ('PyScripter', 97, 114, 20, 23), ('Python', 132, 171, 21, 23), ('RDWorks', 0, 0, 9, 28),
          ('Solitaire', 0, 0, 0, 13), ('VLC', 3, 7, 2, 7)]
story.append(Paragraph('Other programs started by learner accounts (six months, top 15 by focus time)', H2))
OTHER_WIN = [
    ('Chrome app, Profile1 (kinpkgiljofpcfc)', 1, 1, 1, '1.7'), ('Microsoft Store', 72, 48, 143, '1.6'),
    ('Snipping Tool (ScreenSketch)', 58, 41, 384, '0.9'), ('Windows Camera', 22, 24, 50, '0.9'),
    ('AfterFX.exe (Adobe After Effects)', 1, 2, 7, '0.8'), ('Brave browser', 1, 1, 1, '0.7'),
    ('MSEdge', 1, 1, 1, '0.4'), ('prusa-gcodeviewer.exe', 14, 15, 22, '0.4'),
    ('makerbot-print.exe (MakerBot Print)', 9, 7, 26, '0.2'), ('cmd.exe', 5, 6, 10, '0.2'),
    ('Opera browser', 1, 1, 4, '0.2'), ('Chrome app, Profile1 (ikplgjnhlkgencm)', 1, 1, 2, '0.2'),
    ('Photoshop.exe (Adobe Photoshop)', 4, 4, 8, '0.2'), ('X-VPN Free Unlimited VPN', 2, 4, 26, '0.1'),
    ('Microsoft.AutoGenerated.{BB8885E2-...}', 5, 4, 9, '0.1')]
assert sum(a[3] for a in OTHER_WIN) == 694 and abs(sum(float(a[4]) for a in OTHER_WIN) - 8.8) < 0.4  # source total is unrounded
story.append(table(['Program', 'Learner accounts', 'Devices', 'Launches', 'Focus hours'],
                   [list(a) for a in OTHER_WIN] + [['Total (programs listed)', '', '', 694, '8.8']],
                   cols(3.4, 1.2, 1, 1, 1.1), num_cols=(1, 2, 3, 4), total=True, font=8.3, pad=2.6))
story.append(Paragraph('Launches and focus hours are cumulative UserAssist counters.', NOTE))
story.append(PageBreak())
story += [Footer('Windows application records  |  T3: 20 Jul - 25 Sep 2026  |  6m: 25 Mar - 25 Sep 2026')]
story += heading('Application use', 'Windows launch records',
                 'Prefetch runs that fall inside a learner session, and devices with learner evidence for each application')
story.append(table(['Application', 'Prefetch runs in learner sessions T3', 'Prefetch runs 6m',
                    'Devices with learner evidence T3', 'Devices with learner evidence 6m'],
                   [list(a) for a in LAUNCH], cols(2.6, 1.5, 1.2, 1.5, 1.5), num_cols=(1, 2, 3, 4), font=8.3,
                   pad=2.6))
story.append(PageBreak())

story += [Footer('Mac application foreground time recorded by Jamf (all signed-in accounts)')]
story += heading('Application use', 'Mac applications',
                 'Foreground time within each period, from Jamf application usage (per Mac, all signed-in accounts)')
story.append(Paragraph('Tracked applications on Macs', H2))
story.append(table(['Application', 'Macs used T3', 'Foreground hours T3', 'Macs used 6m', 'Foreground hours 6m'], [
    ['Adobe Reader DC', 1, '0.4', 1, '0.4'], ['Chrome', 54, '404.8', 54, '411.6'],
    ['Microsoft 365 Apps', 2, '2.0', 2, '2.0'], ['Safari', 58, '307.6', 59, '308.3'],
    ['Total', 115, '714.8', 116, '722.3'],
], cols(3, 1.3, 1.3, 1.3, 1.3), num_cols=(1, 2, 3, 4), total=True, pad=4))
story.append(Paragraph('Other applications used on Macs (six months)', H2))
story.append(table(['Application', 'Macs', 'Foreground hours'], [
    ['Music', 18, '213.0'], ['Adobe Photoshop 2026', 42, '124.7'], ['Adobe Photoshop 2025', 12, '45.9'],
    ['Preview', 49, '37.6'], ['Adobe Premiere Pro 2025', 3, '17.4'], ['DaVinci Resolve', 2, '11.7'],
    ['Adobe Illustrator', 15, '11.0'], ['Print Center', 29, '10.3'], ['Adobe Photoshop 2024', 3, '7.8'],
    ['Wacom Center', 48, '7.5'], ['Adobe Bridge 2026', 29, '4.5'], ['iMovie', 2, '3.6'],
], cols(4, 1.5, 1.8), num_cols=(1, 2), pad=4))
story.append(PageBreak())

# =============== Hardware + six months ===============
story += [Footer('Hardware inventory and six-month learner use')]
story += heading('Fleet data', 'Hardware and six-month use', 'Hardware data collected from 185 of 211 devices')
story.append(Paragraph('Hardware', H2))
story.append(table(['Model', 'Count', 'CPU', 'RAM', 'Graphics'], [
    ['HP ProBook 4 G1i 14-inch', 86, 'Intel Core Ultra 5 225U', '15 GB', 'Intel Graphics'],
    ['HP ProBook 450 G10 15.6-inch', 15, 'Intel Core i7-1355U', '16 GB', 'Intel UHD Graphics'],
    ['H610M S2H V2 DDR4 desktop', 11, 'Intel Core i7-14700F', '32 GB', 'NVIDIA GeForce RTX 4060'],
    ['MacBook Pro 14-inch (Nov 2023)', 30, 'Apple M3 Pro', '18 GB', '-'],
    ['MacBook Pro 14-inch (2024)', 29, 'Apple M4', '16 GB', '-'],
    ['MacBook Pro 14-inch (M5)', 1, 'Apple M5', '16 GB', '-'],
    ['iMac 24-inch (2023)', 12, 'Apple M3', '8 GB', '-'],
    ['iMac 21.5-inch Retina 4K (Late 2015)', 1, 'Quad-core Intel Core i5', '8 GB', '-'],
    ['Total', 185, '', '', ''],
], cols(2.9, 0.7, 1.9, 0.7, 2.3), num_cols=(1,), pad=3.5, font=8.5, total=True))
story.append(Spacer(1, 6))
story.append(table(['Installed RAM', '8 GB', '12-16 GB', '24 GB or more', 'Discrete graphics'],
                   [['Share of 185 devices', '7.0%', '87.0%', '5.9%', '11 devices']],
                   cols(2.4, 1, 1, 1.2, 1.4), num_cols=(1, 2, 3, 4), pad=3.5, font=8.5))

story.append(Paragraph('Six-month learner use by device group', H2))
s6rows = json.load(open(sys.argv[3]))['s6']
S6LV = {'Regularly': 'Regular', 'Occasionally': 'Occasional', 'Once': 'One day', 'Not used': 'Not used'}
body = []
tot = dict(used=0, logins=0, lv={k: 0 for k in LEVELS})
for g in GROUPS:
    ss = [s for r, s in zip(rows, s6rows) if r['g'] == g]
    assert all(s[0] == r['device'] for r, s in zip(rows, s6rows))
    used = sum(int(s[6]) > 0 for s in ss)
    lg = sum(int(s[6]) for s in ss)
    lv = {k: sum(S6LV[s[11]] == k for s in ss) for k in LEVELS}
    ln = f'{SIX[g][1]}*' if g in SIX else ('179 (Macs)' if g == 'MacBooks' else '')
    if g in SIX:
        assert (used, lg) == (SIX[g][0], SIX[g][2]), g
    body.append([g, len(ss), used, ln, lg] + [lv[k] for k in LEVELS])
    tot['used'] += used
    tot['logins'] += lg
    for k in LEVELS:
        tot['lv'][k] += lv[k]
assert tot['used'] == 158 and tot['logins'] == 4847 and [tot['lv'][k] for k in LEVELS] == [78, 77, 3, 53]
body.append(['All devices', 211, 158, 469, 4847] + [tot['lv'][k] for k in LEVELS])
t = table(['Device group', 'Devices', 'Used', 'Learner accounts', 'Learner logins'] + LEVELS, body,
          cols(2.55, 0.9, 0.8, 1.3, 1.05, 1.0, 1.3, 0.95, 0.95), num_cols=range(1, 9), total=True, font=8.5, pad=4,
          hpad=4.5)
t.setStyle(TableStyle([('SPAN', (3, 4), (3, 5)), ('VALIGN', (3, 4), (3, 5), 'MIDDLE')]))
story.append(t)
story.append(Paragraph('* Sum of the learner counts for each OU in the group; a learner who used devices in more than '
                       'one of these OUs is counted once per OU. Mac login records begin 15 July 2026.', NOTE))
story.append(NextPageTemplate('land'))
story.append(PageBreak())

# =============== Register (landscape) ===============
LW = landscape(A4)[0] - LM - RM
order = {g: i for i, g in enumerate(GROUPS)}
reg = sorted(rows, key=lambda r: (order[r['g']], r['campus2'] or 'zz', r['device']))
PER = 28
hdr = ['No.', 'Device', 'Device group', 'Campus', 'Unique learners', 'Learner logins', 'Days used',
       'Logins / week', 'Days / week', 'Last learner login', 'Level of use', 'First record']
wid = cols(0.6, 1.5, 1.8, 0.9, 1.0, 1.0, 0.85, 0.95, 0.9, 1.15, 1.15, 1.05, width=LW)
pages = [reg[i:i + PER] for i in range(0, len(reg), PER)]
for pi, chunk in enumerate(pages):
    a, b = pi * PER + 1, pi * PER + len(chunk)
    gs = []
    for r in chunk:
        if SHORT[r['g']] not in gs:
            gs.append(SHORT[r['g']])
    story.append(Footer('Term 3 device register  |  20 July - 25 September 2026  |  '
                        'Campus from campus OU, otherwise recorded location'))
    story.append(Paragraph('DEVICE REGISTER  |  TERM 3', KICK))
    story.append(Paragraph('Device-level learner use',
                           ps('h1l', parent=H1, fontSize=19, leading=22)))
    story.append(Paragraph(f'Rows {a:03d}-{b:03d} of 211  |  {", ".join(gs)}', ps('sl', parent=SUB, spaceAfter=8)))
    body = []
    for i, r in enumerate(chunk):
        body.append([f'{a + i:03d}', r['device'], SHORT[r['g']], r['campus2'] or '-', r['learners'], r['logins'],
                     r['days'], f"{r['lpw']:.1f}", f"{r['dpw']:.1f}", r['last'], r['cat'], r['first']])
    story.append(table(hdr, body, wid, num_cols=(4, 5, 6, 7, 8), font=7.8, pad=1.8))
    if pi < len(pages) - 1:
        story.append(PageBreak())


class Doc(BaseDocTemplate):
    pass


doc = Doc(OUT, pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=TM, bottomMargin=BM,
          title='Specialist device usage - Term 3 2026', author='Rolleston College ICT')
fp = Frame(LM, BM, PW - LM - RM, PH - TM - BM, id='p', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
lw, lh = landscape(A4)
fl = Frame(LM, BM, lw - LM - RM, lh - 18 * mm - BM, id='l', leftPadding=0, rightPadding=0, topPadding=0,
           bottomPadding=0)
doc.addPageTemplates([PageTemplate('port', [fp], pagesize=A4), PageTemplate('land', [fl], pagesize=landscape(A4))])
doc.build(story, canvasmaker=NumberedCanvas)
print('ok')
