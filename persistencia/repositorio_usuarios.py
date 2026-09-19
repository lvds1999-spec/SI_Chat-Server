import json
import os


ARQUIVO_USUARIOS = "usuarios.json"


class RepositorioUsuarios:

    def __init__(self):
        self.arquivo = ARQUIVO_USUARIOS

        self._criar_arquivo_se_nao_existir()

    def _criar_arquivo_se_nao_existir(self):

        if not os.path.exists(self.arquivo):

            with open(
                self.arquivo,
                "w",
                encoding="utf-8"
            ) as arquivo:

                json.dump(
                    {},
                    arquivo,
                    ensure_ascii=False,
                    indent=4
                )

    def _carregar(self):

        with open(
            self.arquivo,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return json.load(arquivo)

    def _salvar(self, usuarios):

        with open(
            self.arquivo,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                usuarios,
                arquivo,
                ensure_ascii=False,
                indent=4
            )

    def usuario_existe(self, usuario):

        usuarios = self._carregar()

        return usuario in usuarios

    def cadastrar(self, usuario, senha):

        usuarios = self._carregar()

        if usuario in usuarios:
            return False

        usuarios[usuario] = {
            "senha": senha
        }

        self._salvar(usuarios)

        return True