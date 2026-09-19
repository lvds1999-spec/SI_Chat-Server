class ServicoChat:

    def __init__(self, repositorio_usuarios):

        self.repositorio_usuarios = (
            repositorio_usuarios
        )

    def registrar_usuario(
        self,
        usuario,
        senha
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
                senha
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