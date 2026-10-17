# Persistência e evolução do sistema de vendas

O catálogo `#shop` e o carrinho `#cart` são públicos. A API usa o PostgreSQL para produtos, variantes e carrinhos. A criação de um carrinho não coleta nome, CPF, endereço ou cartão e não cria uma venda.

## Estrutura

| Tabela | Finalidade |
| --- | --- |
| `produtos_loja` | Nome, estilo, cor, imagem e ativação da estampa |
| `variantes_produtos_loja` | Tamanho, preço em centavos, estoque opcional e quantidade reservada |
| `carrinhos_loja` | Hash da referência privada, estado, versão e expiração do acesso |
| `itens_carrinhos_loja` | Variante e quantidade, sem preços controlados pelo cliente |
| `clientes_loja` | Identificação e contato do comprador, para o futuro checkout |
| `pedidos_loja` | Estado, entrega, totais em centavos, moeda e chave de idempotência |
| `itens_pedidos_loja` | Fotografia histórica de nome, estilo, tamanho e preço da venda |
| `enderecos_pedidos_loja` | Endereço de entrega específico do pedido |
| `pagamentos_loja` | Tentativas de pagamento e referências externas do provedor |
| `eventos_pagamentos_loja` | Identificador único, hash e processamento de notificações, sem dados de cartão |
| `historico_pedidos_loja` | Mudanças de estado, motivo e operador |
| `movimentos_estoque_loja` | Ajustes, reservas, baixas, liberações e devoluções |

O catálogo inicial contém as 11 estampas fornecidas pelo usuário e 44 variantes P/M/G/GG. Não há estoque fictício: saldo nulo significa que o controle de saldo ainda não foi definido. A carga inicial não sobrescreve produtos existentes. Valores monetários são inteiros; o total de cada item do pedido é calculado no banco. Chaves estrangeiras, unicidade e verificações impedem quantidades negativas, variantes duplicadas, totais inconsistentes e repetição de notificações externas.

## API implementada

- `GET /api/shop/products`: catálogo e preços públicos, com checkout desabilitado.
- `POST /api/shop/cart`: cria um carrinho e retorna a referência privada uma única vez; pode receber itens locais para importação.
- `POST /api/shop/cart/read`: recupera o carrinho pela referência enviada no corpo JSON.
- `PUT /api/shop/cart`: substitui a seleção com verificação de versão. Estampas/tamanhos inativos e quantidades indisponíveis são recusados.
- `GET /api/shop/orders`: lista até 100 pedidos, somente para a responsável autenticada.
- `POST /api/shop/orders/draft`: converte um carrinho em rascunho, somente para a responsável, exigindo `idempotencyKey`. Congela os itens e registra histórico; não cobra nem reserva estoque.

Os dados do carrinho são acessíveis apenas pela referência aleatória de 256 bits, cujo hash fica no banco. O acesso expira após 30 dias sem atualização. Escritas exigem origem válida, JSON, limites de requisições e validação dos itens. A alteração do carrinho usa bloqueio de linha e versão; uma atualização concorrente desatualizada recebe 409. Uma nova tentativa explícita de salvar usa a versão atual. O navegador mantém os dados locais se uma gravação falhar e exibe o erro.

## Atualização de um banco existente

Faça backup, construa/teste a nova imagem e execute **explicitamente**, com `DATABASE_URL` configurado para o alvo correto:

```text
python -m backend.shop_migrate
```

O comando aplica `backend/shop_schema.sql` em uma transação e sob bloqueio, somente quando nenhuma tabela da loja existe. Se todas existem, não recria nem recarrega o catálogo. Uma instalação parcial é recusada para revisão. Nenhuma tabela da gestão do gatil é apagada ou alterada. Só inicie a nova API após concluir a migração; a inicialização valida os dois esquemas e não migra automaticamente um banco preenchido. Em banco vazio, ambos os esquemas e o catálogo inicial são criados juntos.

As mudanças são aditivas. Voltar à imagem anterior mantém as novas tabelas, sem perda de dados; não remova tabelas para executar rollback de código. Expiração de acesso não elimina registros físicos: definir descarte e retenção dos carrinhos e backups continua sendo uma decisão operacional.

## Etapas ainda necessárias para vender

A estrutura de pagamentos e pedidos está preparada, mas não existe provedor integrado, confirmação de pagamento, reserva de estoque no checkout, cálculo de frete ou painel de operação de vendas. As tabelas dessas etapas permanecem sem pagamentos reais. Antes de abrir vendas, implemente o checkout, a identificação do comprador e a modalidade de entrega, transições transacionais de estoque/pedido, validação das notificações do provedor, reconciliação, estornos, mensagens e administração dos pedidos. Atualize informações comerciais e políticas aplicáveis e teste o fluxo completo no ambiente de testes do provedor.
