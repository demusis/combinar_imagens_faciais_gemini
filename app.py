import os
import io
import base64
import re
import time
import google.generativeai as genai
from flask import Flask, request, Response, stream_with_context, redirect
from PIL import Image

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
os.environ["GOOGLE_API_KEY"] = "SUA_CHAVE_API_AQUI"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
MODEL_NAME = 'gemini-1.5-pro-latest'

MAX_ATTEMPTS = 3
TARGET_SCORE = 85

# ==============================================================================
# INTERFACE (HTML/JS/CSS)
# ==============================================================================
HTML_HEADER = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Console Forense | Alta Fidelidade</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #eceff1; padding: 20px; color: #333; }
        .container { max-width: 1100px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        h2 { border-bottom: 2px solid #cfd8dc; padding-bottom: 10px; color: #37474f; }
        
        .log-window { background-color: #263238; color: #cfd8dc; font-family: 'Consolas', monospace; padding: 15px; border-radius: 5px; height: 350px; overflow-y: auto; border: 1px solid #455a64; margin-bottom: 20px; font-size: 0.85rem; line-height: 1.5; }
        .log-line { margin-bottom: 5px; border-bottom: 1px solid #37474f; padding-bottom: 2px; }
        .log-time { color: #80cbc4; margin-right: 10px; }
        
        .progress-container { width: 100%; background-color: #e0e0e0; border-radius: 4px; margin-bottom: 20px; height: 8px; overflow: hidden; }
        .progress-bar { width: 0%; height: 100%; background-color: #00897b; transition: width 0.5s; }
        
        .gallery img { height: 70px; border: 1px solid #b0bec5; border-radius: 3px; margin-right: 5px; }
        #final-result-area { display: none; border-top: 3px solid #00897b; margin-top: 20px; padding-top: 20px; }
        .result-box { background: #e0f2f1; padding: 20px; border-radius: 5px; border-left: 5px solid #00897b; white-space: pre-wrap; font-family: 'Consolas', monospace; }
        
        .btn-submit { background-color: #37474f; color: white; padding: 15px; border: none; font-weight: bold; cursor: pointer; border-radius: 4px; width: 100%; }
        .btn-submit:hover { background-color: #263238; }
    </style>
    <script>
        function addLog(type, message) {
            const logWin = document.getElementById('log-window');
            const now = new Date().toLocaleTimeString();
            const line = document.createElement('div');
            line.className = 'log-line';
            let color = '#b0bec5';
            if(type === 'WARN') color = '#ffcc80';
            if(type === 'SUCCESS') color = '#a5d6a7';
            if(type === 'ERROR') color = '#ef9a9a';
            line.innerHTML = `<span class="log-time">[${now}]</span><span style="color:${color}">${message}</span>`;
            logWin.appendChild(line);
            logWin.scrollTop = logWin.scrollHeight;
        }
        function updateProgress(percent) { document.getElementById('progress-bar').style.width = percent + '%'; }
        function showResult() { document.getElementById('final-result-area').style.display = 'block'; }
    </script>
</head>
<body>
    <div class="container">
        <h2>Sistema Integrado de Reconstrução Craniométrica</h2>
"""

HTML_FORM = """
        <form action="/processar" method="post" enctype="multipart/form-data">
            <div style="background: #f5f5f5; padding: 20px; margin-bottom: 20px; border: 1px dashed #b0bec5;">
                <label><strong>Upload de Evidências (Degradadas/Multi-ângulo):</strong></label><br><br>
                <input type="file" name="files" multiple accept=".jpg,.jpeg,.png,.webp" required>
            </div>
            <button type="submit" class="btn-submit">INICIAR ANÁLISE & SÍNTESE (STREAMING)</button>
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
def index(): return HTML_HEADER + HTML_FORM

@app.route('/processar', methods=['POST'])
def processar():
    if 'files' not in request.files: return redirect('/')
    files = request.files.getlist('files')
    
    pil_images = []
    b64_imgs = []
    for file in files:
        if file.filename:
            val = file.read()
            pil_images.append(Image.open(io.BytesIO(val)))
            b64_imgs.append(base64.b64encode(val).decode('utf-8'))

    def generate():
        yield HTML_HEADER
        yield f'<div class="gallery" style="margin-bottom:20px;">' + ''.join([f'<img src="data:image/jpeg;base64,{img}">' for img in b64_imgs]) + '</div>'
        yield '<div class="progress-container"><div id="progress-bar" class="progress-bar"></div></div>'
        yield '<h3>Log de Auditoria (ACE-V)</h3><div id="log-window" class="log-window"></div>'
        yield '<div id="final-result-area"><h3>Resultado da Perícia</h3><div id="final-content" class="result-box"></div></div>'
        
        model = genai.GenerativeModel(MODEL_NAME)
        
        # --- ESTÁGIO 1: ANÁLISE ESTRUTURAL ---
        yield "<script>addLog('INFO', 'Iniciando Mapeamento de Invariantes...'); updateProgress(10);</script>"
        
        # Aqui inserimos a PARTE 1 do seu prompt rigoroso
        prompt_analise = """
        ATUAÇÃO: Antropólogo Forense Digital.
        
        TAREFA: Análise Craniométrica Estática.
        Analise o dataset e liste o estado dos seguintes marcos (ignorando tecido mole):
        
        1. ANCORAGEM DE MARCOS ANATÔMICOS:
           - Zona Orbital: Distância Intercantal e Cumes Supraorbitais.
           - Zona Média: Largura Bizigomática e Abertura Piriforme (base nasal óssea).
           - Zona Inferior: Ângulo Goníaco e Pogonion (mento).
           - Lateralidade: Morfologia da Orelha (se visível).
           
        SAÍDA: Apenas o relatório técnico dos dados brutos observados.
        """
        
        try:
            resp_analise = model.generate_content([prompt_analise] + pil_images)
            analise_texto = resp_analise.text.replace('\n', '<br>')
            yield f"<script>addLog('SUCCESS', 'Extração de Marcos Anatômicos concluída.'); updateProgress(25);</script>"
        except Exception as e:
            yield f"<script>addLog('ERROR', 'Erro API: {str(e)}');</script>"
            return

        # --- LOOP RECURSIVO ---
        feedback = ""
        melhor_res = ""
        
        for i in range(MAX_ATTEMPTS):
            iter_num = i + 1
            yield f"<script>addLog('INFO', '>>> Iteração {iter_num}/{MAX_ATTEMPTS}: Síntese e Retificação');</script>"
            
            # Aqui inserimos a PARTE 2 (Completa) do seu prompt rigoroso
            prompt_sintese = f"""
            CONTEXTO: Perícia Forense Digital e Antropometria Computacional.
            INPUT: Imagens Originais + Relatório Base.
            
            FEEDBACK OBRIGATÓRIO DA AUDITORIA ANTERIOR: "{feedback}"
            
            TAREFA DE PROCESSAMENTO E RESTAURAÇÃO:
            
            1. INVARIANTES (Travar estritamente):
               - Zona Orbital (Intercantal/Supraorbitais).
               - Zona Média (Bizigomática/Piriforme ignorando cartilagem).
               - Zona Inferior (Ângulo Goníaco/Pogonion).
               
            2. FILTRAGEM DE RUÍDO E RETIFICAÇÃO:
               - Diferencie pixelização de textura da pele.
               - Corrija distorções de lente (barrel distortion) via triangulação.
               - Remova elementos transientes: barba, óculos, sombras de alto contraste.
            
            OUTPUT SOLICITADO:
            Síntese Visual/Descritiva em "Norma de Identificação Civil":
            - Pose: Frontalidade absoluta (Plano de Frankfurt alinhado).
            - Iluminação: Difusa (Flat Lighting) para evidenciar volumetria.
            - Expressão: Neutra (repouso mecânico).
            """
            
            resp_sintese = model.generate_content([prompt_sintese] + pil_images)
            sintese_atual = resp_sintese.text
            
            yield f"<script>addLog('INFO', 'Síntese {iter_num} gerada. Validando Invariantes...'); updateProgress({25 + (iter_num * 20)});</script>"
            
            # Estágio 3: Auditoria
            prompt_auditoria = f"""
            ATUAÇÃO: Auditor de Qualidade Forense.
            PROPOSTA: "{sintese_atual}"
            
            CRITÉRIOS RÍGIDOS:
            1. O Pogonion e Ângulo Goníaco foram preservados?
            2. O Plano de Frankfurt está alinhado (0º Pitch)?
            3. Houve remoção correta de transientes (barba/óculos)?
            
            SAÍDA: 1. SCORE [0-100]. 2. JUSTIFICATIVA. 3. CORREÇÃO NECESSÁRIA.
            """
            
            resp_auditoria = model.generate_content([prompt_auditoria] + pil_images)
            auditoria_texto = resp_auditoria.text
            score = extrair_score(auditoria_texto)
            
            if score >= TARGET_SCORE:
                yield f"<script>addLog('SUCCESS', 'AUDITORIA APROVADA! Score: {score}/100.'); updateProgress(100);</script>"
                melhor_res = sintese_atual
                break
            else:
                yield f"<script>addLog('WARN', 'Reprovado (Score {score}). Ajustando parâmetros para próxima iteração...');</script>"
                feedback = auditoria_texto
                if iter_num == MAX_ATTEMPTS:
                    yield "<script>addLog('ERROR', 'Máximo de tentativas atingido. Entregando melhor resultado viável.');</script>"
                    melhor_res = sintese_atual

        final_safe = melhor_res.replace('"', '&quot;').replace('\n', '\\n')
        yield f"""<script>
            document.getElementById('final-content').innerText = "{final_safe}";
            showResult();
            addLog('INFO', 'Processo encerrado.');
        </script></div></body></html>"""

    return Response(stream_with_context(generate()), mimetype='text/html')

if __name__ == '__main__':
    print("Servidor Forense Rigoroso (Streaming) ativo em http://127.0.0.1:5000")
    app.run(debug=True, port=5000, threaded=True)
