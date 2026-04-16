from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os, time, logging, requests
from ddgs import DDGS

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
app = Flask(__name__, static_folder="static")

def bios_validate(text: str) -> tuple[bool, str]:
    harmful = ["взлом", "краж", "вирус", "удалить файлы", "пароль", "обойти защиту", "наркоти", "оружие", "террор"]
    if any(bad in text.lower() for bad in harmful):
        return False, "Policy violation: potentially harmful content"
    return True, "ok"

def search_agent(query: str, max_results: int = 3) -> str:
    try:
        results = DDGS().text(query, max_results=max_results)
        if not results: return "[Поиск не дал результатов]"
        safe = [f"{r.get('title','')}: {r.get('body','')}" for r in results if bios_validate(f"{r.get('title','')} {r.get('body','')}")[0]]
        return "\n".join(safe[:2]) if safe else "[Все результаты отклонены BIOS]"
    except Exception as e:
        logger.error(f"Search error: {e}")
        return "[Ошибка поиска]"

def ask_cloud(prompt: str, context: str = "") -> str:
    api_key, folder_id = os.getenv("YANDEX_API_KEY"), os.getenv("YC_FOLDER_ID")
    timeout = int(os.getenv("REQUEST_TIMEOUT", 30))
    if not api_key or not folder_id: return "[Ошибка: не указаны ключи в .env]"
    system = "Ты — помощник BIOS Cloud Gateway. Отвечай кратко. Используй контекст, если он есть." + (f"\n\nКонтекст:\n{context}" if context else "")
    try:
        resp = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion", headers={"Authorization": f"Api-Key {api_key}", "x-folder-id": folder_id}, json={"modelUri": f"gpt://{folder_id}/yandexgpt-lite/latest", "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 2000}, "messages": [{"role": "system", "text": system}, {"role": "user", "text": prompt}]}, timeout=timeout)
        if resp.status_code != 200: return f"[Ошибка API: {resp.status_code}]"
        data = resp.json()
        return data['result']['alternatives'][0]['message']['text'] if 'result' in data and data['result'].get('alternatives') else "[Ошибка формата]"
    except Exception as e: return f"[Ошибка: {str(e)[:100]}]"

@app.route('/health')
def health(): return jsonify({"status": "ok", "bios_gateway": "active", "version": "1.1-final"})

@app.route('/ask', methods=['POST'])
def ask():
    t0 = time.time()
    data = request.get_json() or {}
    prompt, use_search = data.get('prompt', '').strip(), data.get('use_search', False)
    if not prompt: return jsonify({"response": "[Пустой запрос]", "bios_status": "error"}), 400
    safe, reason = bios_validate(prompt)
    if not safe: return jsonify({"response": "[Запрос отклонён BIOS]", "bios_status": "blocked", "reason": reason}), 403
    ctx = search_agent(prompt) if use_search else ""
    answer = ask_cloud(prompt, ctx)
    safe_ans, reason_ans = bios_validate(answer)
    return (jsonify({"response": "[Ответ отклонён BIOS]", "bios_status": "blocked", "reason": reason_ans}), 403) if not safe_ans else jsonify({"response": answer, "bios_status": "ok", "model_source": f"yandexgpt/{os.getenv('YC_FOLDER_ID','?')}", "search_used": use_search, "processing_time": round(time.time()-t0, 2)})

@app.route('/')
def index(): return app.send_static_file('index.html')

if __name__ == '__main__':
    logger.info(f"🔐 BIOS Gateway v1.1-final on http://{os.getenv('HOST','127.0.0.1')}:{os.getenv('PORT',5000)}")
    app.run(host=os.getenv('HOST','127.0.0.1'), port=int(os.getenv('PORT',5000)), debug=False)
