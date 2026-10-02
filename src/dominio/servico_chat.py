class ServicoChat:

    def __init__(self, repositorio_usuarios):

        self.repositorio_usuarios = (
            repositorio_usuarios
        )

    def registrar_usuario(
        self,
        usuario,
        senha,
        chave_publica=None,
    ):

        # Verifica se o nome já está sendo utilizado.
        if self.repositorio_usuarios.usuario_existe(
            usuario
        ):

            return {
                "evento": "resposta_registro",
                "sucesso": False,
                "mensagem": "Nome de usuário já está em uso."
            }

        # Tenta cadastrar o novo usuário.
        cadastrado = (
            self.repositorio_usuarios.cadastrar(
                usuario,
                senha,
                chave_publica,
            )
        )

        if cadastrado:

            return {
                "evento": "resposta_registro",
                "sucesso": True,
                "mensagem": "Usuário registrado com sucesso."
            }

        return {
            "evento": "resposta_registro",
            "sucesso": False,
            "mensagem": "Não foi possível registrar o usuário."
        }

    def autenticar_usuario(self, usuario, senha):
        autenticado = self.repositorio_usuarios.autenticar(
            usuario,
            senha
        )

        if autenticado:
            return {
                "evento": "resposta_login",
                "sucesso": True,
                "mensagem": "Login realizado com sucesso."
            }

        return {
            "evento": "resposta_login",
            "sucesso": False,
            "mensagem": "Usuário ou senha inválidos."
        }