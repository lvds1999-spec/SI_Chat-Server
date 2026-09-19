# SI_Chat-Server

Servidor TCP para aplicativo de chat.

## Como executar

1. Abra um terminal na pasta do projeto.
2. Execute:

   python server.py

3. O servidor ficará ouvindo na porta 8000.

O servidor aceita conexões TCP em paralelo, usando uma thread por cliente. Os eventos são enviados como JSON, delimitados por uma quebra de linha. O evento `registro` verifica se o usuário já existe, persiste nome e senha em `usuarios.json` e responde com `resposta_registro`.