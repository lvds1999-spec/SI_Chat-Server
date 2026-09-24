# SI_Chat-Server

Servidor TCP para aplicativo de chat.

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

Os dados também são mantidos no banco SQLite `chat.db`, criado automaticamente na raiz do projeto. A tabela `usuarios` armazena usuários e senhas, e a tabela `contatos` mantém a lista permanente de cada usuário. A tabela `mensagens` possui `id`, `sender`, `recipient`, `timestamp`, `texto` e `status` (`pendente`, `entregue` ou `lido`). Mensagens pendentes são entregues no próximo login. O arquivo `chat.db` pode ser aberto no VS Code com uma extensão SQLite.