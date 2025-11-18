import os
import io
import base64
import time
import datetime
import google.generativeai as genai
from flask import Flask, request, Response, stream_with_context, redirect
from PIL import Image

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
os.environ["GOOGLE_API_KEY"] = "SUA_CHAVE_API_AQUI"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Modelo de Raciocínio
MODEL_NAME = 'gemini-2.5-pro'

app = Flask(__name__)

# ==============================================================================
# INTERFACE DE DIAGNÓSTICO
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Console Forense | Modo Debug</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { font-family: 'Consolas', 'Segoe UI', monospace; background-color: #121212; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        
        h2 { border-bottom: 1px solid #333; padding-bottom: 10px; color: #00e676; }
        
        /* Área de Logs (Esquerda) */
        .log-panel { background-color: #000; border: 1px solid #333; height: 85vh; overflow-y: auto; padding: 10px; font-size: 0.8rem; }
        .log-entry { margin-bottom: 2px; border-bottom: 1px solid #1a1a1a; padding: 2px 0; word-wrap: break-word; }
        .ts { color: #5c6bc0; margin-right: 8px; }
        .type-INFO { color: #b0bec5; }
        .type-NET { color: #29b6f6; } /* Rede/API */
        .type-DATA { color: #ab47bc; } /* Dados/Chunks */
        .type-WARN { color: #ffca28; }
        .type-ERROR { color: #ef5350; font-weight: bold; background: #2c0b0e; }
        .type-SUCCESS { color: #66bb6a; font-weight: bold; }
        
        /* Área Visual (Direita) */
        .visual-panel { background-color: #1e1e1e; padding: 20px; border-radius: 4px; height: 85vh; overflow-y: auto; }
        .gallery { display: flex; gap: 10px; margin-bottom: 20px; background: #2c2c2c; padding: 10px; border-radius: 4px; }
        .gallery img { height: 60px; border: 1px solid #555; }
        
        .markdown-body { font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #ddd; }
        .markdown-body h1, .markdown-body h2 { border-bottom: 1px solid #444; padding-bottom: 5px; color: #81d4fa; }
        .markdown-body strong { color: #fff; }
        
        .btn-submit { background-color: #00e676; color: #000; padding: 15px; width: 100%; border: none; font-weight: bold; cursor: pointer; margin-top: 20px; font-family: monospace; text-transform: uppercase; }
        .btn-submit:hover { background-color: #00c853; }
    </style>
    <script>
        function log(type, msg) {
            const box = document.getElementById('log-box');
            const now = new Date().toISOString().split('T')[1].slice(0, -1); // HH:MM:SS.mmm
            const div = document.createElement('div');
            div.className = `log-entry type-${type}`;
            div.innerHTML = `<span class="ts">[${now}]</span> ${msg}`;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }
        
        function renderReport(b64Text) {
            const text = new TextDecoder().decode(Uint8Array.from(atob(b64Text), c => c.charCodeAt(0)));
            document.getElementById('report-content').innerHTML = marked.parse(text);
        }
    </script>
</head>
<body>
    <div class="container">
        <div>
            <h2>Terminal de Diagnóstico</h2>
            <div id="log-box" class="log-panel"></div>
        </div>
        
        <div class="visual-panel">
            <h3>Entrada de Evidências</h3>
            <form action="/processar" method="post" enctype="multipart/form-data">
                <input type="file" name="files" multiple accept=".jpg,.jpeg,.png,.webp" required style="width:100%; padding:10px; background:#333; border:1px solid #555; color:#fff;">
                <button type="submit" class="btn-submit">>> Executar Pipeline (Debug Trace)</button>
            </form>
            
            <div id="gallery-area" style="margin-top:20px;"></div>
            
            <div id="report-area" style="margin-top:30px; border-top:2px solid #00e676; padding-top:20px; display:none;">
                <h3>Relatório Final</h3>
                <div id="report-content" class="markdown-body"></div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ==============================================================================
# LÓGICA
# ==============================================================================

@app.route('/', methods=['GET'])
def index(): return HTML_TEMPLATE

@app.route('/processar', methods=['POST'])
@app.route('/processar', methods=['POST'])
def processar():
    if 'files' not in request.files: return redirect('/')
    files = request.files.getlist('files')

    pil_images = []
    b64_imgs = []
    total_bytes = 0

    for file in files:
        if file.filename:
            val = file.read()
            total_bytes += len(val)
            pil_images.append(Image.open(io.BytesIO(val)))
            b64_imgs.append(base64.b64encode(val).decode('utf-8'))

    def generate():
        yield HTML_TEMPLATE
        
        # Renderiza Galeria
        imgs_html = ''.join([f'<img src="data:image/jpeg;base64,{x}">' for x in b64_imgs])
        yield f"""<script>
            document.getElementById('gallery-area').innerHTML = '<div class="gallery">{imgs_html}</div>';
            log('INFO', 'Sistema Iniciado. PID: {os.getpid()}');
            log('INFO', 'Imagens Carregadas: {len(pil_images)}');
            log('INFO', 'Volume Total: {total_bytes/1024:.2f} KB');
            log('NET', 'Inicializando driver Gemini ({MODEL_NAME})...');
        </script>"""
        
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            yield "<script>log('SUCCESS', 'Driver IA conectado.');</script>"
        except Exception as e:
            yield f"<script>log('ERROR', 'Falha driver: {str(e)}');</script>"
            return

        # ======================================================================
        # FASE 1: EXTRAÇÃO VETORIAL (COM CONFIRMAÇÃO DE UPLOAD)
        # ======================================================================
        yield "<script>log('INFO', '--- INICIANDO FASE 1: BIOMETRIA ---');</script>"
        
        prompt_fase1 = """
        ATUAÇÃO: Biometrista Forense.
        TAREFA: Mapear Invariantes Vetoriais.
        
        Analise as imagens e descreva estritamente:
        1. Razões do Triângulo Facial Central.
        2. Inclinação Cantal (Olhos) e Distância Intercantal.
        3. Morfologia do Filtro Labial e Arco do Cupido.
        4. Ângulo Goníaco.
        
        SAÍDA: Relatório técnico cru.
        """
        
        analise_acumulada = ""
        start_t = time.time()
        
        try:
            yield "<script>log('NET', 'Iniciando Upload do Payload (Imagens + Prompt)...');</script>"
            
            # A chamada com stream=True retorna o iterador assim que o cabeçalho é aceito
            response_stream = model.generate_content([prompt_fase1] + pil_images, stream=True)
            
            # SE O CÓDIGO CHEGOU AQUI, O UPLOAD FOI CONCLUÍDO
            yield "<script>log('SUCCESS', 'Upload Confirmado! Servidor do Google aceitou a requisição.');</script>"
            yield "<script>log('WARN', 'Aguardando processamento neural (Time To First Token)...');</script>"
            
            chunk_count = 0
            for chunk in response_stream:
                chunk_count += 1
                text_part = chunk.text if chunk.parts else ""
                analise_acumulada += text_part
                
                # Log do primeiro token (prova de vida)
                if chunk_count == 1:
                     yield "<script>log('DATA', '>>> Primeiro token recebido! A IA começou a responder.');</script>"
                
                # Log periódico para não poluir demais
                if chunk_count % 5 == 0:
                    yield f"<script>log('DATA', 'Recebendo fluxo... ({chunk_count} pacotes)');</script>"
            
            elapsed = time.time() - start_t
            yield f"<script>log('SUCCESS', 'Fase 1 concluída em {elapsed:.2f}s.');</script>"
            
            if not analise_acumulada:
                yield "<script>log('ERROR', 'A API aceitou o upload mas retornou texto vazio (Bloqueio de Segurança?).');</script>"

        except Exception as e:
            yield f"<script>log('ERROR', 'ERRO DURANTE TRANSMISSÃO: {str(e)}');</script>"
            return

        # ======================================================================
        # FASE 2: SÍNTESE
        # ======================================================================
        yield "<script>log('INFO', '--- INICIANDO FASE 2: SÍNTESE ---');</script>"
        
        prompt_fase2 = f"""
        CONTEXTO BIOMÉTRICO:
        {analise_acumulada}
        
        TAREFA: Laudo Pericial em Markdown.
        1. ## Análise Vetorial.
        2. ## Síntese Visual (Descrição da face em pose frontal 0º).
        3. ## Conclusão.
        """
        
        relatorio_final = ""
        
        try:
            yield "<script>log('NET', 'Enviando dados da Fase 2...');</script>"
            response_stream_2 = model.generate_content([prompt_fase2] + pil_images, stream=True)
            yield "<script>log('SUCCESS', 'Upload Fase 2 Confirmado. Aguardando geração do laudo...');</script>"
            
            for chunk in response_stream_2:
                if chunk.text: relatorio_final += chunk.text
            
            yield "<script>log('SUCCESS', 'Laudo recebido. Renderizando...');</script>"

            b64_final = base64.b64encode(relatorio_final.encode('utf-8')).decode('utf-8')
            yield f"""<script>
                document.getElementById('report-area').style.display = 'block';
                renderReport("{b64_final}");
                log('INFO', 'Processo finalizado com sucesso.');
            </script>"""

        except Exception as e:
            yield f"<script>log('ERROR', 'ERRO FASE 2: {str(e)}');</script>"

    return Response(stream_with_context(generate()), mimetype='text/html')

if __name__ == '__main__':
    print("Debug Server ativo: http://127.0.0.1:5000")
    app.run(debug=True, port=5000, threaded=True)
