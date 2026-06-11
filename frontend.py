import customtkinter as ctk
import cv2
import os
import threading
import time
from PIL import Image
from database import Database, PASTA_DADOS
from cadastrar import abrir_camera, treinar_modelo

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

PASTA_FOTOS = os.path.join(PASTA_DADOS, "fotos")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Poisson - Reconhecimento Facial")
        self.geometry("960x600")
        self.minsize(800, 500)

        self.camera = None
        self.executando = False
        self.modo = None
        self.ultimo_frame = None
        self.frame_lock = threading.Lock()
        self.db = Database(tipo="sqlite")
        self.db.conectar()
        self.db.fechar()

        self._criar_interface()
        self._atualizar_lista()

    def _criar_interface(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        frame_esquerdo = ctk.CTkFrame(self)
        frame_esquerdo.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame_esquerdo.grid_rowconfigure(0, weight=1)
        frame_esquerdo.grid_columnconfigure(0, weight=1)

        self.label_camera = ctk.CTkLabel(frame_esquerdo, text="Camera desligada", font=("Arial", 20))
        self.label_camera.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        frame_direito = ctk.CTkFrame(self)
        frame_direito.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        frame_direito.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_direito, text="Poisson - Reconhecimento Facial", font=("Arial", 18, "bold")).pack(pady=(15, 5))

        self.btn_cadastrar = ctk.CTkButton(frame_direito, text="Cadastrar Pessoa", command=self.abrir_cadastro)
        self.btn_cadastrar.pack(pady=5, padx=10, fill="x")

        self.btn_reconhecer = ctk.CTkButton(frame_direito, text="Iniciar Reconhecimento", command=self.iniciar_reconhecimento)
        self.btn_reconhecer.pack(pady=5, padx=10, fill="x")

        self.btn_parar = ctk.CTkButton(frame_direito, text="Parar", command=self.parar, state="disabled", fg_color="gray")
        self.btn_parar.pack(pady=5, padx=10, fill="x")

        self.btn_limpar = ctk.CTkButton(frame_direito, text="Limpar Dados (Apaga Tudo)", command=self.limpar_dados, fg_color="darkred", hover_color="red")
        self.btn_limpar.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(frame_direito, text="--- Cadastrados ---", font=("Arial", 12, "bold")).pack(pady=(15, 5))

        self.lista_frame = ctk.CTkScrollableFrame(frame_direito, height=150)
        self.lista_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.status_label = ctk.CTkLabel(frame_direito, text="", font=("Arial", 11), wraplength=250)
        self.status_label.pack(pady=5, padx=10)

    def _atualizar_lista(self):
        for w in self.lista_frame.winfo_children():
            w.destroy()
        self.db.conectar()
        pessoas = self.db.listar_pessoas()
        self.db.fechar()
        for id_str, dados in pessoas.items():
            frame = ctk.CTkFrame(self.lista_frame)
            frame.pack(pady=1, padx=5, fill="x")
            frame.grid_columnconfigure(0, weight=1)
            texto = f"{dados['nome']} ({dados['matricula']})"
            ctk.CTkLabel(frame, text=texto, anchor="w").grid(row=0, column=0, sticky="w")
            ctk.CTkButton(frame, text="X", width=30, fg_color="darkred", hover_color="red",
                          command=lambda pid=id_str, pnome=dados['nome'], pmat=dados['matricula']: self._remover_pessoa(pid, pnome, pmat)
                          ).grid(row=0, column=1, padx=(5, 0))

    def _set_status(self, texto, cor="white"):
        self.status_label.configure(text=texto, text_color=cor)

    def _remover_pessoa(self, id_pessoa, nome, matricula):
        confirmar = ctk.CTkToplevel(self)
        confirmar.title("Excluir")
        confirmar.geometry("350x150")
        confirmar.transient(self)
        confirmar.grab_set()
        confirmar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(confirmar, text=f"Tem certeza que deseja excluir\n{nome} ({matricula})?", font=("Arial", 14)).pack(pady=20)

        frame_btns = ctk.CTkFrame(confirmar)
        frame_btns.pack(pady=10)

        def confirmar_exclusao():
            confirmar.destroy()
            self.db.conectar()
            self.db.remover_pessoa(int(id_pessoa))
            self.db.fechar()
            for arq in os.listdir(PASTA_FOTOS):
                if arq.startswith(f"{matricula}_"):
                    os.remove(os.path.join(PASTA_FOTOS, arq))
            self._set_status(f"{nome} removido", "yellow")
            self._atualizar_lista()

        ctk.CTkButton(frame_btns, text="Sim", command=confirmar_exclusao, fg_color="darkred", hover_color="red").pack(side="left", padx=10)
        ctk.CTkButton(frame_btns, text="Cancelar", command=confirmar.destroy).pack(side="left", padx=10)

    def _captura_frames(self):
        while self.executando:
            ret, frame = self.camera.read()
            if ret and frame is not None:
                with self.frame_lock:
                    self.ultimo_frame = frame.copy()
            time.sleep(0.03)

    def _atualizar_ui(self):
        if not self.executando:
            return

        frame = None
        with self.frame_lock:
            if self.ultimo_frame is not None:
                frame = self.ultimo_frame.copy()

        if frame is not None:
            if self.modo == "reconhecimento":
                self._processar_reconhecimento(frame)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            max_w = 640
            if w > max_w:
                ratio = max_w / w
                w, h = max_w, int(h * ratio)
            pil = Image.fromarray(rgb).resize((w, h), Image.LANCZOS)
            img_ctk = ctk.CTkImage(pil, size=(w, h))
            self.label_camera.configure(image=img_ctk, text="")

        self.after(50, self._atualizar_ui)

    def _iniciar_camera_loop(self):
        self.executando = True
        threading.Thread(target=self._captura_frames, daemon=True).start()
        self.after(50, self._atualizar_ui)

    def abrir_cadastro(self):
        if self.executando:
            self._set_status("Pare a camera primeiro", "yellow")
            return

        dialogo = ctk.CTkInputDialog(text="Nome da pessoa:", title="Cadastro")
        nome = dialogo.get_input()
        if not nome:
            return

        dialogo2 = ctk.CTkInputDialog(text="Matricula:", title="Cadastro")
        matricula = dialogo2.get_input()
        if not matricula:
            return

        os.makedirs(PASTA_FOTOS, exist_ok=True)

        self.db.conectar()
        labels_existentes = self.db.listar_pessoas()

        for kid, v in labels_existentes.items():
            if v["nome"] == nome and v["matricula"] == matricula:
                self.db.fechar()
                dialog = ctk.CTkInputDialog(text=f"'{nome}' ja existe. Digite 's' para recadastrar:", title="Aviso")
                resp = dialog.get_input()
                if resp != "s":
                    self._set_status("Cadastro cancelado", "yellow")
                    return
                for arq in os.listdir(PASTA_FOTOS):
                    if arq.startswith(f"{v['matricula']}_"):
                        os.remove(os.path.join(PASTA_FOTOS, arq))
                self.db.conectar()
                self.db.remover_pessoa(int(kid))
                break

        for kid, v in labels_existentes.items():
            if v["matricula"] == matricula and v["nome"] != nome:
                self.db.fechar()
                self._set_status(f"Matricula {matricula} ja pertence a {v['nome']}", "red")
                return

        labels_existentes = self.db.listar_pessoas()
        self.db.fechar()

        janela = ctk.CTkToplevel(self)
        janela.title("Capturando Fotos")
        janela.geometry("700x550")
        janela.transient(self)
        janela.grab_set()

        btn_frame = ctk.CTkFrame(janela)
        btn_frame.pack(side="bottom", pady=10, fill="x")
        label_cam = ctk.CTkLabel(janela, text="Iniciando camera...")
        label_cam.pack(expand=True, fill="both", padx=10, pady=10)
        info_label = ctk.CTkLabel(janela, text="", font=("Arial", 14))
        info_label.pack(pady=5)

        cap = [None]
        fotos = 0
        max_fotos = 10
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        capturar_agora = [False]
        rodando = [True]
        fotos_salvas = []
        ultimo_frame_cad = [None]
        lock = threading.Lock()
        finalizar_agora = [False]
        camera_erro = [False]
        pessoa_existente = [None]

        modelo_path = os.path.join(PASTA_DADOS, "modelo.yml")
        if os.path.exists(modelo_path):
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(modelo_path)
            self.db.conectar()
            labels_rec = self.db.listar_pessoas()
            self.db.fechar()
        else:
            recognizer = None
            labels_rec = {}

        def capturar(event=None):
            capturar_agora[0] = True

        def fechar():
            finalizar_agora[0] = True
            rodando[0] = False
            if cap[0]:
                cap[0].release()
                cap[0] = None

        def loop_captura():
            nonlocal fotos
            while rodando[0] and fotos < max_fotos:
                if cap[0] is None:
                    time.sleep(0.05)
                    continue
                ret, frame = cap[0].read()
                if not ret:
                    continue
                h, w = frame.shape[:2]
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                tem_rosto = len(faces) > 0

                if tem_rosto:
                    (x, y, fw, fh) = faces[0]
                    cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)

                if tem_rosto and recognizer is not None and labels_rec:
                    (x, y, fw, fh) = faces[0]
                    face_roi = gray[y:y + fh, x:x + fw]
                    face_roi = clahe.apply(face_roi)
                    face_roi = cv2.resize(face_roi, (200, 200))
                    id_predito, confianca = recognizer.predict(face_roi)
                    if confianca < 50:
                        dados = labels_rec.get(str(id_predito), {"nome": "?", "matricula": "?"})
                        pnome = dados["nome"] if isinstance(dados, dict) else str(dados)
                        pmat = dados["matricula"] if isinstance(dados, dict) else ""
                        pessoa_existente[0] = (pnome, pmat)
                    else:
                        pessoa_existente[0] = None

                cv2.putText(frame, f"Fotos: {fotos}/10 (min 5)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 0) if tem_rosto else (0, 0, 255), 2)

                if capturar_agora[0] and tem_rosto and pessoa_existente[0] is None:
                    capturar_agora[0] = False
                    (x, y, fw, fh) = faces[0]
                    face = gray[y:y + fh, x:x + fw]
                    face = clahe.apply(face)
                    face_resized = cv2.resize(face, (200, 200))
                    nome_arquivo = f"{matricula}_{fotos}.jpg"
                    caminho = os.path.join(PASTA_FOTOS, nome_arquivo)
                    cv2.imwrite(caminho, face_resized)
                    fotos += 1
                    fotos_salvas.append(nome_arquivo)

                if pessoa_existente[0] is not None:
                    pnome, pmat = pessoa_existente[0]
                    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 6)
                    cv2.putText(frame, f"JA CADASTRADO: {pnome} ({pmat})", (w // 2 - 200, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)

                with lock:
                    ultimo_frame_cad[0] = frame.copy()

                time.sleep(0.03)

            if cap[0]:
                cap[0].release()
                cap[0] = None
            rodando[0] = False

        def atualizar_ui_cadastro():
            if camera_erro[0]:
                self._set_status("Erro ao acessar camera", "red")
                if janela.winfo_exists():
                    janela.destroy()
                return
            if not rodando[0]:
                _finalizar_cadastro()
                return
            with lock:
                if ultimo_frame_cad[0] is not None:
                    rgb = cv2.cvtColor(ultimo_frame_cad[0], cv2.COLOR_BGR2RGB)
                    hf, wf = rgb.shape[:2]
                    max_wf = 640
                    nw = max_wf if wf > max_wf else wf
                    nh = int(hf * nw / wf)
                    pil = Image.fromarray(rgb).resize((nw, nh), Image.LANCZOS)
                    img_ctk = ctk.CTkImage(pil, size=(nw, nh))
                    label_cam.configure(image=img_ctk, text="")
            if pessoa_existente[0] is not None:
                pnome, pmat = pessoa_existente[0]
                info_label.configure(text=f"JA CADASTRADO: {pnome} ({pmat})", text_color="red")
                btn_cap.configure(state="disabled")
            else:
                info_label.configure(text=f"Fotos: {fotos}/10 (min 5)", text_color="white")
                btn_cap.configure(state="normal")
            janela.after(50, atualizar_ui_cadastro)

        def _finalizar_cadastro():
            try:
                janela.grab_release()
            except Exception:
                pass
            if pessoa_existente[0] is not None:
                pnome, pmat = pessoa_existente[0]
                for f in fotos_salvas:
                    caminho = os.path.join(PASTA_FOTOS, f)
                    if os.path.exists(caminho):
                        os.remove(caminho)
                self._set_status(f"Rosto ja cadastrado como {pnome} ({pmat})", "red")
            elif fotos >= 5:
                self.db.conectar()
                self.db.adicionar_pessoa(nome, matricula)
                self.db.fechar()
                self._set_status(f"{nome} cadastrado com {fotos} fotos!", "green")
                treinar_modelo()
                self._atualizar_lista()
            else:
                for f in fotos_salvas:
                    caminho = os.path.join(PASTA_FOTOS, f)
                    if os.path.exists(caminho):
                        os.remove(caminho)
                if not finalizar_agora[0]:
                    self._set_status(f"Minimo 5 fotos (tirou {fotos})", "red")
            try:
                if janela.winfo_exists():
                    janela.destroy()
            except Exception:
                pass

        btn_cap = ctk.CTkButton(btn_frame, text="CAPTURAR (ESPACO)", command=lambda: capturar())
        btn_cap.pack(side="left", padx=5)
        janela.bind("<space>", capturar)
        janela.focus_set()
        janela.protocol("WM_DELETE_WINDOW", fechar)

        def abrir_camera_thread():
            c = abrir_camera(so_abrir=True)
            cap[0] = c
            if c is None:
                camera_erro[0] = True
                rodando[0] = False

        threading.Thread(target=loop_captura, daemon=True).start()
        threading.Thread(target=abrir_camera_thread, daemon=True).start()
        janela.after(50, atualizar_ui_cadastro)

    def iniciar_reconhecimento(self):
        modelo_path = os.path.join(PASTA_DADOS, "modelo.yml")
        if not os.path.exists(modelo_path):
            self._set_status("Cadastre uma pessoa primeiro", "yellow")
            return

        if self.executando:
            self._set_status("Ja esta em execucao", "yellow")
            return

        self.camera = abrir_camera(so_abrir=True)
        if self.camera is None:
            self._set_status("Erro ao acessar camera", "red")
            return

        self.modo = "reconhecimento"
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(modelo_path)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self.db.conectar()
        self.labels_rec = self.db.listar_pessoas()
        self.db.fechar()

        self.btn_cadastrar.configure(state="disabled")
        self.btn_reconhecer.configure(state="disabled")
        self.btn_parar.configure(state="normal", fg_color="red")
        self._set_status("Reconhecimento ativo", "green")

        self._iniciar_camera_loop()

    def _processar_reconhecimento(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            face = self.clahe.apply(face)
            face_resized = cv2.resize(face, (200, 200))
            id_predito, confianca = self.recognizer.predict(face_resized)
            if confianca < 50:
                dados = self.labels_rec.get(str(id_predito), {"nome": "?", "matricula": "?"})
                label = f"{dados['nome']} ({dados['matricula']})" if isinstance(dados, dict) else str(dados)
                cor = (0, 255, 0)
            else:
                label = "Desconhecido"
                cor = (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), cor, 2)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor, 2)

    def parar(self):
        self.executando = False
        if self.camera:
            self.camera.release()
            self.camera = None
        self.modo = None
        self.ultimo_frame = None
        self.label_camera.configure(image=None, text="Camera desligada")
        self.btn_cadastrar.configure(state="normal")
        self.btn_reconhecer.configure(state="normal")
        self.btn_parar.configure(state="disabled", fg_color="gray")
        self._set_status("Parado")

    def limpar_dados(self):
        if self.executando:
            self.parar()
        import shutil
        if os.path.exists(PASTA_DADOS):
            shutil.rmtree(PASTA_DADOS)
        os.makedirs(PASTA_FOTOS, exist_ok=True)
        self._set_status("Dados limpos", "yellow")
        self._atualizar_lista()

    def fechar(self):
        self.parar()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.fechar)
    app.mainloop()
