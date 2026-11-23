# Segurança e publicação

Este repositório permanece público por decisão do proprietário. Não publique aqui:
- tokens, credenciais, arquivos .env ou chaves privadas;
- dados financeiros internos, DRE, margens, alçadas ou custos da CTC;
- planilhas de habilitação, acervo técnico ou documentos de clientes;
- CNPJs/inscrições de estabelecimentos da empresa ou material operacional interno.

O serviço Render usa Bearer token gerado pelo Blueprint. Armazene-o somente em secret manager/variáveis de ambiente. Rotacione-o se houver exposição.

O endpoint /health é público para health checks. Os endpoints de consulta exigem autenticação. As consultas upstream são GET-only.
