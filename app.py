import os
import io
import base64
import google.generativeai as genai
from flask import Flask, request, render_template_string, redirect, flash
from PIL import Image

# ==============================================================================
# CONFIGURAÇÃO E CONSTANTES
# ==============================================================================

os.environ["GOOGLE_API_KEY"] = "SUA_CHAVE_API_AQUI"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Utilizando modelo com alta capacidade de raciocínio multimodal (verifique o mais recente, muda rápido).
MODEL_NAME = 'gemini-2.5-pro-latest'
gemini-1.5-pro-latest
# Frontend com visualização de Grid (Galeria)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Console Forense | Comparativo Visual</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #eceff1; padding: 20px; }
        .main-container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        
        h2 { color: #263238; border-bottom: 2px solid #cfd8dc; padding-bottom: 10px; margin-top: 0; }
        
        .alert { padding: 15px; margin-bottom: 20px; border-radius: 4px; color: #c62828; background-color: #ffebee; border: 1px solid #ef9a9a; }
        
        /* Layout de Comparação */
        .comparison-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px; }
        
        /* Coluna Esquerda: Inputs */
        .input-section { background: #f5f5f5; padding: 20px; border-radius: 5px; border: 1px solid #e0e0e0; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; margin-top: 15px; }
        .gallery img { width: 100%; height: 100px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc; }
        
        /* Coluna Direita: Output */
        .output-section { background: #e8f5e9; padding: 20px; border-radius: 5px; border-left: 5px solid #2e7d32; }
        .output-content { white-space: pre-wrap; line-height: 1.6; color: #1b5e20; font-family: 'Consolas', monospace; font-size: 0.95rem; }
        
        /* Formulário */
        .control-panel { background: #cfd8dc; padding: 20px; border-radius: 5px; display: flex; align-items: center; justify-content: space-between; }
        button { background-color: #37474f; color: white; border: none; padding: 12px 25px; font-weight: bold; cursor: pointer; border-radius: 4px; }
        button:hover { background-color: #455a64; }

        @media (max-width: 768px) { .comparison-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="main-container">
        <h2>Módulo de Reconstrução Facial Forense</h2>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form action="/processar" method="post" enctype="multipart/form-data">
            <div class="control-panel">
                <div>
                    <strong>Dataset de Entrada:</strong>
                    <input type="file" name="files" multiple accept=".jpg,.jpeg,.png,.webp" required>
                    <div style="font-size: 0.8em; margin-top: 5px; color: #546e7a;">Suporta imagens degradadas, CFTV e ângulos oblíquos.</div>
                </div>
                <button type="submit">Executar Análise & Síntese</button>
            </div>
        </form>

        {% if inputs_b64 or resultado %}
        <div class="comparison-grid">
            
            <div class="input-section">
                <h3>Evidências de Entrada</h3>
                <div style="font-size: 0.85rem; color: #666;">Imagens originais carregadas na memória (RAM):</div>
                <div class="gallery">
                    {% for img_data in inputs_b64 %}
                        <img src="data:image/jpeg;base64,{{ img_data }}" title="Evidência Input">
                    {% endfor %}
                </div>
            </div>

            <div class="output-section">
                <h3>Síntese / Reconstrução</h3>
                <div class="output-content">
                    {% if resultado %}
                        {{ resultado }}
                    {% else %}
                        <em>Aguardando processamento...</em>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# ==============================================================================
# LÓGICA DO SERVIDOR
# ==============================================================================

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/processar', methods=['POST'])
def processar():
    if 'files' not in request.files:
        flash('Erro: Requisição vazia.')
        return redirect('/')

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        flash('Erro: Nenhuma imagem selecionada.')
        return redirect('/')

    pil_images = [] # Objetos PIL para a IA
    base64_images = [] # Strings para o HTML
    
    try:
        for file in files:
            if file.filename:
                # Lê os bytes do arquivo uma única vez
                file_bytes = file.read()
                
                # 1. Prepara para a IA (Pillow)
                img = Image.open(io.BytesIO(file_bytes))
                pil_images.append(img)
                
                # 2. Prepara para o Frontend (Base64)
                # Converte bytes brutos para string base64
                b64_str = base64.b64encode(file_bytes).decode('utf-8')
                base64_images.append(b64_str)
                
    except Exception as e:
        flash(f"Falha no processamento de imagem: {str(e)}")
        return redirect('/')

    # Prompt Avançado de Reconstrução (Versão Craniométrica Estendida)
    prompt_sistema = """
    Contexto: Perícia Forense Digital e Antropometria Computacional.
    
    INPUT: Dataset de imagens degradadas e multi-angulares.
    
    TAREFA DE PROCESSAMENTO E RESTAURAÇÃO:
    
    1. ANCORAGEM DE MARCOS ANATÔMICOS (Rigor Craniométrico):
       Ao sintetizar a face, você deve travar e preservar estritamente os seguintes invariantes ósseos:
       - Zona Orbital: Distância Intercantal (cantos internos) e Cumes Supraorbitais (testa/sobrancelha).
       - Zona Média: Largura Bizigomática (projeção das maçãs do rosto) e Abertura Piriforme (largura da base nasal real, ignorando cartilagem bulbosa).
       - Zona Inferior: Ângulo Goníaco (curva da mandíbula posterior) e Pogonion (proeminência do queixo).
       - Lateralidade: Morfologia da Orelha (se visível nos inputs).
       
    2. FILTRAGEM DE RUÍDO E RETIFICAÇÃO:
       - Diferencie pixelização de textura da pele.
       - Corrija distorções de lente (barrel distortion) usando triangulação das vistas oblíquas.
       - Remova elementos transientes: barba, óculos, sombras de alto contraste.
    
    OUTPUT SOLICITADO:
    Descrição técnica ou Síntese Visual em "Norma de Identificação Civil" (Mugshot):
    - Pose: Frontalidade absoluta (Plano de Frankfurt alinhado).
    - Iluminação: Difusa (Flat Lighting) para evidenciar a volumetria óssea sem sombras enganosas.
    - Expressão: Neutra (repouso mecânico).
    """

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content([prompt_sistema] + pil_images)
        texto_resultado = response.text if response.parts else "A API processou os dados mas não retornou descrição textual. Verifique se houve bloqueio de segurança."
        
        # Renderiza a página com os inputs (esquerda) e o resultado (direita)
        return render_template_string(HTML_TEMPLATE, inputs_b64=base64_images, resultado=texto_resultado)

    except Exception as e:
        flash(f"Erro de comunicação com a API Gemini: {str(e)}")
        return redirect('/')

if __name__ == '__main__':
    print("Servidor Forense Visual ativo em http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
