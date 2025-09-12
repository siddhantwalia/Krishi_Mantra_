import os
from groq import Groq
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
client = Groq()

audio_file_path = "1_test.mp3"

def transcribe_multilingual(file_path: str, model="whisper-large-v3"):
    with open(file_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            file=f,
            model=model,
            response_format="verbose_json",
        )
    return resp

resp = transcribe_multilingual(audio_file_path)

# print("Detected Language:", resp["language"])
print(resp)
# doc = Document(
#     page_content=resp["text"],
#     metadata={"language": resp["language"], "source": "audio"}
# )

# def translate_to_english(file_path: str, model="whisper-large-v3"):
#     with open(file_path, "rb") as f:
#         resp = client.audio.translations.create(
#             file=f,
#             model=model,
#             response_format="verbose_json",
#         )
#     return resp

# resp = translate_to_english(audio_file_path)
# print("English Translation:", resp["text"])

# prompt = PromptTemplate(
#     input_variables=["transcript", "language"],
#     template="The farmer spoke in {language}. Transcript:\n{transcript}\n\nAnswer in the same language."
# )

# llm = ChatGroq(model="deepseek-r1-distill-llama-70b", temperature=0.3)
# chain = LLMChain(llm=llm, prompt=prompt)

# answer = chain.run({
#     "transcript": doc.page_content,
#     "language": doc.metadata["language"]
# })
# print(answer)
