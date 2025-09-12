from models import speech_to_text, text_to_speech
from utils import Base_llm, generate_1_res_prompt
import json

Audio_file = "farmer_response.mp3"

def get_response():
    Document = speech_to_text(Audio_file)
    LLM_chain = generate_1_res_prompt | Base_llm
    
    response = LLM_chain.invoke({
        "transcript": Document.page_content,
        "language": Document.metadata['language']
    })

    response_text = response.content 
    final_response_json = json.loads(response_text)

    audio = text_to_speech(final_response_json["response"])
    if audio:
        output_path = "response.mp3"
        with open(output_path, "wb") as f:
            f.write(audio)

if __name__ == "__main__":
    get_response()
