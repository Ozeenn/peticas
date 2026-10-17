# Privacidade, consentimento e atendimento de pedidos

Modelo de organização preparado para revisão pela responsável do Gatil Peticas em 13 de outubro de 2026. Os textos e controles implementados ajudam a registrar informações e escolhas; não representam uma certificação de conformidade. A responsável deve adequar a identificação do controlador, as bases legais, os contratos com prestadores e os prazos de guarda ao funcionamento real do gatil, com revisão jurídica quando necessária.

## 1. Ciência e consentimento são registros diferentes

O site apresenta um aviso geral com acesso aos Termos de Uso e à Política de Privacidade, inclusive fora do fluxo de adoção. O botão de aceite lembra a versão e a data neste navegador, em `localStorage`, sem identificar a pessoa nem criar um registro no banco. Se o armazenamento estiver indisponível, a preferência dura apenas na sessão aberta. A navegação e a leitura dos documentos continuam disponíveis; o rodapé permite revisar o aceite. Uma nova versão dos documentos faz o aviso reaparecer.

A aba pública `#shop` apresenta o catálogo de estampas das camisas e a tabela de medidas fornecidos pelo gatil. O carrinho lembra estampas, tamanhos e quantidades localmente e no servidor, sem identificação do visitante. A referência privada fica em `peticas:cart-access:v1`; no banco é guardado apenas seu hash. O acesso expira após 30 dias sem atualização. Isso não representa eliminação física automática dos registros ou backups. Não há checkout ou captura de dados de pagamento. Os rascunhos de pedido são restritos à administração. As imagens são arquivos públicos do site; não contêm dados de candidatos.

Na candidatura, o aceite dos termos e a ciência da política permanecem explícitos. O registro versionado no banco preserva ambos os textos no mesmo snapshot. Os aceites anteriores continuam associados aos documentos que foram apresentados na ocasião; o aceite geral do navegador não marca automaticamente as escolhas do formulário nem autoriza vídeo. O site utiliza cookie de sessão para o acesso da equipe; o aviso não inclui categorias de rastreamento ou publicidade.

A candidatura é solicitada pela própria pessoa. O aviso informa o uso de dados necessários para analisar, formalizar e acompanhar a adoção. A declaração “li e estou ciente” registra ciência, não uma autorização irrestrita.

O vídeo da residência tem escolha separada e opcional. A finalidade proposta é avaliar a proteção do lar, com acesso da responsável. A recusa não impede a candidatura: combine visita ou outra alternativa adequada. A autorização pode ser revogada. O sistema bloqueia novos uploads após a escolha negativa; o tratamento de um vídeo já armazenado exige análise manual do pedido e da conservação cabível.

Não foram incluídos consentimentos para marketing, publicidade ou divulgação da imagem do adotante. Esses usos exigiriam uma finalidade e uma escolha próprias. Não reutilize a autorização do vídeo para redes sociais.

## 2. Revisão antes de uso

Em **Doações e avisos → Identificação e privacidade**, complete:

- Nome legal de quem decide o tratamento de dados e sua identificação documental para os termos internos.
- Endereço e canal público de contato para assuntos de dados pessoais.
- Política de guarda: finalidades, critérios, prazos e hipóteses de conservação por tipo de registro.

Não publique desnecessariamente CPF de pessoa natural. A identificação documental das configurações é usada no termo e não é retornada pelo aviso público. Verifique se o endereço informado é apropriado como contato público.

Revise `backend/privacy.py` e `backend/templates/termo_adocao.json` com a responsável. O termo é um modelo para assinatura manuscrita. A geração do PDF não registra uma assinatura, não comprova entrega e não conclui a adoção. Após assinatura, mantenha uma via com cada parte e anexe a digitalização à candidatura.

## 3. Inventário de dados e decisões a documentar

| Conjunto | Finalidade no sistema | Quem acessa | Decisão da responsável |
| --- | --- | --- | --- |
| Nome, CPF, idade, contato e endereço do candidato | Avaliação solicitada, visita, termo e acompanhamento | Responsável; candidato por link privado limitado | Necessidade de cada campo e adequação do tratamento à adoção solicitada |
| Respostas sobre lar e rotina | Avaliação de segurança e compatibilidade | Responsável | Reduzir perguntas excessivas e evitar dados de terceiros |
| Vídeo da residência | Avaliação do lar | Responsável e acesso autorizado pelo token | Consentimento específico, alternativa sem vídeo e prazo curto compatível com a finalidade |
| Termo assinado | Formalização e comprovação da adoção | Responsável e candidato no vínculo autorizado | Forma de guarda, finalidade e conservação cabível |
| Dados de voluntários | Organização da equipe e acesso | Responsável | Necessidade dos campos e base legal adequada à relação |
| Localização nas medicações | Registro pontual da aplicação | Responsável | Necessidade, proporcionalidade, transparência e base legal documentadas |
| Logs, sessões e limites | Funcionamento e proteção do serviço | Administração técnica | Conteúdo mínimo, proteção e descarte |
| Avisos WhatsApp | Comunicação do processo | Destinatários configurados e prestador | Contratos, telefones, conteúdo e eventual transferência internacional |
| PDFs completos do gato | Manutenção e consulta interna | Responsável | Não entregar a terceiros dados de outras candidaturas ou de voluntários |

A nova entrevista deixa de pedir alergias de outras pessoas. Dados antigos não são apagados por essa alteração. Avalie a necessidade de mantê-los. Campos livres ainda podem receber informações inadequadas: oriente candidatos e equipe a evitar nomes, documentos, condições de saúde e imagens de terceiros, especialmente crianças.

A permissão de localização do navegador não comprova, por si só, consentimento válido. Como a localização é obrigatória no registro de medicamento, a responsável deve revisar a necessidade, a base legal e as condições aplicáveis à equipe. As coordenadas também são declaradas pelo navegador; não comprovam presença física.

## 4. O que o sistema registra

`registros_privacidade` preserva o texto apresentado, versão, ciência, escolha sobre vídeo, candidatura e data. Os registros são acrescentados sem substituir aceites anteriores. Candidaturas antigas não recebem aceite retroativo. Uma versão desatualizada é recusada na nova ciência para evitar registrar um texto diferente do que foi apresentado.

`solicitacoes_privacidade` registra protocolo, nome, e-mail, tipo de pedido, descrição, situação e anotações da equipe. A pessoa recebe um protocolo no site. A responsável acompanha a fila e registra andamento. O sistema não envia resposta por e-mail, não decide o pedido, não verifica identidade nem exclui dados automaticamente.

## 5. Procedimento manual para pedidos

1. Confira a fila regularmente e identifique o tipo: acesso, correção, eliminação, revogação ou outro direito. Pedidos recebidos fora do site também devem ser registrados no controle interno da equipe.
2. Confirme o recebimento pelo contato informado. Guarde o protocolo e a data de entrada. Não solicite documentos adicionais sem necessidade.
3. Verifique a identidade de forma proporcional, usando um canal já associado ao cadastro quando possível. **CPF isolado não comprova identidade**, e um pedido público pode ter sido enviado por outra pessoa.
4. Localize todas as candidaturas, ficha, arquivos e demais registros relacionados. Não entregue informações de familiares, outros candidatos ou voluntários junto com os dados do solicitante.
5. Avalie a finalidade, a base legal e eventual obrigação de conservação. Registre a justificativa de atendimento total, parcial ou de impossibilidade fundamentada. Não prometa apagar tudo automaticamente quando o tratamento não depender exclusivamente de consentimento.
6. Execute as providências aprovadas com a equipe técnica e registre o que foi corrigido, disponibilizado, restringido ou eliminado. Considere cópias exportadas, papéis, prestadores e backups. Preserve a integridade referencial do banco.
7. Responda pelo canal verificado, registre data e resultado e marque “Respondido” somente depois da resposta efetiva. Se necessário, mantenha um registro mínimo de cumprimento do pedido, protegido e pelo período justificado.

Para confirmação e acesso, a LGPD prevê declaração simplificada imediata ou declaração completa em até 15 dias. Não aplique esse prazo indistintamente a todos os direitos: confira a obrigação e a regulamentação aplicáveis ao pedido concreto. O atendimento aos direitos não deve ser cobrado. [Orientação da ANPD](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados/direito-dos-titulares).

Modelo de anotação interna:

```text
Protocolo:
Recebido em:
Direito solicitado:
Canal de verificação e resultado (sem cópias desnecessárias de documentos):
Registros localizados:
Providência e fundamento:
Responsável pela execução:
Resposta enviada em e canal:
Tratamento de cópias, prestadores e backups:
Pendências:
```

## 6. Guarda, exclusão e incidentes

Defina prazos concretos por finalidade antes de usar o modelo como política definitiva. Não foi inventado um prazo único de conservação. Vídeos, entrevistas recusadas, termos concluídos, aceites e logs podem demandar critérios distintos. Expirar uma sessão não elimina uma entrevista ou um anexo.

Não execute `DELETE` genérico por nome ou CPF. Uma mesma pessoa pode ter várias candidaturas. A tabela de respostas usa CPF textual; a consulta usa também um hash com segredo guardado em `configuracoes`. O hash com vínculo recuperável não deve ser tratado como anonimização. Exclusão e anonimização exigem planejamento das FKs, históricos, arquivos e finalidade de cada registro.

Proteja os backups e documente como impedir a reintrodução de dados já eliminados ao restaurar uma cópia antiga. Restrinja PDFs exportados e termos em papel e realize descarte adequado quando não houver mais necessidade.

Se houver perda de arquivo, acesso indevido, link privado compartilhado ou outro incidente: contenha o acesso, preserve evidências mínimas, avise a responsável, identifique os dados e titulares afetados e avalie as obrigações de comunicação conforme as regras aplicáveis. Registre as providências. Não divulgue entrevistas ou arquivos como exemplo do incidente.

## 7. Referências

- [LGPD, texto atualizado na Câmara dos Deputados](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html): princípios, hipóteses de tratamento, consentimento, transparência, direitos e conservação.
- [Direitos dos titulares - ANPD](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados/direito-dos-titulares): orientação sobre exercício de direitos e pedidos ao controlador.

As decisões sobre finalidades, bases legais, retenção e atendimento pertencem à responsável pelo tratamento. Atualize este procedimento quando o funcionamento, os prestadores ou as normas aplicáveis mudarem.

A política pública apresenta o endereço de visita já informado no site como contato padrão e o formulário de privacidade como canal de direitos. Instruções para configurar e revisar informações ficam na área administrativa. O texto público descreve o uso do serviço, sem avisos de configuração pendente.
