import pandas as pd
import time
from PIL import Image, ImageOps
import io
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field
from google.colab import userdata
import re
import json

client = genai.Client(api_key=userdata.get('GOOGLE_API_KEY'))

class QuestionAnalysis(BaseModel):
    topic: str = Field(description="The exact topic name from the allowed list.")
    explanation: str = Field(description="Explicação clara, passo a passo, de como chegar à resposta. Se for '*', explique o motivo do cancelamento e qual seria a resposta correta. Use LaTeX padrão (ex: $x^2$ ou $$\\frac{{a}}{{b}}$$). Layout flexível e limpo.")

df = pd.read_csv("questions.csv")
allowed_topics = "Álgebra Linear, Análise Combinatória, Cálculo Diferencial e Integral, Geometria Analítica, Lógica Matemática, Matemática Discreta, Probabilidade e Estatística, Análise de Algoritmos, Algoritmos e Estrutura de Dados, Arquitetura e Organização de Computadores, Circuitos Digitais, Linguagens de Programação, Linguagens Formais, Autômatos e Computabilidade, Organização de Arquivos e Dados, Sistemas Operacionais, Técnicas de Programação, Teoria dos Grafos, Banco de Dados, Compiladores, Computação Gráfica, Engenharia de Software, Inteligência Artificial, Processamento de Imagens, Redes de Computadores, Sistemas Distribuídos."

for index, row in df.iterrows():
    if pd.notna(row.get('explanation')) and str(row.get('explanation')).strip() != "" and row.get('explanation') != "Explanation generation failed.":
        print(f"Skipping {row['Questao']}")
        continue

    image_path = f"images/{row['Ano']}/{row['Ano']}q{int(row['Questao']):02d}.png"
    
    try:
        with Image.open(image_path) as raw_img:
            sanitized = ImageOps.exif_transpose(raw_img)
            sanitized = sanitized.convert('RGB')
            
            buffer = io.BytesIO()
            sanitized.save(buffer, format="JPEG", quality=95)
            image_bytes = buffer.getvalue() 
            
        img_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
    except Exception as ie:
        print(f"Error preparing image {image_path}: {ie}")
        continue

    known_answer = row['Resposta']

    # The prompt is simplified since Pydantic enforces the JSON structure automatically
    prompt = f"""
    Analise esta imagem de questão de exame. Sabe-se que a resposta correta é: {known_answer}.

    1. Categorize a questão em EXATAMENTE um destes tópicos: {allowed_topics}
    2. Forneça uma explicação didática de como chegar a {known_answer}. Se for resposta dada for '*', isso significa que a questão foi anulada, nesse caso, explique o motivo do cancelamento e qual seria a resposta correta.
        Se você usar notação matemática, frações ou símbolos, envolva-os em LaTeX padrão (ex: $x^2$ ou $$\\frac{{a}}{{b}}$$). Layout flexível e limpo.".
    """

    retry_count = 0
    while True:
        try:
            print(f"Prompting LLM for {image_path}...")
            response = client.models.generate_content(
                model='gemma-4-31b-it',
                contents=[img_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QuestionAnalysis,
                    #max_output_tokens=8192 # Prevents the abrupt cutoff
                )
            )
            
            res_data = response.parsed
            if res_data is None:
                raw_text = response.text
                if not raw_text:
                    # Catch safety blocks or empty outputs
                    raise ValueError("Model returned empty text.")
                
                # Strip Gemma's Markdown formatting
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0]
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0]
                
                
                # Force it into the Pydantic object
                parsed_dict = json.loads(raw_text.strip())
                res_data = QuestionAnalysis(**parsed_dict)
            # ------------------------------

            df.at[index, 'Componente'] = res_data.topic
            df.at[index, 'explanation'] = res_data.explanation

            print(f"Processed {image_path}: {res_data.topic}")
            df.to_csv("questions.csv", index=False)
            print("Sleeping for 3 secs to not exceed RPM")
            time.sleep(3)
            break 

        except errors.APIError as e:
            if e.code == 429:
                delay = 10 
                match = re.search(r"'retryDelay':\s*'([0-9.]+)s'", str(e))
                if match:
                    delay = float(match.group(1))

                print(f"Rate limited. Waiting {delay:.2f} seconds before retrying...\n {e}")
                time.sleep(delay + 1)
            elif e.code == 500:
                retry_count += 1
                # Use a fast 2-second retry on the first 500 error to catch the server waking up
                wait_time = 2 if retry_count == 1 else 10
                print(f"Google Server Error (500) on {image_path}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Failed on {image_path} with API error: {e}")
                df.at[index, 'explanation'] = "Explanation generation failed."
                break
        except json.JSONDecodeError as je:
            print(f"JSON Parse Error on {image_path}. Text returned was: {response.text[:200] if response.text else 'None'}")
            print("Retrying generation for clean JSON layout...")
            time.sleep(5)

        except Exception as e:
            print(f"Failed on {image_path}: {e}")
            df.at[index, 'explanation'] = "Explanation generation failed."
            break 

df.to_csv("questions.csv", index=False)
df.to_json("questions.json", orient="records", indent=2)
print("Finished complete migration pass!")
