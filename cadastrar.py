import cv2
import os
import numpy as np
import json
from pathlib import Path
from pygrabber.dshow_graph import FilterGraph
from database import Database

PASTA_DADOS = "dados"
PASTA_FOTOS = os.path.join(PASTA_DADOS, "fotos")

os.makedirs(PASTA_FOTOS, exist_ok=True)

db = Database(tipo="sqlite")

def abrir_camera(so_abrir=False):
    """Abre a camera. Se so_abrir=True, nao testa leitura (retorna mais rapido)."""
    virtuais = ["virtual camera", "animaze", "obs virtual", "vcam", "manycam", "splitcam"]

    try:
        graph = FilterGraph()
        dispositivos = graph.get_input_devices()
    except Exception:
        dispositivos = [f"CAM {i}" for i in range(10)]

    def _tentar(i, backend=None):
        args = (i, backend) if backend is not None else (i,)
        cap = cv2.VideoCapture(*args)
        if not cap.isOpened():
            return None
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if so_abrir:
            return cap
        ret, frame = cap.read()
        if ret and frame is not None:
            return cap
        cap.release()
        return None

    for i, nome in enumerate(dispositivos):
        if any(v in nome.lower() for v in virtuais):
            continue
        cap = _tentar(i, cv2.CAP_DSHOW) or _tentar(i)
        if cap:
            print(f"[+] {i} - {nome}")
            return cap

    for i in range(10):
        cap = _tentar(i, cv2.CAP_DSHOW) or _tentar(i)
        if cap:
            print(f"[+] Camera {i}")
            return cap

    print("[!] Nenhuma camera encontrada.")
    return None

def cadastrar_pessoa(nome, matricula):
    db.conectar()
    labels = db.listar_pessoas()

    for k, v in list(labels.items()):
        if v["nome"] == nome and v["matricula"] == matricula:
            if any(f.startswith(f"{v['matricula']}_") for f in os.listdir(PASTA_FOTOS)):
                resp = input(f"[?] '{nome}' ja cadastrado. Recadastrar? (s/N): ").strip().lower()
                if resp != "s":
                    db.fechar()
                    return
                for arq in os.listdir(PASTA_FOTOS):
                    if arq.startswith(f"{v['matricula']}_"):
                        os.remove(os.path.join(PASTA_FOTOS, arq))
                db.remover_pessoa(int(k))
                break
            db.remover_pessoa(int(k))
            break

    novo_id = db.adicionar_pessoa(nome, matricula)
    db.fechar()

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = abrir_camera()
    if cap is None:
        return

    print(f"[+] Cadastrando '{nome}' (matricula: {matricula}).")
    print("[+] Clique no botao CAPTURAR ou pressione ESPACO. ESC ou Q para sair.")

    fotos_tiradas = 0
    janela_aberta = True
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    botao_clicado = False

    def mouse_callback(event, x, y, flags, param):
        nonlocal botao_clicado
        if event == cv2.EVENT_LBUTTONDOWN:
            h, w = frame.shape[:2]
            bx1, by1, bx2, by2 = 10, h - 50, 150, h - 10
            if bx1 <= x <= bx2 and by1 <= y <= by2:
                botao_clicado = True

    cv2.namedWindow("Cadastro - Reconhecimento Facial")
    cv2.setMouseCallback("Cadastro - Reconhecimento Facial", mouse_callback)

    while fotos_tiradas < 10 and janela_aberta:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        status = "Nenhum rosto detectado"
        cor_status = (0, 0, 255)
        pode_capturar = False

        if len(faces) > 0:
            (x, y, fw, fh) = faces[0]
            cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)
            status = f"Rosto OK! ({fotos_tiradas}/10)"
            cor_status = (0, 255, 0)
            pode_capturar = True

        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor_status, 2)

        cv2.rectangle(frame, (10, h - 50), (150, h - 10), (0, 200, 0), -1)
        cv2.putText(frame, "CAPTURAR", (25, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Cadastro - Reconhecimento Facial", frame)

        key = cv2.waitKey(1) & 0xFF

        if key in (27, ord('q'), ord('Q')):
            break
        elif (key == 32 or botao_clicado) and pode_capturar:
            botao_clicado = False
            (x, y, fw, fh) = faces[0]
            face = gray[y:y + fh, x:x + fw]
            face = clahe.apply(face)
            face_resized = cv2.resize(face, (200, 200))

            nome_arquivo = f"{matricula}_{fotos_tiradas}.jpg"
            caminho = os.path.join(PASTA_FOTOS, nome_arquivo)
            cv2.imwrite(caminho, face_resized)
            fotos_tiradas += 1
            print(f"  -> Foto {fotos_tiradas}/10 salva.")

        if cv2.getWindowProperty("Cadastro - Reconhecimento Facial", cv2.WND_PROP_VISIBLE) < 1:
            janela_aberta = False

    cap.release()
    cv2.destroyAllWindows()

    if fotos_tiradas >= 5:
        print(f"[+] '{nome}' (matricula: {matricula}) cadastrado com sucesso! (ID: {novo_id}, fotos: {fotos_tiradas})")
    else:
        print(f"[!] Cadastro cancelado. Minimo: 5 fotos (tirou {fotos_tiradas}).")
        db.conectar()
        db.remover_pessoa(novo_id)
        db.fechar()
        for arq in os.listdir(PASTA_FOTOS):
            if arq.startswith(f"{matricula}_"):
                os.remove(os.path.join(PASTA_FOTOS, arq))

def treinar_modelo():
    recognizer = cv2.face.LBPHFaceRecognizer_create()

    db.conectar()
    labels = db.listar_pessoas()
    db.fechar()

    if not labels:
        print("[!] Nenhum cadastro encontrado.")
        return None

    if not os.path.exists(PASTA_FOTOS):
        print("[!] Pasta de fotos nao encontrada.")
        return None

    faces = []
    labels_list = []

    for id_str, dados in labels.items():
        prefixo = f"{dados['matricula']}_" if isinstance(dados, dict) else f"{id_str}_"
        for arq in os.listdir(PASTA_FOTOS):
            if arq.startswith(prefixo):
                caminho = os.path.join(PASTA_FOTOS, arq)
                img = cv2.imread(caminho, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    faces.append(img)
                    labels_list.append(int(id_str))

    if len(faces) == 0:
        print("[!] Nenhuma foto encontrada para treinar.")
        return None

    recognizer.train(faces, np.array(labels_list))
    recognizer.save(os.path.join(PASTA_DADOS, "modelo.yml"))
    print(f"[+] Modelo treinado com {len(faces)} fotos de {len(labels)} pessoa(s).")
    return recognizer


if __name__ == "__main__":
    nome = input("Nome da pessoa para cadastrar: ").strip()
    matricula = input("Matricula: ").strip()
    if nome and matricula:
        cadastrar_pessoa(nome, matricula)
        treinar_modelo()
