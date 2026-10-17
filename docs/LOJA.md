# Catálogo público do gatil

A aba `#shop` apresenta 11 estampas e permite filtrar por base preta ou clara e ampliar as imagens. As fotos das camisas e as informações de medidas foram fornecidas pelo usuário em 16/10/2026. As 11 fotos originais foram copiadas, sem alteração de conteúdo, para `public/assets/loja/`. A tabela foi transcrita em HTML, sem exibir a arte que contém um prazo de encomendas.

As informações compartilhadas da coleção são transcritas da tabela enviada: R$ 49,99, modelo básico adulto unissex, 100% algodão, tecido fio 30.1 penteado e estampa frontal DTF de aproximadamente 24 × 30 cm. Não há prazo de encomendas apresentado no catálogo.

| Tamanho | Largura | Comprimento |
| --- | --- | --- |
| P | 49 cm | 67 cm |
| M | 52 cm | 71 cm |
| G | 55 cm | 73 cm |
| GG | 57 cm | 75 cm |

Modelos: Marina, Mafaldo, Miguel, Tony, Matilda, Vitor, Íris, Um gato leva o outro e três estampas James (Surtei e mordi todo mundo, A paz não é uma opção e Retrato na moldura). As descrições dos estilos servem para diferenciar as imagens e não afirmam estoque.

O catálogo permite escolher o tamanho (P, M, G ou GG) e montar um carrinho com quantidades, remoção de itens e total dos produtos. O carrinho é lembrado em `localStorage` na chave `peticas:cart:v1`; guarda apenas identificador da estampa, tamanho e quantidade. Itens com estampa e tamanho iguais são agrupados, enquanto tamanhos diferentes permanecem separados. A quantidade por combinação vai de 1 a 99. O preço é calculado a partir de 4.999 centavos por unidade e nunca é lido do armazenamento. Conteúdo inválido é descartado. Se o navegador bloquear o armazenamento, a seleção continua na página aberta com um aviso de que será perdida ao recarregar. O carrinho não reserva estoque nem habilita compra, pagamento ou criação de pedido. A loja apresenta somente camisas. Para atualizar o catálogo, edite `public/shop.js`, substitua os arquivos de imagem necessários e atualize a versão do script em `public/index.html`.
