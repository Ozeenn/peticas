CREATE TABLE localizacoes_aplicacoes (
 cod_registro text PRIMARY KEY REFERENCES registros_clinicos(cod_identificador),
 num_latitude double precision NOT NULL CHECK(num_latitude BETWEEN -90 AND 90),
 num_longitude double precision NOT NULL CHECK(num_longitude BETWEEN -180 AND 180),
 num_precisao_metros double precision NOT NULL CHECK(num_precisao_metros BETWEEN 0 AND 100000),
 dat_coleta timestamptz NOT NULL, dat_cadastro timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE mensagens_candidaturas (
 cod_identificador text PRIMARY KEY, cod_candidatura text NOT NULL REFERENCES candidaturas_adocao(cod_identificador),
 cod_usuario text REFERENCES usuarios(cod_identificador), txt_mensagem text NOT NULL,
 dat_cadastro timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_mensagens_candidatura_cadastro ON mensagens_candidaturas(cod_candidatura,dat_cadastro);
INSERT INTO mensagens_candidaturas(cod_identificador,cod_candidatura,txt_mensagem,dat_cadastro)
 SELECT 'inicial:'||cod_identificador,cod_identificador,txt_orientacao,dat_cadastro
 FROM candidaturas_adocao WHERE txt_orientacao<>'';
ALTER TABLE vacinas ADD COLUMN num_versao integer NOT NULL DEFAULT 1;
ALTER TABLE vacinas ADD COLUMN cod_usuario_aplicacao text REFERENCES usuarios(cod_identificador);
ALTER TABLE vacinas ADD COLUMN dat_registro_aplicacao timestamptz;
