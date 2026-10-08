import re, json, sys
lines=open('orig/orig.txt').read().split('\n')
def section(a,b): return lines[a:b]
pat=re.compile(r'^\s*(\S.*?)\s{2,}(Win|Mac)\s+(Junior|Senior|Unknown)\s+(.+?)\s{2,}(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)\s+(Not used|Once|Regularly|Occasionally)\s+(\S+)\s*$')
def parse(a,b):
    out=[]
    for l in lines[a:b]:
        m=pat.match(l)
        if m: out.append(m.groups())
    return out
t3=parse(406,914); s6=parse(1230,1738)
print(len(t3),len(s6))
json.dump({'t3':t3,'s6':s6},open('orig_regs.json','w'))
rows=json.load(open('rows.json'))
cat={'Not used':'Not used','Once':'One day','Regularly':'Regular','Occasionally':'Occasional'}
loc={'Junior':'Junior','Senior':'Senior','Unknown':'-'}
errs=0
for i,(o,r) in enumerate(zip(t3,rows)):
    dev,plat,l,ou,area,ln,lg,d,lpw,dpw,last,lv,first=o
    exp=(dev,loc[l],int(ln),int(lg),int(d),float(lpw),float(dpw),last.replace('–','-'),cat[lv],first.replace('Never','-'))
    got=(r['device'],r['campus'],r['learners'],r['logins'],r['days'],r['lpw'],r['dpw'],r['last'],r['cat'],r['first'])
    if exp!=got: errs+=1; print(i+1,exp,got)
print('T3 mismatches',errs)
from collections import Counter
print(Counter(o[3] for o in t3))
print(Counter(o[4] for o in t3))
