"""Regenerate ../index.html from bills.json, matching the gas/luce layout.

The published report is self-contained: annual totals are computed in-page from the
`bills` array, so a routine monthly update just appends to that array (see the
consumi-rifiuti-quarterly-update skill). This script exists to rebuild the whole
page from data if the layout ever needs changing.

    python3 gen_report.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
bills = json.load(open(HERE / "bills.json"))

def js_bills():
    out = []
    for b in bills:
        note = b.get("note", "")
        n = f',note:"{note}"' if note else ""
        out.append(
            '{{id:"{id}",start:"{start}",end:"{end}",litri:{litri},conf:{conf},'
            'litriMin:{lmin},fissa:{fissa},varia:{varia},altri:{altri},imposte:{imp},'
            'iva:{iva},tot:{tot}{note}}}'.format(
                id=b["id"], start=b["start"], end=b["end"],
                litri=round(b["litriReal"]), conf=b["nReal"], lmin=b["litriBill"],
                fissa=b["fissa"], varia=b["variabile"], altri=b["altri"],
                imp=b["imposte"], iva=b["iva"], tot=b["tot"], note=n)
        )
    return ",\n".join(out)


first, last = bills[0], bills[-1]


def it(d):
    y, m, dd = d.split("-")
    return f"{dd}/{m}/{y}"


HTML = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Consumi e costi dei rifiuti — andamento storico</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" integrity="sha384-iU8HYtnGQ8Cy4zl7gbNMOhsDTTKX02BTXptVP/vqAWIaTfM7isw76iyZCsjL2eVi" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js" integrity="sha384-/XXDzxe4FsGiAe50i/u9pY/Vy/uX654MHB1xoc1BJNnH1WXHhqHga9g3q5tF4gj7" crossorigin="anonymous"></script>
<link href="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css" rel="stylesheet">
<style>
  :root{ color-scheme: light; --bg:#f7f8fa; --card:#ffffff; --ink:#1c2430; --muted:#5b6572;
         --fissa:#4a6fa5; --varia:#2e9e5b; --altri:#f2a007; --imposte:#8e6bb0; --iva:#9aa3af;
         --min:#c4c9d1; --line:#e2e5ea; }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px;}
  .back{display:inline-block;font-size:13px;color:var(--muted);text-decoration:none;margin-bottom:14px;}
  .back:hover{color:#2f6fed;}
  h1{font-size:22px;margin:0 0 4px;}
  .subtitle{color:var(--muted);font-size:14px;margin:0 0 24px;}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:28px;}
  .kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;}
  .kpi .label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;}
  .kpi .value{font-size:22px;font-weight:600;margin-top:4px;}
  .kpi .sub{font-size:12px;color:var(--muted);margin-top:2px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin-bottom:22px;}
  .card h2{font-size:15px;margin:0 0 14px;}
  .chart-box{position:relative;height:320px;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px;}
  @media (max-width:860px){.grid2{grid-template-columns:1fr;}}
  .legend-row{display:flex;flex-wrap:wrap;gap:18px;font-size:12px;color:var(--muted);margin-top:6px;}
  .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;}
  .notes{font-size:13px;color:var(--muted);line-height:1.6;}
  .notes b{color:var(--ink);}
  #table{font-size:13px;}
  .gridjs-wrapper{border-radius:10px;}
  .footer{font-size:12px;color:var(--muted);text-align:center;margin-top:10px;}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="../">&larr; Tutti i report</a>
  <h1>Consumi e costi dei rifiuti — andamento storico</h1>
  <p class="subtitle">__NBILLS__ bollette analizzate · dal __FIRST__ al __LAST__ · gestore: Hera · Tariffa Corrispettiva Puntuale · fatturazione quadrimestrale</p>
  <div class="kpis" id="kpis"></div>
  <div class="card">
    <h2>Rifiuto indifferenziato conferito per bolletta (litri) — reale vs. fatturato</h2>
    <div class="chart-box"><canvas id="litriChart"></canvas></div>
    <div class="legend-row">
      <span><span class="dot" style="background:var(--varia)"></span>Litri effettivamente conferiti (svuotamenti del bidone da 40 L)</span>
      <span><span class="dot" style="background:var(--min)"></span>Litri minimi fatturati (Quota Variabile di Base)</span>
    </div>
  </div>
  <div class="card">
    <h2>Ripartizione della spesa per bolletta (€)</h2>
    <div class="chart-box"><canvas id="costChart"></canvas></div>
    <div class="legend-row">
      <span><span class="dot" style="background:var(--fissa)"></span>Quota fissa + normalizzata</span>
      <span><span class="dot" style="background:var(--varia)"></span>Quota variabile (base + aggiuntiva)</span>
      <span><span class="dot" style="background:var(--altri)"></span>Perequative e agevolazioni</span>
      <span><span class="dot" style="background:var(--imposte)"></span>Imposta provinciale</span>
      <span><span class="dot" style="background:var(--iva)"></span>IVA 10%</span>
    </div>
  </div>
  <div class="grid2">
    <div class="card"><h2>Conferimenti annui (litri) — reale vs. minimo</h2><div class="chart-box"><canvas id="yearLitriChart"></canvas></div></div>
    <div class="card"><h2>Spesa annua — ripartizione (€)</h2><div class="chart-box"><canvas id="yearCostChart"></canvas></div></div>
  </div>
  <div class="card">
    <h2>Costo per litro effettivamente conferito (€/litro)</h2>
    <div class="chart-box"><canvas id="priceChart"></canvas></div>
    <div class="legend-row" id="priceLegend"></div>
  </div>
  <div class="card"><h2>Dettaglio bollette</h2><div id="table"></div></div>
  <div class="card notes">
    <h2 style="margin-bottom:8px;">Note sui dati</h2>
    <p><b>Come funziona la Tariffa Corrispettiva Puntuale.</b> A differenza della TARI, qui una parte della bolletta dipende dalla quantità di <b>rifiuto indifferenziato</b> effettivamente prodotta, misurata in litri tramite un bidone da 40 L dotato di chip (matricola HERA01000679). A ogni utenza è attribuita una quantità di <b>litri minimi annui</b>, fatturata comunque come "Quota Variabile di Base"; i conferimenti della raccolta differenziata sono gratuiti.</p>
    <p><b>Si paga il minimo, non il conferito.</b> Nella maggior parte degli anni i litri fatturati (il minimo) sono <i>superiori</i> a quelli realmente conferiti: la quota variabile si comporta quindi di fatto come un secondo costo fisso. Solo quando si supera il minimo scatta la <b>Quota Variabile Aggiuntiva</b>, addebitata a conguaglio l'anno successivo.</p>
    <p><b>Perché tre bollette sono molto più alte.</b> Le bollette gen–apr 2022 (134,66 €), gen–apr 2023 (124,73 €) e gen–apr 2024 (108,96 €) contengono il conguaglio dell'anno precedente: rispettivamente <b>62,33 €</b> per 840 L di eccedenza 2021, <b>54,02 €</b> per 760 L del 2022 e <b>20,73 €</b> per 261,48 L del 2023. Dal 2024 non ci sono più eccedenze.</p>
    <p><b>Il consumo è sceso di due terzi.</b> Dai 1.440 L (36 svuotamenti) del 2021 ai 480 L (12 svuotamenti) del 2025. Va però letto insieme al cambio di nucleo familiare: dal <b>04/10/2023</b> l'utenza passa da 2 persone "non residenti" a 4 "residenti", e i litri minimi annui salgono da 600 a 840. La riduzione delle eccedenze è quindi in parte dovuta anche a una soglia più alta.</p>
    <p><b>Conferimenti annui.</b> Le bollette riportano i litri conferiti in modo <b>cumulato dal 1° gennaio</b>, non per periodo: il dato per singola bolletta qui mostrato è ricavato per differenza fra bollette consecutive dello stesso anno. La somma dei litri fatturati ricostruita in questo modo coincide con i minimi annui dichiarati da Hera (600,00 nel 2021-2022, 658,52 nel 2023, 840,00 nel 2024, 839,99 nel 2025).</p>
    <p><b>Anni parziali.</b> <b>2020</b> è coperto da una sola bolletta (set–dic): i 480 L indicati sono il totale dell'intero anno solare, non del solo quadrimestre. <b>2026</b> si ferma alla bolletta gen–apr. Entrambi sono contrassegnati con * e non sono confrontabili con gli anni completi.</p>
    <p><b>Voci minori.</b> Le <b>componenti perequative</b> UR1/UR2 (delibera ARERA 386/2023) compaiono dal 2024 e UR3 (delibera 133/2025) dal 2025. Le <b>agevolazioni centri di raccolta</b> sono crediti per il conferimento diretto in isola ecologica (ingombranti, piccoli elettrodomestici) e compaiono come importi negativi. Alcune bollette contengono inoltre <b>ricalcoli tariffari</b> retroattivi su periodi già fatturati.</p>
    <p>Metodo: ogni bolletta è scomposta in quota fissa (fissa + normalizzata), quota variabile (base + aggiuntiva), perequative e agevolazioni, imposta provinciale (fuori campo IVA) e IVA 10%, includendo le rettifiche di conguaglio e ricalcolo. La somma delle cinque voci coincide al centesimo con il totale fatturato per tutte le __NBILLS__ bollette.</p>
  </div>
  <p class="footer">Generato a partire dalle bollette Hera del servizio rifiuti dell'abitazione, dal 2020 al 2026.</p>
</div>
<script>
const bills = [
__BILLS__
];
// Nessuna bolletta attraversa il 31 dicembre (i periodi sono gen-apr / mag-ago / set-dic),
// quindi i totali annui sono semplici somme: si ricalcolano da soli quando si aggiunge una bolletta.
const annual = {};
bills.forEach(b=>{
  const y=b.start.slice(0,4);
  annual[y]=annual[y]||{real:0,conf:0,min:0,tot:0,fissa:0,varia:0,altri:0,imposte:0,iva:0};
  const a=annual[y];
  a.real+=b.litri; a.conf+=b.conf; a.min+=b.litriMin; a.tot+=b.tot;
  a.fissa+=b.fissa; a.varia+=b.varia; a.altri+=b.altri; a.imposte+=b.imposte; a.iva+=b.iva;
});
Object.values(annual).forEach(a=>{["min","tot","fissa","varia","altri","imposte","iva"].forEach(k=>a[k]=+a[k].toFixed(2));});
const MESI =["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"];
function fmtIt(d){ const dt=new Date(d+"T00:00:00"); return dt.getDate()+" "+MESI[dt.getMonth()]+" "+String(dt.getFullYear()).slice(2); }
function periodLabel(b){ return fmtIt(b.start)+" – "+fmtIt(b.end); }
function eur(n){ return n.toLocaleString("it-IT",{minimumFractionDigits:2,maximumFractionDigits:2})+" €"; }
function litri(n){ return Math.round(n).toLocaleString("it-IT")+" L"; }
const totLitri=bills.reduce((s,b)=>s+b.litri,0), totConf=bills.reduce((s,b)=>s+b.conf,0);
const totTot=bills.reduce((s,b)=>s+b.tot,0);
const totFissa=bills.reduce((s,b)=>s+b.fissa,0), totVaria=bills.reduce((s,b)=>s+b.varia,0);
const kpis=[
 {label:"Rifiuto conferito",value:litri(totLitri),sub:totConf+" svuotamenti · __FIRST__ → __LAST__"},
 {label:"Spesa totale",value:eur(totTot),sub:bills.length+" bollette"},
 {label:"Quota fissa",value:(totFissa/totTot*100).toFixed(0)+"%",sub:eur(totFissa)+" — fissa + normalizzata"},
 {label:"Quota variabile",value:(totVaria/totTot*100).toFixed(0)+"%",sub:eur(totVaria)+" — base + aggiuntiva"},
 {label:"Costo per litro",value:(totTot/totLitri).toFixed(3)+" €/L",sub:"sui litri realmente conferiti"},
];
document.getElementById("kpis").innerHTML=kpis.map(k=>`<div class="kpi"><div class="label">${k.label}</div><div class="value">${k.value}</div><div class="sub">${k.sub}</div></div>`).join("");
const labels=bills.map(periodLabel);
new Chart(document.getElementById("litriChart"),{type:"bar",data:{labels,datasets:[
 {label:"Conferiti (reali)",data:bills.map(b=>b.litri),backgroundColor:"#2e9e5b",borderRadius:4},
 {label:"Fatturati (minimi)",data:bills.map(b=>b.litriMin),backgroundColor:"#c4c9d1",borderRadius:4}]},
 options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>ctx.dataset.label+": "+litri(ctx.parsed.y)+(ctx.datasetIndex===0?" ("+bills[ctx.dataIndex].conf+" svuotamenti)":"")}}},scales:{x:{ticks:{maxRotation:60,minRotation:60,autoSkip:false,font:{size:9}}},y:{title:{display:true,text:"litri"}}}}});
new Chart(document.getElementById("costChart"),{type:"bar",data:{labels,datasets:[
 {label:"Quota fissa",data:bills.map(b=>b.fissa),backgroundColor:"#4a6fa5"},
 {label:"Quota variabile",data:bills.map(b=>b.varia),backgroundColor:"#2e9e5b"},
 {label:"Perequative/agevolazioni",data:bills.map(b=>b.altri),backgroundColor:"#f2a007"},
 {label:"Imposta provinciale",data:bills.map(b=>b.imposte),backgroundColor:"#8e6bb0"},
 {label:"IVA 10%",data:bills.map(b=>b.iva),backgroundColor:"#9aa3af"}]},
 options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>ctx.dataset.label+": "+eur(ctx.parsed.y)}}},scales:{x:{stacked:true,ticks:{maxRotation:60,minRotation:60,autoSkip:false,font:{size:9}}},y:{stacked:true,title:{display:true,text:"€"}}}}});
const yearKeys=Object.keys(annual).sort();
function yearLabel(y){return (y==="2020"||y==="2026")?y+" *":y;}
new Chart(document.getElementById("yearLitriChart"),{type:"bar",data:{labels:yearKeys.map(yearLabel),datasets:[
 {label:"Conferiti (reali)",data:yearKeys.map(y=>annual[y].real),backgroundColor:"#2e9e5b",borderRadius:4},
 {label:"Minimi fatturati",data:yearKeys.map(y=>annual[y].min),backgroundColor:"#c4c9d1",borderRadius:4}]},
 options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:"bottom"},tooltip:{callbacks:{label:ctx=>ctx.dataset.label+": "+litri(ctx.parsed.y)+(ctx.datasetIndex===0?" ("+annual[yearKeys[ctx.dataIndex]].conf+" svuotamenti)":"")}}},scales:{y:{title:{display:true,text:"litri"}}}}});
new Chart(document.getElementById("yearCostChart"),{type:"bar",data:{labels:yearKeys.map(yearLabel),datasets:[
 {label:"Quota fissa",data:yearKeys.map(y=>annual[y].fissa),backgroundColor:"#4a6fa5"},
 {label:"Quota variabile",data:yearKeys.map(y=>annual[y].varia),backgroundColor:"#2e9e5b"},
 {label:"Perequative/agevolazioni",data:yearKeys.map(y=>annual[y].altri),backgroundColor:"#f2a007"},
 {label:"Imposta provinciale",data:yearKeys.map(y=>annual[y].imposte),backgroundColor:"#8e6bb0"},
 {label:"IVA 10%",data:yearKeys.map(y=>annual[y].iva),backgroundColor:"#9aa3af"}]},
 options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:"bottom"},tooltip:{callbacks:{label:ctx=>ctx.dataset.label+": "+eur(ctx.parsed.y)}}},scales:{x:{stacked:true},y:{stacked:true,title:{display:true,text:"€"}}}}});
const perLitro=yearKeys.map(y=>annual[y].real>0?+(annual[y].tot/annual[y].real).toFixed(3):null);
new Chart(document.getElementById("priceChart"),{type:"line",data:{labels:yearKeys.map(yearLabel),datasets:[
 {label:"€ per litro conferito",data:perLitro,borderColor:"#2e9e5b",backgroundColor:"#2e9e5b22",fill:true,tension:0.25,pointRadius:4,pointBackgroundColor:"#2e9e5b"}]},
 options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>ctx.parsed.y+" €/L — "+litri(annual[yearKeys[ctx.dataIndex]].real)+" conferiti, "+eur(annual[yearKeys[ctx.dataIndex]].tot)+" fatturati"}}},scales:{y:{title:{display:true,text:"€/litro"}}}}});
document.getElementById("priceLegend").innerHTML='<span>Spesa annua fatturata divisa per i litri realmente conferiti nell\\'anno. Il valore sale quando si conferisce poco: la quota fissa e i litri minimi si distribuiscono su meno rifiuto effettivo.</span>';
new gridjs.Grid({columns:["Dal","Al","Litri conferiti","Svuot.","Litri fatturati","Quota fissa (€)","Quota variabile (€)","Altri (€)","Imposte (€)","IVA (€)","Totale (€)","Note"],
 data:bills.map(b=>[fmtIt(b.start),fmtIt(b.end),b.litri,b.conf,b.litriMin.toFixed(2),b.fissa.toFixed(2),b.varia.toFixed(2),b.altri.toFixed(2),b.imposte.toFixed(2),b.iva.toFixed(2),b.tot.toFixed(2),b.note||""]),
 sort:true,search:true,pagination:{limit:12},className:{table:"gridjs-table"}}).render(document.getElementById("table"));
</script>
</body>
</html>
"""

html = (HTML
        .replace("__BILLS__", js_bills())
        .replace("__NBILLS__", str(len(bills)))
        .replace("__FIRST__", it(first["start"]))
        .replace("__LAST__", it(last["end"])))

out = HERE.parent / "index.html"
out.write_text(html)
print(f"wrote {out} ({len(html)} bytes, {len(bills)} bills)")
