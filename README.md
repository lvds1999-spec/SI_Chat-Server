# SI_Chat-Server

Servidor TCP para aplicativo de chat.

## Arquitetura

`server.py` é o único ponto de entrada e coordena as conexões TCP. O código da aplicação fica organizado por responsabilidade:

- `src/dominio/`: regras de registro e autenticação.
- `src/seguranca/`: handshake de canal, cifragem, derivação de chaves e assinaturas.
- `src/infraestrutura/rede/`: protocolo JSON transportado no canal seguro.
- `src/infraestrutura/persistencia/`: banco SQLite e repositórios de usuários, contatos e mensagens.

Execute o servidor com `python server.py` na raiz do projeto.

## Como executar

1. Abra um terminal na pasta do projeto.
2. Execute:

   python server.py

3. O servidor ficará ouvindo na porta 8000.

O servidor aceita conexões TCP em paralelo, usando uma thread por cliente. Os eventos são enviados como JSON, delimitados por uma quebra de linha. O evento `registro` verifica se o usuário já existe, persiste nome e senha no banco SQLite e responde com `resposta_registro`.

O evento `login` verifica nome e senha. Após um login bem-sucedido, o cliente recebe `lista_usuarios`, contendo todos os usuários cadastrados e o campo booleano `online` de cada um. Alterações posteriores de conexão são comunicadas por eventos `presenca`.

Os eventos `digitando_inicio` e `digitando_fim` são efêmeros: o servidor apenas os encaminha se o destinatário estiver conectado e não os armazena para entrega posterior. O cliente deve remover o indicador de digitação após 2 segundos sem nova atualização.

Linhas JSON inválidas ou eventos que não sejam objetos recebem uma resposta `erro` e não derrubam o handler da conexão. Se o mesmo usuário autenticar em outro socket, a sessão anterior é fechada e o novo socket passa a ser a sessão ativa.

Após aceitar uma conexão TCP, o servidor executa um handshake DHE efêmero. Os eventos seguintes passam por `enviar_evento` e `ler_eventos` em envelopes autenticados com HMAC-SHA256 e cifrados com AES-256-CTR, usando chaves derivadas por HKDF-SHA256. A sessão renova as chaves após 100 mensagens ou 60 minutos de atividade, no próximo ciclo de transporte.

Usuários usam `senha_hash` Argon2id e `salt` aleatório. Um login deve informar `algoritmo_assinatura` (`ed25519` ou `rsa-pss`) e `chave_publica`. Para uma chave já cadastrada, o servidor envia `desafio_login` com um nonce e aceita somente `login_assinatura` válida. Para uma chave nova, a senha autoriza a troca; as mensagens offline pendentes são descartadas e os contatos online recebem `aviso_novo_dispositivo`.

O evento `solicitar_chave_publica` retorna a chave pública cadastrada do destinatário. Depois que o cliente conclui o acordo E2E, envia `handshake_concluido`; o servidor registra o par remetente/destinatário. Mensagens são encaminhadas como pacotes opacos, sem interpretação do conteúdo cifrado. Uma mensagem para destinatário offline só entra na fila se esse handshake existir; caso contrário, o remetente recebe `erro` com código `handshake_ausente`.

Os dados são mantidos no banco SQLite `chat.db`, gerado automaticamente na raiz na primeira execução. A tabela `usuarios` armazena usuários e hashes de senha; a tabela SQL `contatos` é a única fonte de verdade para as listas de contatos. A tabela `mensagens` possui `id`, `sender`, `recipient`, `timestamp`, `texto`, `payload` e `status` (`pendente`, `entregue` ou `lido`). Mensagens pendentes são entregues no próximo login. O arquivo `chat.db` pode ser aberto no VS Code com uma extensão SQLite e não é versionado.

`usuarios.json` e `mensagens_offline.json` são somente fontes de importação de dados legados quando as tabelas correspondentes estão vazias; novas alterações são persistidas no SQLite.