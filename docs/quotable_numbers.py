"""Recomputes every number quoted in the presenter notes from the raw dataset.
Read-only, standard library only. Run:  python3 -I docs/quotable_numbers.py
The customer flag follows build.py (A8a): a speaker is a customer if the meeting has an outside
attendee and the speaker's name is not among the aegiscloud.com invitees' names.
Type labels here are the exploration rule (title starts 'Support Case' / any outside attendee),
NOT the Stage 0 pipeline output, which has not been run."""
import json,glob,re,collections,statistics as st,math,os
root=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","dataset")
M=[]
for d in sorted(glob.glob(root+"/*/")):
    mi=json.load(open(d+"meeting-info.json"));s=json.load(open(d+"summary.json"));t=json.load(open(d+"transcript.json"))["data"]
    ext=[e for e in mi["allEmails"] if not e.endswith("@aegiscloud.com")]
    ty="support" if mi["title"].startswith("Support Case") else ("external" if ext else "internal")
    staff={e.split("@")[0].replace("."," ") for e in mi["allEmails"] if e.endswith("@aegiscloud.com")}
    cust=[bool(ext) and re.sub(r"[^a-z ]","",x["speaker_name"].lower()) not in staff for x in t]
    M.append(dict(id=mi["meetingId"],t=mi["title"],ty=ty,s=s,tr=t,cust=cust,month=mi["startTime"][:7],ne=len(ext)))
def corr(x,y):
    mx,my=st.mean(x),st.mean(y);return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
bal=lambda tr:(sum(x["sentimentType"]=="positive" for x in tr)-sum(x["sentimentType"]=="negative" for x in tr))/len(tr)
P=lambda k,v:print(f"{k:<46}{v}")
T=("support","external","internal")
P("N1 meetings",len(M))
P("N2 rule types support/external/internal",[sum(m["ty"]==t for m in M) for t in T])
words=sum(len(x["sentence"].split()) for m in M for x in m["tr"])
P("N3 sentences",sum(len(m["tr"]) for m in M));P("N3 words",words);P("N3 est. tokens (words x 1.35)",round(words*1.35))
P("N3 median words/call full vs summary",(int(st.median(sum(len(x['sentence'].split()) for x in m['tr']) for m in M)),int(st.median(len(m['s']['summary'].split()) for m in M))))
c=collections.Counter(x["sentimentType"] for m in M for x in m["tr"]);P("N4 provided sentence labels",dict(c))
sc=[m["s"]["sentimentScore"] for m in M];P("N5 corr(score, pos-neg balance) all",round(corr(sc,[bal(m["tr"]) for m in M]),2))
P("N5 corr by type",{t:round(corr([m["s"]["sentimentScore"] for m in M if m["ty"]==t],[bal(m["tr"]) for m in M if m["ty"]==t]),2) for t in T})
P("N6 mean provided score by rule type",{t:round(st.mean(m["s"]["sentimentScore"] for m in M if m["ty"]==t),2) for t in T})
P("N6 mean provided score by month",{k:round(st.mean(m["s"]["sentimentScore"] for m in M if m["month"]==k),2) for k in sorted({m["month"] for m in M})})
P("N7 distinct provided scores / meetings at 2.4",(len(set(sc)),sc.count(2.4)))
tags=collections.Counter(x.lower() for m in M for x in m["s"]["topics"])
P("N8 topic tags / distinct / used once",(sum(tags.values()),len(tags),sum(v==1 for v in tags.values())))
for t in T:
    X=[m for m in M if m["ty"]==t];cc=collections.Counter(x["sentimentType"] for m in X for x in m["tr"]);n=sum(cc.values())
    P(f"N9 label shares {t} pos/neu/neg %",[round(100*cc[k]/n,1) for k in("positive","neutral","negative")])
for t in ("support","external"):
    cn=[];en=[]
    for m in M:
        if m["ty"]!=t:continue
        c_=[x for x,f in zip(m["tr"],m["cust"]) if f];e_=[x for x,f in zip(m["tr"],m["cust"]) if not f]
        if c_ and e_:cn.append(sum(x["sentimentType"]=="negative" for x in c_)/len(c_));en.append(sum(x["sentimentType"]=="negative" for x in e_)/len(e_))
    P(f"N10 {t}: customer vs staff negative % (calls)",(round(100*st.mean(cn),1),round(100*st.mean(en),1),len(cn)))
def thirds(tr):
    k=len(tr)//3;f,l=tr[:k],tr[-k:];ng=lambda a:sum(x["sentimentType"]=="negative" for x in a)/len(a);return ng(f),ng(l)
for t in T:
    X=[thirds(m["tr"]) for m in M if m["ty"]==t];P(f"N11 {t}: negative % first third -> last third",(round(100*st.mean(a for a,_ in X),1),round(100*st.mean(b for _,b in X),1)))
mods={"Detect":r"\bDetect\b","Comply":r"\bComply\b","Identity":r"\bIdentity\b|SSO|SAML|SCIM|LDAP|MFA","Protect":r"\bProtect\b","Backup":r"[Bb]ackup|CloudPrime|restore"}
hit=[{k for k,p in mods.items() if re.search(p,m["t"]+" "+m["s"]["summary"]+" "+" ".join(m["s"]["topics"]))} for m in M]
P("N12 calls mentioning >=1 module / >1 module",(sum(bool(h) for h in hit),sum(len(h)>1 for h in hit)))
P("N12 per module",{k:sum(k in h for h in hit) for k in mods})
op=re.compile(r"thank you for calling|support,? this is|how can i help",re.I)
P("N13 opening (first 2 utterances) matches greeting regex",{t:sum(bool(op.search(" ".join(x['sentence'] for x in m['tr'][:2]))) for m in M if m['ty']==t) for t in T})
fam={"Outage & incident response":r"outage|incident|post-?mortem|war room|downtime|single point|cascading","Compliance & audit":r"complian|audit|soc ?2|hipaa|iso ?27|pci|certif|regulat","Renewal, pricing & billing":r"renewal|contract|pricing|billing|invoice|overage|licens|discount","Churn & competitive risk":r"churn|compet|sentinelshield|vendor comparison|win/loss|retention","Onboarding & rollout":r"onboard|kickoff|deployment|rollout|adoption|launch|early access|setup","Identity & access":r"identity|sso|saml|mfa|scim|ldap|provisioning","Product roadmap & planning":r"roadmap|sprint|planning|feature request|retro|standup|all hands|design review","Integrations, backup & data":r"integration|connector|api |backup|restore|siem|logvault|false positive"}
nth=collections.Counter(sum(bool(re.search(p,(m["t"]+" "+" ".join(m["s"]["topics"])).lower())) for p in fam.values()) for m in M)
P("N14 keyword themes per call (title+topics): 1 theme",nth[1]);P("N14 distribution",dict(sorted(nth.items())))
# T1 exploration: relabel the three escalation calls by title prefix (a manual judgment, exploration only)
rel=("URGENT: Blackridge","URGENT: Cobalt","ESCALATION: Northstar")
lab2=[("support" if m["t"].startswith(rel) else m["ty"]) for m in M]
P("T1 calls relabeled by hand",sum(a!=m["ty"] for a,m in zip(lab2,M)))
P("T1 mean support/external before",(round(st.mean(m["s"]["sentimentScore"] for m in M if m["ty"]=="support"),2),round(st.mean(m["s"]["sentimentScore"] for m in M if m["ty"]=="external"),2)))
P("T1 mean support/external after",(round(st.mean(m["s"]["sentimentScore"] for a,m in zip(lab2,M) if a=="support"),2),round(st.mean(m["s"]["sentimentScore"] for a,m in zip(lab2,M) if a=="external"),2)))
