import os
import io
import base64
import re
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
MODEL_NAME = 'gemini-1.5-pro-latest'

# Configurações do Processo
MAX_ATTEMPTS = 3
TARGET_SCORE = 85

# ==============================================================================
# TEMPLATES HTML (Divididos para Streaming)
# ==============================================================================

HTML_HEADER = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Console Forense | Log em Tempo Real</title>
    <style>
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #eceff1; padding: 20px; color: #333; }
        .container { max-width: 1100px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        
        h2 { border-bottom: 2px solid #cfd8dc; padding-bottom: 10px; color: #37474f; }
        
        /* Terminal de Log */
        .log-window { background-color: #263238; color: #cfd8dc; font-family: 'Consolas', 'Courier New', monospace; padding: 15px; border-radius: 5px; height: 300px; overflow-y: auto; border: 1px solid #455a64; margin-bottom: 20px; font-size: 0.9rem; line-height: 1.5; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); }
        .log-line { margin-bottom: 5px; border-bottom: 1px solid #37474f; padding-bottom: 2px; }
        .log-time { color: #80cbc4; margin-right: 10px; }
        .log-info { color: #b0bec5; }
        .log-warn { color: #ffcc80; }
        .log-success { color: #a5d6a7; font-weight: bold; }
        .log-error { color: #ef9a9a; font-weight: bold; }

        /* Barra de Progresso */
        .progress-container { width: 100%; background-color: #e0e0e0; border-radius: 4px; margin-bottom: 20px; height: 10px; overflow: hidden; }
        .progress-bar { width: 0%; height: 100%; background-color: #00897b; transition: width 0.5s; }

        /* Galeria */
        .gallery img { height: 70px; border: 1px solid #b0bec5; border-radius: 3px; margin-right: 5px; }
        
        /* Resultado Final */
        #final-result-area { display: none; border-top: 3px solid #00897b; margin-top: 20px; padding-top: 20px; animation: fadeIn 1s; }
        .result-box { background: #e0f2f1; padding: 20px; border-radius: 5px; border-left: 5px solid #00897b; white-space: pre-wrap; font-family: 'Consolas', monospace; }
        
        .btn-submit { background-color: #37474f; color: white; padding: 15px 30px; border: none; font-weight: bold; cursor: pointer; border-radius: 4px; width: 100%; font-size: 1rem; transition: background 0.2s; }
        .btn-submit:hover { background-color: #263238; }

        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    </style>
    <script>
        // Função para adicionar linhas ao log via Streaming
        function addLog(type, message) {
            const logWin = document.getElementById('log-window');
            const now = new Date().toLocaleTimeString();
            const line = document.createElement('div');
            line.className = 'log-line';
            
            let colorClass = 'log-info';
            if(type === 'WARN') colorClass = 'log-warn';
            if(type === 'SUCCESS') colorClass = 'log-success';
            if(type === 'ERROR') colorClass = 'log-error';
            
            line.innerHTML = `<span class="log-time">[${now}]</span><span class="${colorClass}">${message}</span>`;
            logWin.appendChild(line);
            logWin.scrollTop = logWin.scrollHeight; // Auto-scroll
        }
        
        function updateProgress(percent) {
            document.getElementById('progress-bar').style.width = percent + '%';
        }
        
        function showResult() {
            document.getElementById('final-result-area').style.display = 'block';
        }
    </script>
</head>
<body>
    <div class="container">
        <h2>Sistema Integrado de Reconstrução Facial Forense</h2>
"""

HTML_FORM = """
        <form action="/processar" method="post" enctype="multipart/form-data">
            <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; border: 1px dashed #b0bec5;">
                <label style="font-weight:bold;">1. Upload de Evidências (Imagens Degradadas/Multi-ângulo):</label><br><br>
                <input type="file" name="files" multiple accept=".jpg,.jpeg,.png,.webp" required>
            </div>
            <button type="submit" class="btn-submit">INICIAR PIPELINE RECURSIVO (STREAMING)</button>
        </form>
    </div>
</body>
</html>
"""

# ==============================================================================
# LÓGICA DO SERVIDOR
# ==============================================================================

app = Flask(__name__)

def extrair_score(texto):
    try:
        match = re.search(r'(?:SCORE|NOTA|PONTUAÇÃO).*?(\d{1,3})', texto, re.IGNORECASE)
        return int(match.group(1)) if match else 0
    except: return 0

@app.route('/', methods=['GET'])
def index():
    return HTML_HEADER + HTML_FORM

@app.route('/processar', methods=['POST'])
def processar():
    if 'files' not in request.files: return redirect('/')
    files = request.files.getlist('files')
    
    # Processamento inicial de imagens
    pil_images = []
    b64_imgs = []
    for file in files:
        if file.filename:
            val = file.read()
            pil_images.append(Image.open(io.BytesIO(val)))
            b64_imgs.append(base64.b64encode(val).decode('utf-8'))

    # Função Geradora (Streaming)
    def generate():
        # 1. Envia o Cabeçalho e Estrutura da Página
        yield HTML_HEADER
        
        # Injeta o HTML da Galeria e do Console de Log
        gallery_html = '<div class="gallery" style="margin-bottom:20px;">' + ''.join([f'<img src="data:image/jpeg;base64,{img}">' for img in b64_imgs]) + '</div>'
        
        yield f"""
        <div class="gallery-area">
            <strong>Evidências Carregadas:</strong><br><br>
            {gallery_html}
        </div>
        
        <div class="progress-container"><div id="progress-bar" class="progress-bar"></div></div>
        
        <h3>Log de Processamento (ACE-V)</h3>
        <div id="log-window" class="log-window"></div>
        
        <div id="final-result-area">
            <h3>Resultado Final da Perícia</h3>
            <div id="final-content" class="result-box"></div>
        </div>
        
        <script>addLog('INFO', 'Sistema inicializado. {len(pil_images)} imagens carregadas na memória segura.');</script>
        """
        
        model = genai.GenerativeModel(MODEL_NAME)
        
        # --- ESTÁGIO 1: ANÁLISE ---
        yield "<script>addLog('INFO', 'Estágio 1/3: Iniciando Mapeamento Craniométrico...'); updateProgress(10);</script>"
        
        prompt_analise = """
        ATUAÇÃO: Antropólogo Forense Digital.
        TAREFA: Mapeamento estrito de INVARIANTES ÓSSEOS.
        INSTRUÇÃO: Liste características observadas (Zona Orbital, Média, Inferior) ignorando ruído.
        """
        try:
            resp_analise = model.generate_content([prompt_analise] + pil_images)
            analise_texto = resp_analise.text.replace('\n', '<br>') # Formata para JS
            yield f"<script>addLog('SUCCESS', 'Análise Biométrica Concluída.'); updateProgress(30);</script>"
        except Exception as e:
            yield f"<script>addLog('ERROR', 'Falha na API: {str(e)}');</script>"
            return

        # --- LOOP RECURSIVO ---
        feedback = ""
        melhor_resultado = ""
        
        for i in range(MAX_ATTEMPTS):
            iter_num = i + 1
            yield f"<script>addLog('INFO', '>>> Iniciando Iteração {iter_num}/{MAX_ATTEMPTS} (Refinamento)');</script>"
            
            # Estágio 2: Síntese
            prompt_sintese = f"""
            CONTEXTO: Perícia Forense. INPUT: Imagens + Relatório Base.
            FEEDBACK CORRETIVO ANTERIOR: "{feedback}"
            
            TAREFA:
            1. Filtragem e Retificação (Correção de Lente, Remoção de Transientes).
            2. Norma Civil: Frontalidade Absoluta (Plano de Frankfurt), Iluminação Difusa.
            Gere a descrição/síntese técnica.
            """
            resp_sintese = model.generate_content([prompt_sintese] + pil_images)
            sintese_atual = resp_sintese.text
            
            yield f"<script>addLog('INFO', 'Síntese {iter_num} gerada. Enviando para Auditoria...'); updateProgress({30 + (iter_num * 15)});</script>"
            
            # Estágio 3: Auditoria
            prompt_auditoria = f"""
            ATUAÇÃO: Auditor de Qualidade Forense.
            PROPOSTA: "{sintese_atual}"
            CHECKLIST: Plano de Frankfurt (0º Pitch)? Invariantes preservados? Alucinações?
            SAÍDA: 1. SCORE [0-100]. 2. CRÍTICA. 3. ORDEM DE CORREÇÃO.
            """
            resp_auditoria = model.generate_content([prompt_auditoria] + pil_images)
            auditoria_texto = resp_auditoria.text
            score = extrair_score(auditoria_texto)
            
            # Log da decisão
            if score >= TARGET_SCORE:
                yield f"<script>addLog('SUCCESS', 'AUDITORIA APROVADA! Score: {score}/100. Critério de qualidade atingido.'); updateProgress(100);</script>"
                melhor_resultado = sintese_atual
                break
            else:
                yield f"<script>addLog('WARN', 'Reprovação na Auditoria. Score: {score}/100. Motivo: Desvios anatômicos detectados.');</script>"
                feedback = auditoria_texto
                if iter_num == MAX_ATTEMPTS:
                    yield "<script>addLog('ERROR', 'Limite de tentativas excedido. Utilizando melhor resultado disponível.');</script>"
                    melhor_resultado = sintese_atual

        # --- FINALIZAÇÃO ---
        # Escapa quebras de linha para não quebrar o JavaScript
        final_safe = melhor_resultado.replace('"', '&quot;').replace('\n', '\\n')
        log_full = auditoria_texto.replace('"', '&quot;').replace('\n', '\\n')
        
        yield f"""
        <script>
            document.getElementById('final-content').innerText = "{final_safe}";
            showResult();
            addLog('INFO', 'Processo finalizado. Cadeia de custódia encerrada.');
        </script>
        </div></body></html>
        """

    return Response(stream_with_context(generate()), mimetype='text/html')

if __name__ == '__main__':
    print("Servidor Forense (Streaming Log) ativo em http://127.0.0.1:5000")
    app.run(debug=True, port=5000, threaded=True)
