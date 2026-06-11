import sqlite3
import os

PASTA_DADOS = "dados"
ARQUIVO_DB = os.path.join(PASTA_DADOS, "pessoas.db")


class Database:
    def __init__(self, tipo="sqlite", **config):
        if tipo == "sqlite":
            self._impl = _SQLiteImpl(config.get("db_path", ARQUIVO_DB))
        elif tipo == "api":
            self._impl = _APIImpl(config.get("base_url", ""))
        else:
            raise ValueError(f"Tipo de database desconhecido: {tipo}")

    def conectar(self):
        self._impl.conectar()

    def fechar(self):
        self._impl.fechar()

    def listar_pessoas(self):
        return self._impl.listar_pessoas()

    def adicionar_pessoa(self, nome, matricula):
        return self._impl.adicionar_pessoa(nome, matricula)

    def remover_pessoa(self, id_pessoa):
        self._impl.remover_pessoa(id_pessoa)

    def limpar(self):
        self._impl.limpar()


class _SQLiteImpl:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def conectar(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS pessoas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                matricula TEXT NOT NULL UNIQUE
            )
        """)
        self.conn.commit()

    def fechar(self):
        if self.conn:
            self.conn.close()

    def listar_pessoas(self):
        cursor = self.conn.execute("SELECT id, nome, matricula FROM pessoas")
        return {str(row[0]): {"nome": row[1], "matricula": row[2]} for row in cursor.fetchall()}

    def adicionar_pessoa(self, nome, matricula):
        cursor = self.conn.execute(
            "INSERT INTO pessoas (nome, matricula) VALUES (?, ?)",
            (nome, matricula)
        )
        self.conn.commit()
        return cursor.lastrowid

    def remover_pessoa(self, id_pessoa):
        self.conn.execute("DELETE FROM pessoas WHERE id = ?", (id_pessoa,))
        self.conn.commit()

    def limpar(self):
        self.conn.execute("DROP TABLE IF EXISTS pessoas")
        self.conn.commit()
        self.conectar()


class _APIImpl:
    def __init__(self, base_url):
        self.base_url = base_url

    def conectar(self):
        pass

    def fechar(self):
        pass

    def listar_pessoas(self):
        import requests
        resp = requests.get(f"{self.base_url}/pessoas")
        resp.raise_for_status()
        return resp.json()

    def adicionar_pessoa(self, nome, matricula):
        import requests
        resp = requests.post(f"{self.base_url}/pessoas", json={"nome": nome, "matricula": matricula})
        resp.raise_for_status()
        return resp.json()["id"]

    def remover_pessoa(self, id_pessoa):
        import requests
        requests.delete(f"{self.base_url}/pessoas/{id_pessoa}")

    def limpar(self):
        import requests
        requests.delete(f"{self.base_url}/pessoas")
