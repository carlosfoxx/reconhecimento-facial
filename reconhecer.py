import cv2
import os
from pathlib import Path
from pygrabber.dshow_graph import FilterGraph
from database import Database

PASTA_DADOS = "dados"
ARQUIVO_MODELO = os.path.join(PASTA_DADOS, "modelo.yml")

db = Database(tipo="sqlite")

def abrir_camera():
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

def reconhecer():
    if not os.path.exists(ARQUIVO_MODELO):
        print("[!] Modelo nao encontrado. Execute o cadastro primeiro.")
        return

    db.conectar()
    labels = db.listar_pessoas()
    db.fechar()

    if not labels:
        print("[!] Nenhum cadastro encontrado.")
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(ARQUIVO_MODELO)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = abrir_camera()
    if cap is None:
        return

    print("[+] Reconhecimento em tempo real iniciado. ESC ou Q para sair.")

    janela_aberta = True
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    while janela_aberta:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            face = clahe.apply(face)
            face_resized = cv2.resize(face, (200, 200))

            id_predito, confianca = recognizer.predict(face_resized)

            if confianca < 50:
                dados = labels.get(str(id_predito), {"nome": "Desconhecido", "matricula": ""})
                if isinstance(dados, dict):
                    label = f"{dados['nome']} ({dados['matricula']})"
                else:
                    label = str(dados)
                cor = (0, 255, 0)
                cv2.putText(frame, label, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, cor, 2)
            else:
                cor = (0, 0, 255)
                cv2.putText(frame, "Desconhecido", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, cor, 2)

            cv2.rectangle(frame, (x, y), (x + w, y + h), cor, 2)

        cv2.imshow("Reconhecimento Facial", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break

        if cv2.getWindowProperty("Reconhecimento Facial", cv2.WND_PROP_VISIBLE) < 1:
            janela_aberta = False

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    reconhecer()
