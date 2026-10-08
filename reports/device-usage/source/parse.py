import re, json, sys
from collections import Counter, defaultdict
from datetime import date
pat=re.compile(r'^\s*(\d{3})\s+(.+?)\s{2,}(Junior|Senior|-)\s+([A-Z])\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)\s+(Not used|One day|Regular|Occasional)\s+(\S+)\s*$')
rows=[]
for line in open(sys.argv[1]):
    m=pat.match(line)
    if m:
        g=m.groups()
        rows.append(dict(no=int(g[0]),device=g[1].strip(),campus=g[2],ou=g[3],learners=int(g[4]),logins=int(g[5]),days=int(g[6]),lpw=float(g[7]),dpw=float(g[8]),last=g[9],cat=g[10],first=g[11]))
print(len(rows))
def grp(r):
    if r['ou']=='M':
        return 'iMac' if r['device'].startswith(('RCWS','IMAC')) else 'MacBook'
    return {'A':'DigiTech COW','C':'DigiTech COW','B':'DigiTech desktop','D':'DigiTech desktop','E':'DigiTech desktop','F':'DVC COW','G':'DVC COW','H':'DVC COW'}[r['ou']]
for r in rows:
    r['group']=grp(r)
    oc={'C':'Junior','G':'Junior','H':'Senior'}.get(r['ou'])
    r['campus2']=oc or (r['campus'] if r['campus']!='-' else None)
    r['camp_src']='OU' if oc else ('Location' if r['campus']!='-' else None)
print(Counter(r['group'] for r in rows))
print(Counter(r['campus2'] for r in rows))
print(Counter(r['campus'] for r in rows))
# conflicts
for r in rows:
    if r['camp_src']=='OU' and r['campus']!='-' and r['campus']!=r['campus2']: print('conflict',r['device'],r['ou'],r['campus'])
# checks
for ou in 'ABCDEFGHM':
    s=[r for r in rows if r['ou']==ou]
    print(ou,len(s),sum(r['logins']>0 for r in s),sum(r['logins'] for r in s))
print(Counter(r['cat'] for r in rows), sum(r['logins'] for r in rows))
# lpw/dpw checks
bad=[r['device'] for r in rows if abs(r['logins']/10-r['lpw'])>0.051 or abs(r['days']/10-r['dpw'])>0.051]
print('bad',bad)
for r in rows:
    if r['cat']=='Regular' and r['days']<5: print('reg<5',r)
    if (r['cat']=='One day')!=(r['days']==1): print('oneday mismatch',r)
    if (r['cat']=='Not used')!=(r['days']==0): print('notused mismatch',r)
json.dump(rows,open('rows.json','w'),indent=0)
