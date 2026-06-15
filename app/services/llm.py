from openai import OpenAI

class LLMClient:

    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def call(self, prompt: str):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content


# ✅ FUNÇÃO FORA DA CLASSE
def analisar_requisito(texto: str):
    return {
        "texto": texto,
        "ambiguidade": "baixa",
        "incompleto": False,
        "consistencia": "ok",
        "realismo": "alto",
        "integridade": "boa"
    }
