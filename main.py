import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import openai
import json
from typing import Optional
from toolz.functoolz import pipe
import re


# TODO: Monadic error handling (fix error handling in non handled areas (setup_db))
# @st.cache
def setup(secrets: dict) -> tuple[firestore.Client, dict]:
    openai.api_key = json.loads(secrets["openai_key"])['api_key']
    key_dict = json.loads(secrets["db_key"])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
    return firestore.Client(credentials=credentials), json.loads(secrets["prompts"])


def setup_db(secrets: dict) -> firestore.Client:
    key_dict = json.loads(secrets["db_key"])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
    return firestore.Client(credentials=credentials)


def get_request(prompt: str) -> Optional[openai.Completion]:
    try:
        return openai.Completion.create(model="text-davinci-002",
                                        prompt=prompt,
                                        max_tokens=1000,
                                        temperature=0.1,
                                        top_p=1)
    except Exception:
        st.error("Error generating code review. Reload the webpage and try again.")
        return None


def format_response(response: Optional[openai.Completion]) -> str:
    try:
        return response.choices[0].text
    except Exception:
        return ""


def decode_st_code(st_code) -> Optional[str]:
    try:
        return st_code.read().decode("utf-8")
    except UnicodeDecodeError:
        return None


def get_output(prompt: str) -> str:
    return pipe(prompt, get_request, format_response)


@st.cache
def ai_magic(prompt: str, code):
    in_1 = prompt.format(Code=code)[-12000:]
    out_1 = get_output(in_1)
    in_2 = in_1 + out_1 + '\n\nRate the code from 1 to 10:'
    out_2 = get_output(in_2)
    fin = in_2 + out_2
    return out_1, out_2, fin, 0 if len(in_1) < 12000 else 1


@st.cache
def save_prompt(fin: bytes, exceed_len: int):
    database.collection('ai_responses').add({'response': fin, 'exceeded_lenght': exceed_len})


@st.cache
def save_response(fin: bytes, human_response: bytes, human_score: int, exceed_len: int):
    database.collection('responses').add({'ai_response': fin,
                                          'human_evaluation': human_response,
                                          'human_score': human_score,
                                          'exceeded_lenght': exceed_len})


database, prompts = setup(st.secrets)


def main():
    temp = st.empty()
    with temp.container():
        code_uploaded = st.file_uploader(
            "Upload your code file here. (Hint: Long code files might give unexpected results)")
    if code_uploaded:
        code = decode_st_code(code_uploaded)
        if code is None:
            st.error("File type is not supported or encountered an error while decoding. Choose a different file.")
        else:
            st.code(code)
            temp.empty()
            with temp.container():
                st.text('Press F5 to upload a new code file')
                category = st.selectbox("Select a category to review your code in", prompts.keys())
                prompt = prompts[category]
                button = st.button("Generate code review")
            if not st.session_state.get('button'):
                st.session_state['button'] = button
            if st.session_state['button']:
                out_1, out_2, fin, exceed_len = ai_magic(prompt, code)
                encoded_fin = fin.encode('utf-8')
                save_prompt(encoded_fin, exceed_len)
                with temp.form('my_form'):
                    st.text(f'AI rating of the code in terms of {category}')
                    st.text('1:' + out_1 + '\n\nScore:' + out_2)
                    human_response = st.text_area("Do you agree with the AI? What would you change?",
                                                  value='1:' + out_1, height=400)
                    human_score = st.slider("Rate the code from 1 to 10:", 1, 10,
                                            value=int(re.findall(r'\d+', out_2)[0]), step=1)
                    if st.form_submit_button("Submit"):
                        save_response(encoded_fin, human_response.encode('utf-8'), human_score, exceed_len)
                        st.session_state['button'] = False
                        temp.button('Restart')


if __name__ == "__main__":
    main()
