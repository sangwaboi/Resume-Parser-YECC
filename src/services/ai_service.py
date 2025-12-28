import json
import time
import re
import google.generativeai as genai
from openai import OpenAI
from src.config import config
class AIService:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.9,
                "max_output_tokens": 4000,
            }
        )
        self.grok_client = None
        if config.GROK_API_KEY:
            self.grok_client = OpenAI(
                api_key=config.GROK_API_KEY,
                base_url=config.GROK_API_BASE
            )
    def call_gemini(self, prompt, retry_count=0):
        try:
            response = self.gemini_model.generate_content(prompt)
            if not response.text:
                raise Exception("Empty response from Gemini")
            return response.text.strip()
        except Exception as e:
            if retry_count < 2:
                print(f"   Retry {retry_count + 1}/3...")
                time.sleep(1)
                return self.call_gemini(prompt, retry_count + 1)
            raise
    def call_grok(self, prompt, system_instruction="", retry_count=0):
        if not self.grok_client:
            raise Exception("Grok API not configured")
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            response = self.grok_client.chat.completions.create(
                model=config.GROK_MODEL,
                messages=messages,
                temperature=0.1,
                max_tokens=4000
            )
            if not response.choices or not response.choices[0].message.content:
                raise Exception("Empty response from Grok")
            return response.choices[0].message.content.strip()
        except Exception as e:
            if retry_count < 2:
                print(f"   Retry {retry_count + 1}/3...")
                time.sleep(1)
                return self.call_grok(prompt, system_instruction, retry_count + 1)
            raise
    @staticmethod
    def parse_json_response(content):
        if not content or not content.strip():
            raise json.JSONDecodeError("Empty content", "", 0)
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
        content = content.strip()
        start = content.find('{')
        end = content.rfind('}')
        if start == -1 or end == -1 or end <= start:
            raise json.JSONDecodeError("No JSON found", content, 0)
        json_str = content[start:end+1]
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
        if open_brackets > close_brackets:
            json_str += ']' * (open_brackets - close_brackets)
        return json.loads(json_str)
ai_service = AIService()
