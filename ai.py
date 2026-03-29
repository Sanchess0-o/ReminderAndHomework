import requests

API_KEY = " "

url = "https://openrouter.ai/api/v1/chat/completions"

def generate_ai_text(user_message):




    headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        # необязательно:
        # "HTTP-Referer": "https://your-site.com",
        # "X-Title": "My Test Bot",
    }

    data = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": "Ты полезный помощник."},
            {"role": "user", "content": f"{user_message}"}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]
      

    except requests.exceptions.HTTPError:
        print("HTTP ошибка:", response.status_code)
        print(response.text)

    except requests.exceptions.RequestException as e:
        print("Ошибка запроса:", e)

    except KeyError:
        print("Неожиданный формат ответа:")
        print(response.text)

