import os
import io
import google.generativeai as genai
from flask import Flask, request, render_template_string, redirect, flash
from PIL import Image

# ==============================================================================
# CONFIGURAÇÃO E CONSTANTES
# ==============================================================================

# Configuração da API Key do Google Gemini
os.environ["GOOGLE_API_KEY"] = "SUA_CHAVE_API_AQUI"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Definição do Modelo
MODEL_NAME = 'gemini-1.5-pro-latest'

# Interface do Usuário (Frontend embutido)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Console de Síntese Forense (Monolítico)</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #eceff1; padding: 40px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 700px; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h2 { color: #37474f; border-bottom: 2px solid #cfd8dc; padding-bottom: 15px; margin-top: 0; font-weight: 600; }
        .alert { padding: 15px; margin-bottom: 20px; border-radius: 4px; font-size: 0.9rem; }
        .alert-error { background-color: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
        .form-group { border: 2px dashed #b0bec5; padding: 30px; text-align: center; border-radius: 6px; background: #fafafa; margin-bottom: 20px; transition: background 0.3s; }
        .form-group:hover { background: #f0f4c3; border-color: #827717; }
        input[type="file"] { margin-top: 10px; }
        button { width: 100%; background-color: #455a64; color: white; border: none; padding: 15px; font-size: 1rem; font-weight: bold; cursor: pointer; border-radius: 4px; transition: background 0.2s; }
        button:hover { background-color: #263238; }
        .output-area { margin-top: 30px; background: #f1f8e9; padding: 20px; border-left: 5px solid #33691e; white-space: pre-wrap; line-height: 1.6; }
        .technical-note { font-size: 0.8rem; color: #78909c; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Módulo de Processamento Facial</h2>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-error">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% if erro_sistema %}
            <div class="alert alert-error"><strong>Erro do Sistema:</strong> {{ erro_sistema }}</div>
        {% endif %}

        <form action="/processar" method="post" enctype="multipart/form-data">
            <div class="form-group">
                <label>Carregar Dataset (Imagens do Indivíduo)</label>
                <br><br>
                <input type="file" name="files" multiple accept=".jpg,.jpeg,.png,.webp" required>
            </div>
            <button type="submit">Iniciar Síntese Forense</button>
        </form>

        {% if resultado %}
        <div class="output-area">
            <strong>Retorno da Inferência:</strong><br><br>
            {{ resultado }}
        </div>
        {% endif %}
        
        <div class="technical-note">
            Ambiente de execução única. Nenhuma imagem é retida no servidor.
        </div>
    </div>
</body>
</html>
"""

# ==============================================================================
# LÓGICA DO SERVIDOR (BACKEND)
# ==============================================================================

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/processar', methods=['POST'])
def processar():
    if 'files' not in request.files:
        flash('Requisição inválida: nenhum arquivo anexado.')
        return redirect('/')

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        flash('Nenhum arquivo foi selecionado para upload.')
        return redirect('/')

    # Carregamento e pré-processamento em memória
    input_images = []
    try:
        for file in files:
            if file.filename:
                # Leitura direta do buffer de bytes para PIL
                image_bytes = file.read()
                img = Image.open(io.BytesIO(image_bytes))
                input_images.append(img)
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, erro_sistema=f"Falha na leitura de I/O: {e}")

    # Construção do Prompt de Engenharia Forense
    prompt_sistema = """
    Contexto: Atuação como perito forense digital.
    Tarefa: Analisar o conjunto de imagens faciais fornecidas de um único sujeito.
    Objetivo: Sintetizar uma descrição ou representação visual para "Norma de Identificação Civil" (Mugshot).
    
    Requisitos Rígidos:
    1. Orientação: Frontal estrita (0º pitch/yaw/roll).
    2. Invariantes: Manter morfologia exata de nariz, olhos e queixo.
    3. Expressão: Neutra total (sem sorriso, olhos abertos).
    4. Iluminação: Uniforme, eliminando sombras de alto contraste presentes nas originais.
    
    Saída Esperada: Gere o resultado focando na precisão anatômica para fins de reconhecimento.
    """

    # Chamada à API
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content([prompt_sistema] + input_images)
        
        # Verificação e extração do resultado
        texto_resultado = response.text if response.parts else "Aviso: O modelo processou a entrada mas não retornou texto descritivo. Verifique filtros de segurança."
        
        return render_template_string(HTML_TEMPLATE, resultado=texto_resultado)

    except Exception as e:
        return render_template_string(HTML_TEMPLATE, erro_sistema=f"Erro na API Google Gemini: {e}")

if __name__ == '__main__':
    # Inicia o servidor local na porta 5000
    print("Iniciando servidor em http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
