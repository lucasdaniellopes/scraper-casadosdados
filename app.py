from flask import Flask, jsonify, request
import cloudscraper
import logging
from bs4 import BeautifulSoup
from collections import defaultdict
from unidecode import unidecode

app = Flask(__name__)


logging.basicConfig(level=logging.INFO)

@app.route('/api/consulta-cnpj', methods=['POST'])
def consultar_cnpj():
    try:
        logging.info(f"Request headers: {request.headers}")
        logging.info(f"Request data (raw): {request.data}")
        
        data = request.get_json(force=True)

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        scraper = cloudscraper.create_scraper()
        url = 'https://api.casadosdados.com.br/v2/public/cnpj/search'
        response = scraper.post(url, json=data)  

        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Falha na requisição à API", 
                            "status_code": response.status_code}), response.status_code
    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/obter-links-cnpj', methods=['GET'])
def scrape_json():
    try:
        url = 'https://casadosdados.com.br/solucao/cnpj?q=diogo+vieira+de+oliveira'

        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)

        if response.status_code == 200:
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            p_tags = soup.select("p[data-v-a7c716ab]")[2:]
            
            p_data = []
            for p in p_tags:
                p_text = ' '.join(p.stripped_strings)
                links = [a['href'].replace('"', '') for a in p.find_all('a', href=True)]

                if isinstance(links, list):
                    p_info = {
                        "text": p_text,
                        "links": links
                    }
                    p_data.append(p_info)

            return jsonify(p_data), 200

        else:
            return jsonify({"error": "Falha ao acessar a página", 
                            "status_code": response.status_code}), response.status_code

    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/extrair-dados-empresa', methods=['GET'])
def extrair_elementos():
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({"error": "URL é obrigatória."}), 400

        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)

        if response.status_code != 200:
            return jsonify({"error": "Falha ao acessar a página", "status_code": response.status_code}), response.status_code

        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        elementos_titulos = soup.select("div > label[data-v-533dd612]")

        dados_extracao = defaultdict(list)

        for titulo in elementos_titulos:
            titulo_texto = unidecode(titulo.get_text(strip=True).replace(":", ""))
            if not titulo_texto:
                titulo_texto = "-"

            p_irmao = titulo.find_next_sibling()
            has_value = False

            while p_irmao and p_irmao.name == "p" and "has-text-weight-bold" in p_irmao.get("class", []):
                valor_texto = p_irmao.get_text(strip=True)

                if titulo_texto == "Telefone":
                    valor_texto = valor_texto.replace("Whatsapp", "").strip()

                dados_extracao[titulo_texto].append(valor_texto)
                has_value = True
                p_irmao = p_irmao.find_next_sibling()

            if "CNAEs Secundarios" in titulo_texto:
                cnae_secundarios = []
                while p_irmao and p_irmao.name == "p" and "has-text-weight-bold" in p_irmao.get("class", []):
                    cnae_secundarios.append(p_irmao.get_text(strip=True))
                    p_irmao = p_irmao.find_next_sibling()

                if cnae_secundarios:
                    dados_extracao["CNAEs Secundarios"].extend(cnae_secundarios)

            if not has_value:
                dados_extracao[titulo_texto].append("-")

        resultado_final = {}
        for chave, valores in dados_extracao.items():
            if len(valores) == 1:
                resultado_final[chave] = valores[0]
            else:
                resultado_final[chave] = valores

        return jsonify(resultado_final), 200

    except Exception as e:
        logging.error(f"Erro geral: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
