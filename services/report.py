"""Writes the daily outputs: a self-contained report.html (filterable table plus a
Leaflet map), brief.md and brief.json. The HTML embeds its data as JSON and
needs no server; Leaflet and map tiles load from the internet when opened."""
import html
import json
import os
from typing import Dict, List


def _money(v) -> str:
    return f"£{v:,.0f}" if isinstance(v, (int, float)) else "?"


def listing_line(r: Dict, criteria) -> str:
    status = {"new": "NEW", "reduced": "REDUCED", "earlier": "earlier"}.get(r["status"], r["status"])
    bits = [f"**{status}** {_money(r['price'])}"]
    if r.get("reduced_from"):
        bits[0] += f" (was {_money(r['reduced_from'])})"
    elif r.get("alert_said_reduced") and r["status"] == "new":
        bits[0] += " (Rightmove marks it reduced)"
    bits.append(f"{r.get('beds') or '?'}-bed {r.get('type') or 'home'}")
    bits.append(f"[{r.get('address') or 'address not given'}]({r['url']})" if r.get("url") else (r.get("address") or "?"))
    tier = f"tier {r['tier']}" if r.get("tier") else "outside tiers"
    km = f", {r['church_km']} km to church" if r.get("church_km") is not None else ""
    bits.append(tier + km)
    bits.append(f"garden {r['garden']}, parking {r['parking']}")
    if r.get("epc"):
        bits.append(f"EPC {r['epc']}")
    bits.append(f"condition: {r['condition']} (estimate)")
    c = r.get("costs") or {}
    if c:
        bits.append(f"5% deposit {_money(c['deposit_5'])}, about {_money(c['monthly_5'])}/month; "
                    f"stamp duty {_money(c['stamp_duty_ftb'])} first-time buyer / {_money(c['stamp_duty'])} standard")
    return " · ".join(bits)


def _flags(r: Dict, criteria) -> List[str]:
    flags = []
    if criteria.preferred_max_price and (r.get("price") or 0) > criteria.preferred_max_price:
        flags.append(f"over the preferred {_money(criteria.preferred_max_price)}")
    if r.get("tier") == 3:
        flags.append(f"tier 3 ({r.get('tier_place')})")
    if r.get("tier") is None:
        flags.append("not in a listed village")
    c = r.get("costs") or {}
    if c and not c.get("savings_cover_5pct"):
        flags.append(f"5% deposit is {_money(c['deposit_5'] - c['savings'])} more than savings")
    f = r.get("flood") or {}
    if f.get("live_warnings"):
        flags.append("live flood warning nearby")
    if r.get("tenure") == "Leasehold":
        flags.append("leasehold: check lease length and charges")
    if r.get("precision") in ("outcode", "village/town", "not found"):
        flags.append(f"location approximate ({r['precision']})")
    return flags


def build_brief(rows: List[Dict], rejected: List[Dict], meta: Dict, criteria, report_path: str) -> Dict:
    today = [r for r in rows if r["status"] in ("new", "reduced")]
    today.sort(key=lambda r: (r.get("tier") or 9, r.get("church_km") or 99, r.get("price") or 0))
    brief = {
        "date": meta["date"],
        "emails_read": meta["emails"],
        "listings_in_emails": meta["parsed"],
        "new": sum(r["status"] == "new" for r in rows),
        "reduced": sum(r["status"] == "reduced" for r in rows),
        "filtered_out": len(rejected),
        "report": report_path,
        "listings": [dict(id=r["id"], status=r["status"], price=r["price"], address=r["address"], url=r["url"],
                          tier=r.get("tier"), church_km=r.get("church_km"), beds=r.get("beds"),
                          garden=r["garden"], parking=r["parking"], condition=r["condition"],
                          flags=_flags(r, criteria)) for r in today],
    }
    lines = [f"# House brief, {meta['date']}", ""]
    if not today:
        lines.append("Nothing new or reduced in today's alert emails.")
    else:
        lines.append(f"{brief['new']} new and {brief['reduced']} reduced in your range "
                     f"({criteria.min_beds}-{criteria.max_beds} beds, up to {_money(criteria.max_price)}).")
        lines.append("")
        for r, b in zip(today, brief["listings"]):
            lines.append("- " + listing_line(r, criteria))
            if b["flags"]:
                lines.append("  - Check: " + "; ".join(b["flags"]))
    lines += ["", f"Read {meta['emails']} alert email(s) with {meta['parsed']} listing(s); "
              f"{len(rejected)} were outside the criteria."]
    lines += ["", f"Full report with map and filters: {report_path}",
              "", "_Condition, garden and parking come from the agent's wording, and the mortgage figures are "
              "illustrative. Check them before you rely on them._"]
    brief["markdown"] = "\n".join(lines) + "\n"
    return brief


def write_outputs(out_dir: str, rows: List[Dict], rejected: List[Dict], meta: Dict, criteria) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = {k: os.path.join(out_dir, f) for k, f in
             (("report", "report.html"), ("brief_md", "brief.md"), ("brief_json", "brief.json"))}
    brief = build_brief(rows, rejected, meta, criteria, os.path.abspath(paths["report"]))
    with open(paths["report"], "w", encoding="utf-8") as f:
        f.write(render_html(rows, meta, criteria))
    with open(paths["brief_md"], "w", encoding="utf-8") as f:
        f.write(brief["markdown"])
    with open(paths["brief_json"], "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in brief.items() if k != "markdown"}, f, indent=2)
    return paths


def render_html(rows: List[Dict], meta: Dict, criteria) -> str:
    payload = {"rows": rows, "church": criteria.church, "preferred": criteria.preferred_max_price,
               "max_price": criteria.max_price, "meta": meta}
    data = json.dumps(payload).replace("</", "<\\/")
    title = html.escape(f"Houses near {criteria.church.get('name', 'church')} - {meta['date']}")
    return TEMPLATE.replace("{{TITLE}}", title).replace("{{DATA}}", data)


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{TITLE}}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<style>
body{font-family:system-ui,sans-serif;margin:0;color:#222}
header{padding:12px 16px;background:#1f3b57;color:#fff}header h1{font-size:18px;margin:0}
header p{margin:4px 0 0;font-size:13px;opacity:.85}
.wrap{display:grid;grid-template-columns:250px 1fr;gap:0}
aside{padding:12px;border-right:1px solid #ddd;font-size:13px;background:#fafafa}
aside fieldset{border:0;padding:0;margin:0 0 12px}aside legend{font-weight:600;margin-bottom:4px}
aside label{display:block}aside input[type=number]{width:90px}
main{padding:12px;overflow:auto}#map{height:360px;margin-bottom:12px;border:1px solid #ccc}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:6px;border-bottom:1px solid #eee;text-align:left;vertical-align:top}
th{cursor:pointer;background:#f0f3f6;position:sticky;top:0}tr.row:hover{background:#f7fbff}
.badge{display:inline-block;padding:1px 6px;border-radius:8px;font-size:11px;color:#fff}
.new{background:#2e7d32}.reduced{background:#c62828}.earlier{background:#777}
.t1{color:#1b5e20;font-weight:600}.t2{color:#e65100}.t3{color:#b71c1c}
.detail td{background:#fcfcfc;font-size:12px}.detail h4{margin:6px 0 2px}.est{color:#8a6d00}
.muted{color:#777}#count{font-weight:600}
@media(max-width:800px){.wrap{grid-template-columns:1fr}aside{border-right:0}}
</style></head><body>
<header><h1>{{TITLE}}</h1><p id="sub"></p></header>
<div class="wrap"><aside id="filters"></aside>
<main><div id="map"></div><p><span id="count"></span> shown. Click a row for area details; click a heading to sort.</p>
<table id="t"><thead><tr>
<th data-k="status">Status</th><th data-k="price">Price</th><th data-k="beds">Beds</th><th data-k="type">Type</th>
<th data-k="address">Address</th><th data-k="tenure">Tenure</th><th data-k="tier">Tier</th><th data-k="church_km">Church km</th>
<th data-k="garden">Garden</th><th data-k="parking">Parking</th><th data-k="epc">EPC</th><th data-k="flood_flag">Flood</th>
<th data-k="condition">Condition*</th></tr></thead><tbody></tbody></table>
<p class="muted">*Condition is an estimate from the listing wording and EPC, not a survey. Garden and parking are read from the text.
Mortgage figures are illustrative repayments. Stamp duty uses England rates from April 2025.
Sources: Rightmove alert emails, postcodes.io, OpenStreetMap Nominatim, data.police.uk, Environment Agency, DfE GIAS, HM Land Registry price-paid data (Crown copyright, OGL).</p>
</main></div>
<script id="data" type="application/json">{{DATA}}</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const rows=D.rows.map(r=>Object.assign(r,{flood_flag:!r.flood?'unknown':(r.flood.live_warnings.length?'live warning':(r.flood.areas_within_1km.length?'alert area':'none')),tier_s:r.tier?String(r.tier):'none'}));
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>v==null?'?':'£'+Math.round(v).toLocaleString('en-GB');
document.getElementById('sub').textContent=`${D.meta.emails} alert email(s) read on ${D.meta.date}. Up to ${money(D.max_price)} (preferred ${money(D.preferred)}).`;
const facets=[['status','Status'],['tier_s','Church tier'],['type','Type'],['tenure','Tenure'],['garden','Garden'],['parking','Parking'],['epc','EPC'],['flood_flag','Flood'],['condition','Condition (estimate)']];
const F=document.getElementById('filters');
let h=`<fieldset><legend>Price</legend><label>min <input type=number id=pmin step=5000></label><label>max <input type=number id=pmax step=5000 value="${D.max_price||''}"></label></fieldset>
<fieldset><legend>Beds</legend><label>min <input type=number id=bmin min=0 max=9></label></fieldset>
<fieldset><legend>Max km to church</legend><input type=number id=kmax step=0.5></fieldset>`;
for(const [k,label] of facets){const vals=[...new Set(rows.map(r=>r[k]==null?'unknown':String(r[k])))].sort();
 h+=`<fieldset><legend>${label}</legend>`+vals.map(v=>`<label><input type=checkbox data-f="${k}" value="${esc(v)}" checked> ${esc(v)} (${rows.filter(r=>String(r[k]==null?'unknown':r[k])===v).length})</label>`).join('')+'</fieldset>';}
F.innerHTML=h+'<button id=reset>Reset</button>';
let map=null,layer=null;
if(window.L){map=L.map('map').setView([D.church.lat,D.church.lng],12);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
 L.marker([D.church.lat,D.church.lng],{title:D.church.name}).addTo(map).bindPopup(esc(D.church.name));
 [2,5,8].forEach(km=>L.circle([D.church.lat,D.church.lng],{radius:km*1000,color:'#1f3b57',weight:1,fill:false,dashArray:'4'}).addTo(map));
 layer=L.layerGroup().addTo(map);}else{document.getElementById('map').innerHTML='<p class=muted>Map needs an internet connection (Leaflet).</p>';}
let sortK='tier',sortDir=1;
function pass(r){const n=id=>{const v=document.getElementById(id).value;return v===''?null:+v};
 if(n('pmin')!=null&&r.price<n('pmin'))return false;if(n('pmax')!=null&&r.price>n('pmax'))return false;
 if(n('bmin')!=null&&r.beds!=null&&r.beds<n('bmin'))return false;if(n('kmax')!=null&&r.church_km!=null&&r.church_km>n('kmax'))return false;
 for(const cb of F.querySelectorAll('input[type=checkbox]:not(:checked)')){if(String(r[cb.dataset.f]==null?'unknown':r[cb.dataset.f])===cb.value)return false;}
 return true;}
function detail(r){const c=r.costs||{},cr=r.crime,fl=r.flood,cp=r.comparables||{};
 let s=`<h4>Costs (illustrative)</h4>Stamp duty: ${money(c.stamp_duty_ftb)} first-time buyer, ${money(c.stamp_duty)} standard.
 5% deposit ${money(c.deposit_5)} (about ${money(c.monthly_5)}/month); 10% deposit ${money(c.deposit_10)} (about ${money(c.monthly_10)}/month), at ${c.rate_pct}% over ${c.term_years} years. Savings ${money(c.savings)}.
 Council tax band: <a href="${r.council_tax_link}" target=_blank>check on GOV.UK</a>${r.postcode?' for '+esc(r.postcode):''}.`;
 s+=`<h4>Area</h4>Location: ${esc(r.precision||'unknown')} precision${r.parish?', parish '+esc(r.parish):''}. `;
 s+=cr?`Crime within 1 mile (${esc(cr.month)}): ${cr.total} reports; top: ${cr.top.map(t=>esc(t.category)+' '+t.count).join(', ')}. `:'Crime: not available. ';
 s+=fl?`Flood: ${fl.areas_within_1km.length?'within 1 km of '+fl.areas_within_1km.map(esc).join('; '):'no EA flood alert areas within 1 km'}${fl.live_warnings.length?'. <b>Live: '+fl.live_warnings.map(esc).join('; ')+'</b>':''}. `:'Flood: not available. ';
 s+=`<a href="${r.flood_link}" target=_blank>Long-term flood risk</a>.`;
 s+='<h4>Nearest primary schools</h4>'+((r.schools||[]).length?(r.schools.map(x=>`${esc(x.name)} (${x.km} km${x.religious?', '+esc(x.religious):''}) <a href="${x.link}" target=_blank>Ofsted</a>`).join('<br>')):'None found within range, or not available.');
 s+='<h4>Sold prices (Land Registry)</h4>';
 const sm=(o)=>`${o.count} sales, median ${money(o.median)}, latest ${money(o.latest.price)} on ${esc(o.latest.date)}`;
 s+=(cp.street?`Same street (${esc(cp.street.label)}): ${sm(cp.street)}.<br>`:'')+(cp.area?`${esc(cp.area.label)}, type ${esc(cp.type)}: ${sm(cp.area)}.`:(cp.street?'':'Not available.'));
 s+=`<h4>Condition estimate</h4><span class=est>${esc(r.condition)}</span>${(r.condition_signals||[]).length?' from: '+r.condition_signals.map(esc).join(', '):''}.`;
 s+=`<h4>Listing text</h4>${esc(r.description)}`;return s;}
function render(){const tb=document.querySelector('#t tbody');tb.innerHTML='';if(layer)layer.clearLayers();
 const vis=rows.filter(pass).sort((a,b)=>{const x=a[sortK],y=b[sortK];if(x==null)return 1;if(y==null)return -1;return (x>y?1:x<y?-1:0)*sortDir||(a.price-b.price);});
 for(const r of vis){const tr=document.createElement('tr');tr.className='row';
  const over=D.preferred&&r.price>D.preferred?' title="over preferred price" style="color:#b71c1c"':'';
  tr.innerHTML=`<td><span class="badge ${r.status}">${r.status}</span></td><td${over}>${money(r.price)}${r.reduced_from?'<br><s class=muted>'+money(r.reduced_from)+'</s>':''}</td><td>${r.beds??'?'}</td><td>${esc(r.type)}</td>
  <td><a href="${esc(r.url)}" target=_blank>${esc(r.address||'listing')}</a></td><td>${esc(r.tenure)}</td><td class="t${r.tier||''}">${r.tier?r.tier+' '+esc(r.tier_place):'none'}</td>
  <td>${r.church_km??'?'}</td><td>${esc(r.garden)}</td><td>${esc(r.parking)}</td><td>${esc(r.epc||'?')}</td><td>${esc(r.flood_flag)}</td><td class=est>${esc(r.condition)}</td>`;
  const dt=document.createElement('tr');dt.className='detail';dt.style.display='none';dt.innerHTML=`<td colspan=13>${detail(r)}</td>`;
  tr.onclick=e=>{if(e.target.tagName!=='A')dt.style.display=dt.style.display==='none'?'':'none'};tb.append(tr,dt);
  if(layer&&r.lat!=null){const col={1:'#2e7d32',2:'#ef6c00',3:'#c62828'}[r.tier]||'#555';
   L.circleMarker([r.lat,r.lng],{radius:8,color:col,fillOpacity:.8}).addTo(layer).bindPopup(`<b>${money(r.price)}</b> ${r.beds??'?'}-bed ${esc(r.type)}<br>${esc(r.address)}<br>${r.church_km??'?'} km to church<br><a href="${esc(r.url)}" target=_blank>Rightmove</a>`);}}
 document.getElementById('count').textContent=vis.length+' of '+rows.length;}
F.addEventListener('input',render);document.getElementById('reset').onclick=()=>{F.querySelectorAll('input[type=checkbox]').forEach(c=>c.checked=true);['pmin','bmin','kmax'].forEach(i=>document.getElementById(i).value='');document.getElementById('pmax').value=D.max_price||'';render();};
document.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortDir=k===sortK?-sortDir:1;sortK=k;render();});
render();
if(map){const pts=rows.filter(r=>r.lat!=null).map(r=>[r.lat,r.lng]);if(pts.length){pts.push([D.church.lat,D.church.lng]);map.fitBounds(pts,{padding:[30,30],maxZoom:14});}}
</script></body></html>
"""
