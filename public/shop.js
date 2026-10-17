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
const shopCartKey='peticas:cart:v1',shopUnitPrice=4999;
const shopSelectedSizes={};
let shopCartMemoryOnly=false;
let shopCart=loadShopCart();
function normalizeShopCart(items){
 if(!Array.isArray(items))return [];
 const result=[];
 for(const item of items.slice(0,200)){
  if(!item||!shopShirts.some(s=>s.id===item.id)||!shopSizes.some(s=>s[0]===item.size)||!Number.isInteger(item.quantity)||item.quantity<1||item.quantity>99)continue;
  const existing=result.find(s=>s.id===item.id&&s.size===item.size);
  if(existing)existing.quantity=Math.min(99,existing.quantity+item.quantity);
  else result.push({id:item.id,size:item.size,quantity:item.quantity});
 }
 return result;
}
function loadShopCart(){let raw;try{raw=localStorage.getItem(shopCartKey)}catch{shopCartMemoryOnly=true;return []}try{const saved=JSON.parse(raw);return saved?.version===1?normalizeShopCart(saved.items):[]}catch{return []}}
function saveShopCart(){try{localStorage.setItem(shopCartKey,JSON.stringify({version:1,items:shopCart}));shopCartMemoryOnly=false}catch{shopCartMemoryOnly=true}refreshShopCart()}
function shopMoney(cents){return (cents/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}
function shopCartCount(){return shopCart.reduce((sum,item)=>sum+item.quantity,0)}
function shopCartTotal(){return shopCartCount()*shopUnitPrice}
function addShopCartItem(id,size,quantity=1){
 if(!shopShirts.some(s=>s.id===id))throw new Error('Escolha uma camisa do catálogo.');
 if(!shopSizes.some(s=>s[0]===size))throw new Error('Escolha o tamanho da camisa.');
 if(!Number.isInteger(quantity)||quantity<1||quantity>99)throw new Error('Informe uma quantidade entre 1 e 99.');
 const item=shopCart.find(s=>s.id===id&&s.size===size);
 if((item?.quantity||0)+quantity>99)throw new Error('O limite é de 99 unidades por estampa e tamanho.');
 if(item)item.quantity+=quantity;else shopCart.push({id,size,quantity});
 saveShopCart();
}
function addShopToCart(event,id){event.preventDefault();try{const size=new FormData(event.target).get('size');addShopCartItem(id,size);shopSelectedSizes[id]=size;toast('Camisa tamanho '+size+' adicionada ao carrinho.')}catch(error){formError(event,error.message)}}
function setShopCartQuantity(index,value){
 const quantity=Number(value);
 if(!Number.isInteger(index)||!shopCart[index])throw new Error('Item não encontrado no carrinho.');
 if(!Number.isInteger(quantity)||quantity<1||quantity>99)throw new Error('Informe uma quantidade entre 1 e 99.');
 shopCart[index].quantity=quantity;saveShopCart();
}
function editShopCartQuantity(index,value){try{setShopCartQuantity(index,value)}catch(error){toast(error.message);refreshShopCart()}}
function removeShopCartItem(index){if(!Number.isInteger(index)||!shopCart[index])return;shopCart.splice(index,1);saveShopCart()}
function clearShopCart(){shopCart=[];saveShopCart()}
function shopCartContents(){return `<div class="shop-cart-heading"><h2 tabindex="-1">Seu carrinho <span data-cart-count>(${shopCartCount()})</span></h2>${shopCart.length?'<button type="button" class="text-btn" onclick="clearShopCart()">Esvaziar carrinho</button>':''}</div>${shopCart.length?`<ul class="shop-cart-items">${shopCart.map((item,index)=>{const shirt=shopShirts.find(s=>s.id===item.id);const label=esc(shirt.name+' · '+shirt.style+' · tamanho '+item.size);return `<li class="shop-cart-item"><img src="${shopShirtImage(shirt)}" alt="Camisa ${esc(shirt.name)}: ${esc(shirt.style)}" width="90" height="90"><div class="shop-cart-description"><h3>${esc(shirt.name)}</h3><p>${esc(shirt.style)} · Base ${shirt.color.toLowerCase()}</p><strong>Tamanho ${item.size}</strong><small>${shopMoney(shopUnitPrice)} por unidade</small></div><div class="shop-cart-controls"><label>Quantidade<input type="number" min="1" max="99" step="1" value="${item.quantity}" aria-label="Quantidade de ${label}" onchange="editShopCartQuantity(${index},this.value)"></label><strong>${shopMoney(item.quantity*shopUnitPrice)}</strong><button type="button" class="text-btn" aria-label="Remover ${label}" onclick="removeShopCartItem(${index})">Remover</button></div></li>`}).join('')}</ul><div class="shop-cart-total"><strong>Total dos produtos</strong><strong>${shopMoney(shopCartTotal())}</strong></div><p class="sub">Seu carrinho reúne as escolhas. A finalização da compra e o pagamento ainda não estão disponíveis.</p>`:'<p class="sub">Seu carrinho está vazio. Escolha uma estampa e um tamanho para começar.</p>'}${shopCartMemoryOnly?'<p class="notice" role="status">O armazenamento do navegador está indisponível. As alterações no carrinho serão perdidas ao recarregar esta página.</p>':''}`}
function refreshShopCart(){const cart=$('#shop-cart');if(cart)cart.innerHTML=shopCartContents();for(const counter of document.querySelectorAll('[data-cart-count]'))counter.textContent='('+shopCartCount()+')'}
function openShopCart(){const scroll=()=>{const cart=$('#shop-cart');cart?.scrollIntoView({behavior:'smooth',block:'start'});cart?.querySelector('h2')?.focus({preventScroll:true})};if(view==='shop')scroll();else Promise.resolve(go('shop')).then(scroll)}
window.addEventListener('storage',event=>{if(event.key===shopCartKey||event.key===null){shopCart=loadShopCart();refreshShopCart()}});
let shopColor='Todas';
function shopShirtImage(shirt){return 'assets/loja/camisa-'+shirt.id+'.jpg'}
function shopShirtCard(shirt){return `<article class="panel shop-shirt" data-shirt="${shirt.id}"><button type="button" class="shop-photo" onclick="showShopPhoto('${shirt.id}')" aria-label="Ampliar camisa ${esc(shirt.name)}: ${esc(shirt.style)}"><img src="${shopShirtImage(shirt)}" alt="Camisa de base ${shirt.color.toLowerCase()} com estampa ${esc(shirt.style)} de ${esc(shirt.name)}" width="1254" height="1254" loading="lazy" decoding="async"><span>Ampliar foto ${icon('plus')}</span></button><div class="shop-shirt-content"><span class="eyebrow">Base ${shirt.color.toLowerCase()}</span><h3>${esc(shirt.name)}</h3><p>${esc(shirt.style)}</p><div class="shop-shirt-price"><strong>R$ 49,99</strong><small>P · M · G · GG</small></div><form class="shop-add-form" onsubmit="addShopToCart(event,'${shirt.id}')"><label for="shop-size-${shirt.id}">Tamanho<select id="shop-size-${shirt.id}" name="size" required onchange="shopSelectedSizes['${shirt.id}']=this.value"><option value="">Selecione</option>${shopSizes.map(([size])=>`<option value="${size}" ${shopSelectedSizes[shirt.id]===size?'selected':''}>${size}</option>`).join('')}</select></label><button type="submit" class="btn pink">Adicionar ao carrinho ${icon('plus')}</button></form></div></article>`}
function setShopColor(color){if(!['Todas','Preta','Clara'].includes(color))return;shopColor=color;render()}
function showShopPhoto(id){const shirt=shopShirts.find(s=>s.id===id);if(!shirt)return;showModal(esc(shirt.name)+' · '+esc(shirt.style),`<img class="shop-enlarged" src="${shopShirtImage(shirt)}" alt="Camisa ${esc(shirt.name)}: ${esc(shirt.style)}"><p class="sub">Base ${shirt.color.toLowerCase()} · R$ 49,99 · Modelagem adulto unissex.</p>`)}
function shopSizeTable(){return `<div class="table-wrap"><table><caption>Medidas da camiseta em centímetros</caption><thead><tr><th scope="col">Tamanho</th><th scope="col">Largura</th><th scope="col">Comprimento</th></tr></thead><tbody>${shopSizes.map(([size,width,length])=>`<tr><th scope="row">${size}</th><td>${width} cm</td><td>${length} cm</td></tr>`).join('')}</tbody></table></div>`}
function showShopSizeGuide(){showModal('Tabela de medidas',`${shopSizeTable()}<section class="community-section"><h3>Como medir</h3><p>Estenda uma camiseta em uma superfície plana. Meça a largura de uma lateral à outra, abaixo das mangas, e o comprimento do ombro até a barra. Compare com a tabela para escolher seu tamanho.</p><p>Modelo básico adulto unissex · 100% algodão · Fio 30.1 penteado. Estampa frontal DTF de aproximadamente 24 × 30 cm.</p></section>`)}
function shopPage(){
 const shirts=shopShirts.filter(s=>shopColor==='Todas'||s.color===shopColor);
 return `<section class="shop-intro"><div class="eyebrow">Coleção de camisas · Gatil Peticas</div><h1>Vista o carinho pelos nossos gatinhos.</h1><p>Muitas personalidades e o mesmo amor pelos gatos. Conheça cada modelo e encontre o seu favorito.</p><div class="shop-collection-info"><strong>R$ 49,99 <small>por camisa</small></strong><span>Adulto unissex · P ao GG</span><button type="button" class="btn secondary" onclick="showShopSizeGuide()">Ver tabela de medidas</button><button type="button" class="btn" onclick="openShopCart()">Ver carrinho <span data-cart-count>(${shopCartCount()})</span></button></div></section><section id="shop-cart" class="panel community-section shop-cart" aria-label="Carrinho de compras">${shopCartContents()}</section><section class="shop-catalog" aria-labelledby="shop-catalog-title"><div class="shop-catalog-head"><div><h2 id="shop-catalog-title">Camisas personalizadas</h2><p class="sub">Toque na foto para ver os detalhes e escolha seu tamanho.</p></div><div class="shop-color-filters" role="group" aria-label="Filtrar por cor da camisa">${[['Todas','Todas'],['Preta','Base preta'],['Clara','Base clara']].map(([value,label])=>`<button type="button" class="public-tab ${shopColor===value?'active':''}" aria-pressed="${shopColor===value}" onclick="setShopColor('${value}')">${label}</button>`).join('')}</div></div><div class="shop-shirt-grid">${shirts.map(shopShirtCard).join('')}</div></section><section class="panel community-section shop-size-guide"><h2>Encontre seu tamanho</h2><p>Modelo básico, adulto unissex, em 100% algodão e tecido fio 30.1 penteado. Estampa frontal em DTF de aproximadamente 24 × 30 cm.</p>${shopSizeTable()}<button type="button" class="text-btn" onclick="showShopSizeGuide()">Ver medidas e orientações →</button></section>`;
}
const shopPublicPage=publicPage;
publicPage=function(){return view==='shop'?shopPage():shopPublicPage()};

const shopHeaderShell=publicShell;
publicShell=function(){return shopHeaderShell().replace('<div class="public-actions">','<div class="public-actions"><button type="button" class="btn secondary small" onclick="openShopCart()">Carrinho <span data-cart-count>('+shopCartCount()+')</span></button>')};
