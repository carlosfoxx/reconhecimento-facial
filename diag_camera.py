import cv2
import time
from pygrabber.dshow_graph import FilterGraph

virtuais = ["virtual camera", "animaze", "obs virtual", "vcam", "manycam", "splitcam"]

def tentar(i, backend=None, nome=""):
    args = (i, backend) if backend is not None else (i,)
    cap = cv2.VideoCapture(*args)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        for t in range(15):
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"  OK [{nome}] indice {i} backend {backend}: frame {t+1}")
                cap.release()
                return True
            time.sleep(0.2)
        print(f"  FALHOU [{nome}] indice {i} backend {backend}: abriu mas sem frame")
        cap.release()
        time.sleep(0.5)
    else:
        print(f"  FALHOU [{nome}] indice {i} backend {backend}: nao abriu")
    return False

# 1 - Non-virtual cameras with DSHOW
print("1. NON-VIRTUAL com DSHOW:")
try:
    for i, nome in enumerate(FilterGraph().get_input_devices()):
        if not any(v in nome.lower() for v in virtuais):
            tentar(i, cv2.CAP_DSHOW, nome)
except Exception as e:
    print(f"  Erro pygrabber: {e}")

# 2 - Non-virtual cameras with DEFAULT
print("\n2. NON-VIRTUAL com DEFAULT:")
try:
    for i, nome in enumerate(FilterGraph().get_input_devices()):
        if not any(v in nome.lower() for v in virtuais):
            tentar(i, None, nome)
except Exception as e:
    print(f"  Erro pygrabber: {e}")

# 3 - ALL cameras DSHOW
print("\n3. TODAS com DSHOW:")
for i in range(5):
    tentar(i, cv2.CAP_DSHOW)

# 4 - ALL cameras DEFAULT
print("\n4. TODAS com DEFAULT:")
for i in range(5):
    tentar(i)
