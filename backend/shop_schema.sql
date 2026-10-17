-- Complemento do esquema: aplicar explicitamente em instalações existentes.
CREATE TABLE produtos_loja (
 cod_identificador text PRIMARY KEY, txt_nome text NOT NULL, txt_estilo text NOT NULL,
 txt_cor text NOT NULL, txt_imagem text NOT NULL, flg_ativo boolean NOT NULL DEFAULT true,
 dat_cadastro timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE variantes_produtos_loja (
 cod_identificador text PRIMARY KEY, cod_produto text NOT NULL REFERENCES produtos_loja(cod_identificador),
 txt_tamanho text NOT NULL CHECK(txt_tamanho IN ('P','M','G','GG')),
 num_preco_centavos integer NOT NULL CHECK(num_preco_centavos BETWEEN 1 AND 100000000),
 num_estoque integer CHECK(num_estoque>=0), num_reservado integer NOT NULL DEFAULT 0 CHECK(num_reservado>=0),
 flg_ativo boolean NOT NULL DEFAULT true, UNIQUE(cod_produto,txt_tamanho),
 CHECK(num_estoque IS NULL OR num_reservado<=num_estoque)
);
CREATE TABLE carrinhos_loja (
 cod_identificador text PRIMARY KEY, txt_token_hash text NOT NULL UNIQUE,
 txt_estado text NOT NULL DEFAULT 'active' CHECK(txt_estado IN ('active','converted','expired')),
 num_versao integer NOT NULL DEFAULT 0 CHECK(num_versao>=0),
 dat_expiracao timestamptz NOT NULL DEFAULT now()+interval '30 days',
 dat_cadastro timestamptz NOT NULL DEFAULT now(), dat_atualizacao timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_carrinhos_loja_expiracao ON carrinhos_loja(dat_expiracao);
CREATE TABLE itens_carrinhos_loja (
 cod_carrinho text NOT NULL REFERENCES carrinhos_loja(cod_identificador) ON DELETE CASCADE,
 cod_variante text NOT NULL REFERENCES variantes_produtos_loja(cod_identificador),
 num_quantidade integer NOT NULL CHECK(num_quantidade BETWEEN 1 AND 99), PRIMARY KEY(cod_carrinho,cod_variante)
);
CREATE TABLE clientes_loja (
 cod_identificador text PRIMARY KEY, txt_nome text NOT NULL, txt_email text NOT NULL,
 txt_telefone text NOT NULL DEFAULT '', dat_cadastro timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_clientes_loja_email ON clientes_loja(txt_email);
CREATE TABLE pedidos_loja (
 cod_identificador text PRIMARY KEY, cod_carrinho text NOT NULL UNIQUE REFERENCES carrinhos_loja(cod_identificador),
 cod_cliente text REFERENCES clientes_loja(cod_identificador), txt_chave_idempotencia text NOT NULL UNIQUE,
 txt_estado text NOT NULL DEFAULT 'draft' CHECK(txt_estado IN ('draft','awaiting_payment','paid','preparing','shipped','delivered','cancelled','refunded')),
 txt_nome_cliente text NOT NULL DEFAULT '', txt_email_cliente text NOT NULL DEFAULT '', txt_telefone_cliente text NOT NULL DEFAULT '',
 txt_entrega text NOT NULL DEFAULT 'undecided' CHECK(txt_entrega IN ('undecided','pickup','shipping')),
 txt_moeda text NOT NULL DEFAULT 'BRL' CHECK(txt_moeda='BRL'),
 num_subtotal_centavos bigint NOT NULL CHECK(num_subtotal_centavos>=0),
 num_frete_centavos bigint NOT NULL DEFAULT 0 CHECK(num_frete_centavos>=0),
 num_desconto_centavos bigint NOT NULL DEFAULT 0 CHECK(num_desconto_centavos>=0),
 num_total_centavos bigint NOT NULL CHECK(num_total_centavos>=0),
 dat_cadastro timestamptz NOT NULL DEFAULT now(), dat_atualizacao timestamptz NOT NULL DEFAULT now(),
 CHECK(num_total_centavos=num_subtotal_centavos+num_frete_centavos-num_desconto_centavos)
);
CREATE INDEX idx_pedidos_loja_estado ON pedidos_loja(txt_estado,dat_cadastro);
CREATE TABLE itens_pedidos_loja (
 cod_identificador text PRIMARY KEY, cod_pedido text NOT NULL REFERENCES pedidos_loja(cod_identificador),
 cod_variante text NOT NULL REFERENCES variantes_produtos_loja(cod_identificador),
 txt_nome_produto text NOT NULL, txt_estilo text NOT NULL, txt_cor text NOT NULL, txt_tamanho text NOT NULL,
 num_preco_centavos integer NOT NULL CHECK(num_preco_centavos BETWEEN 1 AND 100000000),
 num_quantidade integer NOT NULL CHECK(num_quantidade BETWEEN 1 AND 99),
 num_total_centavos bigint GENERATED ALWAYS AS (num_quantidade::bigint*num_preco_centavos) STORED,
 UNIQUE(cod_pedido,cod_variante)
);
CREATE TABLE enderecos_pedidos_loja (
 cod_pedido text PRIMARY KEY REFERENCES pedidos_loja(cod_identificador), txt_destinatario text NOT NULL,
 txt_cep text NOT NULL, txt_estado text NOT NULL, txt_cidade text NOT NULL, txt_bairro text NOT NULL,
 txt_logradouro text NOT NULL, txt_numero text NOT NULL, txt_complemento text NOT NULL DEFAULT '',
 txt_pais text NOT NULL DEFAULT 'BR' CHECK(txt_pais='BR')
);
CREATE TABLE pagamentos_loja (
 cod_identificador text PRIMARY KEY, cod_pedido text NOT NULL REFERENCES pedidos_loja(cod_identificador),
 txt_provedor text NOT NULL, txt_referencia_externa text, txt_chave_idempotencia text NOT NULL UNIQUE,
 txt_estado text NOT NULL DEFAULT 'pending' CHECK(txt_estado IN ('pending','approved','rejected','cancelled','refunded','partially_refunded')),
 num_valor_centavos bigint NOT NULL CHECK(num_valor_centavos>0),
 txt_moeda text NOT NULL DEFAULT 'BRL' CHECK(txt_moeda='BRL'),
 dat_cadastro timestamptz NOT NULL DEFAULT now(), dat_atualizacao timestamptz NOT NULL DEFAULT now(),
 UNIQUE(txt_provedor,txt_referencia_externa)
);
CREATE TABLE eventos_pagamentos_loja (
 cod_identificador text PRIMARY KEY, cod_pagamento text REFERENCES pagamentos_loja(cod_identificador),
 txt_provedor text NOT NULL, txt_evento_externo text NOT NULL, txt_tipo text NOT NULL,
 txt_conteudo_hash text NOT NULL, dat_recebimento timestamptz NOT NULL DEFAULT now(),
 dat_processamento timestamptz, txt_erro text, UNIQUE(txt_provedor,txt_evento_externo)
);
CREATE TABLE historico_pedidos_loja (
 cod_identificador text PRIMARY KEY, cod_pedido text NOT NULL REFERENCES pedidos_loja(cod_identificador),
 txt_estado_anterior text, txt_estado_novo text NOT NULL, txt_motivo text NOT NULL,
 cod_usuario text REFERENCES usuarios(cod_identificador), dat_cadastro timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_historico_pedidos_loja ON historico_pedidos_loja(cod_pedido,dat_cadastro);
CREATE TABLE movimentos_estoque_loja (
 cod_identificador text PRIMARY KEY, cod_variante text NOT NULL REFERENCES variantes_produtos_loja(cod_identificador),
 cod_pedido text REFERENCES pedidos_loja(cod_identificador),
 txt_tipo text NOT NULL CHECK(txt_tipo IN ('adjustment','reservation','release','sale','return')),
 num_saldo_delta integer NOT NULL DEFAULT 0, num_reserva_delta integer NOT NULL DEFAULT 0,
 txt_motivo text NOT NULL, cod_usuario text REFERENCES usuarios(cod_identificador),
 dat_cadastro timestamptz NOT NULL DEFAULT now(), CHECK(num_saldo_delta<>0 OR num_reserva_delta<>0)
);
CREATE INDEX idx_movimentos_estoque_loja ON movimentos_estoque_loja(cod_variante,dat_cadastro);
