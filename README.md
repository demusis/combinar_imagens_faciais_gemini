# Síntese Facial Forense Assistida por IA Generativa (Google Gemini)

## Resumo do Projeto
Esta implementação consiste em uma aplicação *web* monolítica desenvolvida em Python/Flask, projetada para integrar a API do Google Gemini (modelo `gemini-1.5-pro`) em fluxos de trabalho forenses. O sistema aceita um *dataset* de imagens faciais não padronizadas (múltiplos ângulos e iluminações) e utiliza engenharia de *prompt* para solicitar a síntese ou descrição de uma imagem em "Norma de Identificação Civil" (vista frontal rigorosa), visando a preservação de invariantes biométricos e proporções antropométricas.

## Arquitetura
O código opera em arquitetura servidor *stateless*, processando imagens exclusivamente em memória (`RAM`) para garantir a segurança da cadeia de custódia e evitar latência de I/O em disco.

* **Backend:** Flask (Microframework).
* **Motor de Inferência:** Google Generative AI (`google-generativeai`).
* **Processamento de Imagem:** Pillow (PIL).
* **Frontend:** HTML5/CSS3 embutido (renderização no lado do servidor).

## Pré-requisitos

* Python 3.9 ou superior.
* Chave de API válida do Google AI Studio (`GOOGLE_API_KEY`).

## Instalação e Configuração

1.  **Clonagem e Ambiente Virtual**
    Recomenda-se o isolamento das dependências:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    venv\Scripts\activate     # Windows
    ```

2.  **Instalação de Dependências**
    ```bash
    pip install flask google-generativeai pillow
    ```

3.  **Configuração de Credenciais**
    Defina a chave de API como variável de ambiente para evitar exposição no código-fonte:
    
    *Linux/Mac:*
    ```bash
    export GOOGLE_API_KEY="sua_chave_aqui"
    ```
    
    *Windows (PowerShell):*
    ```powershell
    $env:GOOGLE_API_KEY="sua_chave_aqui"
    ```

## Execução

Inicie o servidor de aplicação:

```bash
python app.py
