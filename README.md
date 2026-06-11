# Reconhecimento Facial

Sistema desktop de reconhecimento facial com OpenCV, CustomTkinter e SQLite.

## Funcionalidades

- **Cadastro de pessoas** com captura de fotos via câmera
- **Reconhecimento facial** em tempo real (LBPH)
- **Detecção de duplicatas** — bloqueia cadastro se o rosto ou matrícula já existirem
- **Exclusão individual** ou limpeza total dos dados
- Interface moderna com CustomTkinter

## Requisitos

- Python 3.8+
- Webcam

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

1. **Cadastrar Pessoa** — informe nome e matrícula, capture 5+ fotos
2. **Iniciar Reconhecimento** — reconhece rostos cadastrados em tempo real
3. **Limpar Dados** — apaga todo o banco e fotos

## Estrutura

```
reconhecimento-facial/
├── main.py          # ponto de entrada
├── frontend.py      # interface gráfica
├── cadastrar.py     # cadastro e treinamento do modelo
├── database.py      # abstração do banco (SQLite / API)
├── reconhecer.py    # reconhecimento via terminal
└── requirements.txt
```
