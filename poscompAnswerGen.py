import pandas as pd
import time
from PIL import Image
from google import genai
from google.genai import errors
from pydantic import BaseModel, Field
from google.colab import userdata
import re

client = genai.Client(api_key=userdata.get('GOOGLE_API_KEY'))

# Simplified structure: we only need what we don't already have
class QuestionAnalysis(BaseModel):
    topic: str = Field(description="The exact topic name from the allowed list.")
    explanation: str = Field(description="Step-by-step explanation of how to arrive at the provided correct answer. Use standard LaTeX enclosed in $ or $$ for math formulas.")

df = pd.read_csv("questions.csv")
allowed_topics = "Álgebra Linear, Análise Combinatória, Cálculo Diferencial e Integral, Geometria Analítica, Lógica Matemática, Matemática Discreta, Probabilidade e Estatística, Análise de Algoritmos, Algoritmos e Estrutura de Dados, Arquitetura e Organização de Computadores, Circuitos Digitais, Linguagens de Programação, Linguagens Formais, Autômatos e Computabilidade, Organização de Arquivos e Dados, Sistemas Operacionais, Técnicas de Programação, Teoria dos Grafos, Banco de Dados, Compiladores, Computação Gráfica, Engenharia de Software, Inteligência Artificial, Processamento de Imagens, Redes de Computadores, Sistemas Distribuídos."  # Update with your full list

for index, row in df.iterrows():
    if pd.notna(row.get('explanation')) and str(row.get('explanation')).strip() != "" and row.get('explanation') != "Explanation generation failed.":
        print(f"Skipping {row['Questao']}")
        continue

    image_path = f"images/{row['Ano']}/{row['Ano']}q{int(row['Questao']):02d}.png"
    img = Image.open(image_path)

    # Extract the known answer from your CSV
    known_answer = row['Resposta']

    # Inject the answer directly into the prompt instructions
    prompt = f"""
    Analyze this exam question image. The correct answer is known to be: {known_answer}.

    1. Categorize the question into EXACTLY one of these topics: {allowed_topics}
    2. Provide a clear, step-by-step explanation of how to arrive at {known_answer}. If it's '*', that means the question was cancelled, so, in that case, explain why it was cancelled and the correct answer.
       If you use mathematical notation, fractions, or symbols, wrap them in standard LaTeX (e.g., $x^2$ or $$\\frac{{a}}{{b}}$$).
    """

    while True:
        try:
            print("Prompting LLM...")
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=[img, prompt],
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': QuestionAnalysis,
                },
            )
            res_data = response.parsed

            df.at[index, 'Componente'] = res_data.topic
            df.at[index, 'explanation'] = res_data.explanation

            print(f"Processed {image_path}: {res_data.topic}")
            df.to_csv("questions.csv", index=False)
            print("Sleeping for 3 secs to not exceed RPM")
            time.sleep(3)
            break # Success! Break out of the while loop to move to the next question

        except errors.APIError as e:
            if e.code == 429:
                # Parse the retryDelay using regex (e.g., extracts "31.116" from "'retryDelay': '31.116s'")
                delay = 10 # Default fallback in case parsing fails
                match = re.search(r"'retryDelay':\s*'([0-9.]+)s'", str(e))
                if match:
                    delay = float(match.group(1))

                print(f"Rate limited. Waiting {delay:.2f} seconds before retrying...\n {e}")
                time.sleep(delay + 1) # Add a 1-second buffer to ensure the quota resets
            else:
                print(f"Failed on {image_path} with API error: {e}")
                df.at[index, 'explanation'] = "Explanation generation failed."
                break # It's a different API error, break the retry loop

        except Exception as e:
            print(f"Failed on {image_path}: {e}")
            df.at[index, 'explanation'] = "Explanation generation failed."
            break # It's a local code/network error, break the retry loop

# Save everything to JSON for your frontend
df.to_csv("questions.csv", index=False)
df.to_json("questions.json", orient="records", indent=2)
