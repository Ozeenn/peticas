// Catálogo e informações transcritos das imagens fornecidas pelo gatil.
const shopShirts=[
 {id:'marina',name:'Marina',style:'Círculo dourado',color:'Preta'},
 {id:'mafaldo',name:'Mafaldo',style:'Moldura vintage',color:'Preta'},
 {id:'miguel',name:'Miguel',style:'Listras verdes',color:'Clara'},
 {id:'tony',name:'Tony',style:'I love all cats and some people',color:'Clara'},
 {id:'matilda',name:'Matilda',style:'Quatro momentos',color:'Clara'},
 {id:'vitor',name:'Vitor',style:'Olhar curioso',color:'Preta'},
 {id:'iris',name:'Íris',style:'Retrato',color:'Preta'},
 {id:'um-gato-leva-o-outro',name:'Um gato leva o outro',style:'A turma do Peticas',color:'Clara'},
 {id:'james-surtei',name:'James',style:'Surtei e mordi todo mundo',color:'Preta'},
 {id:'james-paz',name:'James',style:'A paz não é uma opção',color:'Clara'},
 {id:'james-retrato',name:'James',style:'Retrato na moldura',color:'Preta'}
];
const shopSizes=[['P',49,67],['M',52,71],['G',55,73],['GG',57,75]];
let shopColor='Todas';
function shopShirtImage(shirt){return 'assets/loja/camisa-'+shirt.id+'.jpg'}
function shopShirtCard(shirt){return `<article class="panel shop-shirt" data-shirt="${shirt.id}"><button type="button" class="shop-photo" onclick="showShopPhoto('${shirt.id}')" aria-label="Ampliar camisa ${esc(shirt.name)}: ${esc(shirt.style)}"><img src="${shopShirtImage(shirt)}" alt="Camisa de base ${shirt.color.toLowerCase()} com estampa ${esc(shirt.style)} de ${esc(shirt.name)}" width="1254" height="1254" loading="lazy" decoding="async"><span>Ampliar foto ${icon('plus')}</span></button><div class="shop-shirt-content"><span class="eyebrow">Base ${shirt.color.toLowerCase()}</span><h3>${esc(shirt.name)}</h3><p>${esc(shirt.style)}</p><div class="shop-shirt-price"><strong>R$ 49,99</strong><small>P · M · G · GG</small></div></div></article>`}
function setShopColor(color){if(!['Todas','Preta','Clara'].includes(color))return;shopColor=color;render()}
function showShopPhoto(id){const shirt=shopShirts.find(s=>s.id===id);if(!shirt)return;showModal(esc(shirt.name)+' · '+esc(shirt.style),`<img class="shop-enlarged" src="${shopShirtImage(shirt)}" alt="Camisa ${esc(shirt.name)}: ${esc(shirt.style)}"><p class="sub">Base ${shirt.color.toLowerCase()} · R$ 49,99 · Modelagem adulto unissex.</p>`)}
function shopSizeTable(){return `<div class="table-wrap"><table><caption>Medidas da camiseta em centímetros</caption><thead><tr><th scope="col">Tamanho</th><th scope="col">Largura</th><th scope="col">Comprimento</th></tr></thead><tbody>${shopSizes.map(([size,width,length])=>`<tr><th scope="row">${size}</th><td>${width} cm</td><td>${length} cm</td></tr>`).join('')}</tbody></table></div>`}
function showShopSizeGuide(){showModal('Tabela de medidas',`${shopSizeTable()}<section class="community-section"><h3>Como medir</h3><p>Estenda uma camiseta em uma superfície plana. Meça a largura de uma lateral à outra, abaixo das mangas, e o comprimento do ombro até a barra. Compare com a tabela para escolher seu tamanho.</p><p>Modelo básico adulto unissex · 100% algodão · Fio 30.1 penteado. Estampa frontal DTF de aproximadamente 24 × 30 cm.</p></section>`)}
function shopPage(){
 const shirts=shopShirts.filter(s=>shopColor==='Todas'||s.color===shopColor);
 return `<section class="shop-intro"><div class="eyebrow">Coleção de camisas · Gatil Peticas</div><h1>Vista o carinho pelos nossos gatinhos.</h1><p>Onze estampas, muitas personalidades e o mesmo amor pelos gatos. Conheça cada modelo e encontre o seu favorito.</p><div class="shop-collection-info"><strong>R$ 49,99 <small>por camisa</small></strong><span>Adulto unissex · P ao GG</span><button type="button" class="btn secondary" onclick="showShopSizeGuide()">Ver tabela de medidas</button></div></section><section class="shop-catalog" aria-labelledby="shop-catalog-title"><div class="shop-catalog-head"><div><h2 id="shop-catalog-title">Camisas personalizadas</h2><p class="sub">${shirts.length} estampa(s) · Toque na foto para ver os detalhes.</p></div><div class="shop-color-filters" role="group" aria-label="Filtrar por cor da camisa">${[['Todas','Todas'],['Preta','Base preta'],['Clara','Base clara']].map(([value,label])=>`<button type="button" class="public-tab ${shopColor===value?'active':''}" aria-pressed="${shopColor===value}" onclick="setShopColor('${value}')">${label}</button>`).join('')}</div></div><div class="shop-shirt-grid">${shirts.map(shopShirtCard).join('')}</div></section><section class="panel community-section shop-size-guide"><h2>Encontre seu tamanho</h2><p>Modelo básico, adulto unissex, em 100% algodão e tecido fio 30.1 penteado. Estampa frontal em DTF de aproximadamente 24 × 30 cm.</p>${shopSizeTable()}<button type="button" class="text-btn" onclick="showShopSizeGuide()">Ver medidas e orientações →</button></section>`;
}
const shopPublicPage=publicPage;
publicPage=function(){return view==='shop'?shopPage():shopPublicPage()};
