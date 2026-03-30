const DATA = {
    rbk: {
        hoy: [
            { tit:"FILL RATE GLOBAL", val:"94.2%", numVal:94.2, sub:"▲ 2.1% vs periodo anterior", subC:"c-green", valC:"c-blue", trend:[88,90,91,89,92,93,94.2], lineC:"#38bdf8", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val:"4,200", numVal:4200, sub:"▲ 12% sobre la meta", subC:"c-green", valC:"c-green", trend:[3000,3200,3100,3500,3800,4000,4200], lineC:"#34d399", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val:"3", numVal:3, sub:"⚠ Requieren atención", subC:"c-red", valC:"c-red", trend:[5,4,6,3,5,4,3], lineC:"#f87171", type:"alert",
              alerts:[{client:"Walmart",qty:2,status:"Retraso 2h"},{client:"Liverpool",qty:1,status:"Sin asignar"}] },
        ],
        semana: [
            { tit:"FILL RATE GLOBAL", val:"91.8%", numVal:91.8, sub:"▲ 1.5% vs periodo anterior", subC:"c-green", valC:"c-blue", trend:[85,87,89,90,91,90,91.8], lineC:"#38bdf8", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val:"28,500", numVal:28500, sub:"▲ 8% sobre la meta", subC:"c-green", valC:"c-green", trend:[22000,23500,25000,26000,27000,28000,28500], lineC:"#34d399", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val:"15", numVal:15, sub:"⚠ Requieren atención inmediata", subC:"c-red", valC:"c-red", trend:[12,10,15,8,14,11,15], lineC:"#f87171", type:"alert",
              alerts:[{client:"Walmart",qty:6,status:"Retraso >4h"},{client:"Liverpool",qty:4,status:"Retraso 2h"},{client:"Coppel",qty:3,status:"Sin asignar"},{client:"Palacio",qty:2,status:"En reparto"}] },
        ],
        mes: [
            { tit:"FILL RATE GLOBAL", val:"89.5%", numVal:89.5, sub:"▼ 0.8% vs mes anterior", subC:"c-red", valC:"c-blue", trend:[80,82,85,87,86,88,89.5], lineC:"#38bdf8", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val:"112,000", numVal:112000, sub:"▲ 5% sobre la meta", subC:"c-green", valC:"c-green", trend:[90000,95000,100000,105000,108000,110000,112000], lineC:"#34d399", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val:"42", numVal:42, sub:"⚠ Requieren atención inmediata", subC:"c-red", valC:"c-red", trend:[30,35,32,38,40,39,42], lineC:"#f87171", type:"alert",
              alerts:[{client:"Walmart",qty:15,status:"Múltiples retrasos"},{client:"Liverpool",qty:12,status:"Retraso >6h"},{client:"Coppel",qty:8,status:"Sin asignar"},{client:"Palacio",qty:4,status:"En reparto"},{client:"Suburbia",qty:3,status:"Sin ruta"}] },
        ],
    },
    on: {
        hoy: [
            { tit:"FILL RATE GLOBAL", val:"82.1%", numVal:82.1, sub:"▼ 5.2% vs periodo anterior", subC:"c-red", valC:"c-pink", trend:[78,80,79,81,80,82,82.1], lineC:"#f472b6", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val:"3,100", numVal:3100, sub:"▼ 8% bajo la meta", subC:"c-red", valC:"c-amber", trend:[3500,3400,3200,3000,2900,3050,3100], lineC:"#fbbf24", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val:"7", numVal:7, sub:"⚠ Requieren atención", subC:"c-red", valC:"c-red", trend:[5,6,8,7,9,6,7], lineC:"#f87171", type:"alert",
              alerts:[{client:"Innovasport",qty:4,status:"Retraso 3h"},{client:"Martí",qty:3,status:"Sin ruta"}] },
        ],
        semana: [
            { tit:"FILL RATE GLOBAL", val:"79.4%", numVal:79.4, sub:"▼ 3.1% vs periodo anterior", subC:"c-red", valC:"c-pink", trend:[72,74,76,75,78,79,79.4], lineC:"#f472b6", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val:"19,800", numVal:19800, sub:"▼ 12% bajo la meta", subC:"c-red", valC:"c-amber", trend:[22000,21000,20500,19800,19500,19700,19800], lineC:"#fbbf24", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val:"23", numVal:23, sub:"⚠ Requieren atención inmediata", subC:"c-red", valC:"c-red", trend:[18,20,15,22,25,21,23], lineC:"#f87171", type:"alert",
              alerts:[{client:"Innovasport",qty:9,status:"Retraso >4h"},{client:"Martí",qty:7,status:"Sin asignar"},{client:"Liverpool",qty:4,status:"Retraso 2h"},{client:"Dportenis",qty:3,status:"En reparto"}] },
        ],
        mes: [
            { tit:"FILL RATE GLOBAL", val:"76.2%", numVal:76.2, sub:"▼ 6.5% vs mes anterior", subC:"c-red", valC:"c-pink", trend:[68,70,72,73,75,74,76.2], lineC:"#f472b6", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val:"84,000", numVal:84000, sub:"▼ 15% bajo la meta", subC:"c-red", valC:"c-amber", trend:[95000,92000,88000,85000,84500,84200,84000], lineC:"#fbbf24", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val:"58", numVal:58, sub:"⚠ Requieren atención inmediata", subC:"c-red", valC:"c-red", trend:[40,45,48,50,54,55,58], lineC:"#f87171", type:"alert",
              alerts:[{client:"Innovasport",qty:20,status:"Múltiples retrasos"},{client:"Martí",qty:15,status:"Sin asignar"},{client:"Liverpool",qty:12,status:"Retraso >6h"},{client:"Dportenis",qty:6,status:"Sin ruta"},{client:"Coppel",qty:5,status:"En reparto"}] },
        ],
    }
};

let state = { rbk: { view:0, filter:'semana' }, on: { view:0, filter:'semana' } };

function makeSVG(data, color) {
    const W=480, H=65;
    const mx=Math.max(...data)*1.05, mn=Math.min(...data)*0.95, rng=mx-mn||1;
    const pts=data.map((v,i)=>[(i/(data.length-1))*W, H-((v-mn)/rng)*H]);
    const pathD=pts.map((p,i)=>(i===0?'M':'L')+p[0]+' '+p[1]).join(' ');
    const fillD=pathD+' L '+W+' '+H+' L 0 '+H+' Z';
    const uid='s'+Math.random().toString(36).substr(2,5);
    const [r,g,b]=[parseInt(color.substr(1,2),16),parseInt(color.substr(3,2),16),parseInt(color.substr(5,2),16)];
    const circles=pts.map(p=>'<circle cx="'+p[0]+'" cy="'+p[1]+'" r="3.5" fill="'+color+'" stroke="#161c28" stroke-width="2"/>').join('');
    return '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" style="width:100%;height:75px;overflow:visible;">'+
        '<defs><linearGradient id="'+uid+'" x1="0" x2="0" y1="0" y2="1">'+
        '<stop offset="0%" stop-color="'+color+'" stop-opacity="0.18"/>'+
        '<stop offset="100%" stop-color="'+color+'" stop-opacity="0.0"/></linearGradient>'+
        '<filter id="gl'+uid+'"><feGaussianBlur stdDeviation="2"/></filter></defs>'+
        '<path d="'+fillD+'" fill="url(#'+uid+')"/>'+
        '<path d="'+pathD+'" fill="none" stroke="'+color+'" stroke-width="2" opacity="0.25" filter="url(#gl'+uid+')"/>'+
        '<path d="'+pathD+'" fill="none" stroke="'+color+'" stroke-width="2"/>'+
        circles+'</svg>';
}

console.log(makeSVG([88,90,91,89,92,93,94.2], "#38bdf8"));
