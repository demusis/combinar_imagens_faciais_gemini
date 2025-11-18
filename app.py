import os
import io
import base64
import time
from mimetypes import guess_type
import google.generativeai as genai
from flask import Flask, request, Response, stream_with_context, redirect
from PIL import Image

# ==============================================================================
# CONFIGURACAO
# ==============================================================================
# Em producao, defina GOOGLE_API_KEY no ambiente, nao no codigo-fonte
os.environ["GOOGLE_API_KEY"] = "SUA_CHAVE_API_AQUI"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Modelo de Raciocinio
MODEL_NAME = 'gemini-2.5-pro'

app = Flask(__name__)

# ==============================================================================
# INTERFACE DE DIAGNOSTICO
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
        
        /* Area de Logs (Esquerda) */
        .log-panel { background-color: #000; border: 1px solid #333; height: 85vh; overflow-y: auto; padding: 10px; font-size: 0.8rem; }
        .log-entry { margin-bottom: 2px; border-bottom: 1px solid #1a1a1a; padding: 2px 0; word-wrap: break-word; }
        .ts { color: #5c6bc0; margin-right: 8px; }
        .type-INFO { color: #b0bec5; }
        .type-NET { color: #29b6f6; } /* Rede/API */
        .type-DATA { color: #ab47bc; } /* Dados/Chunks */
        .type-WARN { color: #ffca28; }
        .type-ERROR { color: #ef5350; font-weight: bold; background: #2c0b0e; }
        .type-SUCCESS { color: #66bb6a; font-weight: bold; }
        
        /* Area Visual (Direita) */
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
        // Evitar HTML injection nos logs
        function log(type, msg) {
            const box = document.getElementById('log-box');
            const now = new Date().toISOString().split('T')[1].slice(0, -1); // HH:MM:SS.mmm

            const div = document.createElement('div');
            div.className = `log-entry type-${type}`;

            const tsSpan = document.createElement('span');
            tsSpan.className = 'ts';
            tsSpan.textContent = `[${now}]`;

            const msgSpan = document.createElement('span');
            msgSpan.textContent = ' ' + msg;

            div.appendChild(tsSpan);
            div.appendChild(msgSpan);

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
            <h2>Terminal de Diagnostico</h2>
            <div id="log-box" class="log-panel"></div>
        </div>
        
        <div class="visual-panel">
            <h3>Entrada de Evidencias</h3>
            <form action="/processar" method="post" enctype="multipart/form-data">
                <input type="file" name="files" multiple accept=".jpg,.jpeg,.png,.webp" required style="width:100%; padding:10px; background:#333; border:1px solid #555; color:#fff;">
                <button type="submit" class="btn-submit">>> Executar Pipeline (Debug Trace)</button>
            </form>
            
            <div id="gallery-area" style="margin-top:20px;"></div>
            
            <div id="report-area" style="margin-top:30px; border-top:2px solid #00e676; padding-top:20px; display:none;">
                <h3>Relatorio Final</h3>
                <div id="report-content" class="markdown-body"></div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ==============================================================================
# LOGICA
# ==============================================================================

@app.route('/', methods=['GET'])
def index():
    return HTML_TEMPLATE

@app.route('/processar', methods=['POST'])
def processar():
    if 'files' not in request.files:
        return redirect('/')

    files = request.files.getlist('files')

    pil_images = []
    b64_imgs = []  # agora guarda (mime, b64)
    total_bytes = 0

    for file in files:
        if file.filename:
            val = file.read()
            total_bytes += len(val)

            pil_images.append(Image.open(io.BytesIO(val)))

            mime, _ = guess_type(file.filename)
            if not mime:
                mime = "image/jpeg"
            b64_data = base64.b64encode(val).decode('utf-8')
            b64_imgs.append((mime, b64_data))

    def generate():
        # HTML base
        yield HTML_TEMPLATE
        
        # Renderiza Galeria com tipo de imagem correto
        imgs_html = ''.join(
            [f'<img src="data:{mime};base64,{data}">' for (mime, data) in b64_imgs]
        )
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
        # FASE 1: EXTRACAO VETORIAL (COM CONFIRMACAO DE UPLOAD)
        # ======================================================================
        yield "<script>log('INFO', '--- INICIANDO FASE 1: BIOMETRIA ---');</script>"
        
        prompt_fase1 = """
        ATUACAO: Biometrista Forense.
        TAREFA: Mapear Invariantes Vetoriais.
        
        Analise as imagens e descreva estritamente:
        1. Razoes do Triangulo Facial Central.
        2. Inclinacao Cantal (Olhos) e Distancia Intercantal.
        3. Morfologia do Filtro Labial e Arco do Cupido.
        4. Angulo Goniaco.
        
        SAIDA: Relatorio tecnico cru.
        """
        
        analise_acumulada = ""
        start_t = time.time()
        
        try:
            yield "<script>log('NET', 'Iniciando Upload do Payload (Imagens + Prompt)...');</script>"
            
            response_stream = model.generate_content([prompt_fase1] + pil_images, stream=True)
            
            yield "<script>log('SUCCESS', 'Upload Confirmado! Servidor do Google aceitou a requisicao.');</script>"
            yield "<script>log('WARN', 'Aguardando processamento neural (Time To First Token)...');</script>"
            
            chunk_count = 0
            for chunk in response_stream:
                chunk_count += 1

                text_part = getattr(chunk, "text", "") or ""
                analise_acumulada += text_part
                
                if chunk_count == 1:
                    yield "<script>log('DATA', '>>> Primeiro token recebido! A IA comecou a responder.');</script>"
                
                if chunk_count % 5 == 0:
                    yield f"<script>log('DATA', 'Recebendo fluxo... ({chunk_count} pacotes)');</script>"
            
            elapsed = time.time() - start_t
            yield f"<script>log('SUCCESS', 'Fase 1 concluida em {elapsed:.2f}s.');</script>"
            
            if not analise_acumulada:
                yield "<script>log('ERROR', 'A API aceitou o upload mas retornou texto vazio (Bloqueio de Seguranca?).');</script>"

        except Exception as e:
            yield f"<script>log('ERROR', 'ERRO DURANTE TRANSMISSAO: {str(e)}');</script>"
            return

        # ======================================================================
        # FASE 2: SÍNTESE
        # ======================================================================
        yield "<script>log('INFO', '--- INICIANDO FASE 2: SÍNTESE ---');</script>"
        
        prompt_fase2 = f"""
        CONTEXTO BIOMETRICO:
        {analise_acumulada}
        
        TAREFA: Laudo Pericial em Markdown.
        1. ## Analise Vetorial.
        2. ## Sintese Visual (Descricao da face em pose frontal 0º).
        3. ## Conclusao.
        """
        
        relatorio_final = ""
        
        try:
            yield "<script>log('NET', 'Enviando dados da Fase 2...');</script>"
            response_stream_2 = model.generate_content([prompt_fase2] + pil_images, stream=True)
            yield "<script>log('SUCCESS', 'Upload Fase 2 Confirmado. Aguardando geracao do laudo...');</script>"
            
            for chunk in response_stream_2:
                text_part = getattr(chunk, "text", "") or ""
                relatorio_final += text_part
            
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
    app.run(debug=False, port=5000, threaded=True)
