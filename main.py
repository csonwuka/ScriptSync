import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI

openai_api_key = st.secrets['OPENAI_API_KEY']


def save_user_file():
    user_file = st.file_uploader("Upload the video that you want to translate.\nSupported video extensions "
                                 "include: 'mp4', 'avi', 'mov', 'webm', 'mkv', 'wmv' only.\nFile size should not "
                                 "exceed 200mb.", type=["mp4", "avi", "mov", "webm", "mkv", "wmv"],
                                 key="video_file")
    if user_file:
        with open(user_file.name, mode='wb') as f:
            f.write(user_file.getvalue())
    else:
        st.info(f'No file has been uploaded. Please upload a file!')
        st.stop()

    return user_file.name


def get_audio_file(video_file):
    video_clip = VideoFileClip(video_file)
    audio_path = "sample_audio.mp3"
    video_clip.audio.write_audiofile(audio_path)
    return audio_path


def transcribe_video(api_key, audio_file_path):
    client = OpenAI(api_key=api_key)
    audio_file = open(audio_file_path, "rb")
    transcriptions = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
        language="en",
        timestamp_granularities=["segment"]
    )
    return transcriptions


def translate_video(api_key, audio_file_path):
    client = OpenAI(api_key=api_key)
    audio_file = open(audio_file_path, "rb")
    translations = client.audio.translations.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json"
    )
    return translations


def translate_to_fr(api_key, en_word):
    client = OpenAI(api_key=api_key)
    prompt = f"Translate the following English word to French: '{en_word}'. Only return the exact translation of {en_word}. Nothing more"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that translates English words to French."},
            {"role": "user", "content": prompt}
        ]
    )
    # Extract the translation from the response
    translation = response.choices[0].message.content
    return translation


def seconds_to_vtt_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{int(seconds):02}.{milliseconds:03}"


def json_to_vtt(transcription_segments, vtt_file, translation_format):
    with open(vtt_file, 'w') as f:
        f.write("WEBVTT\n\n")

        for subtitle in transcription_segments:
            start_timestamp = seconds_to_vtt_timestamp(subtitle['start'])
            end_timestamp = seconds_to_vtt_timestamp(subtitle['end'])
            f.write(f"{subtitle['id']}\n")
            f.write(f"{start_timestamp} --> {end_timestamp}\n")
            if translation_format == "French to English":
                f.write(f"{subtitle['text']}\n\n")
            elif translation_format == "English to French":
                fr_text = translate_to_fr(api_key=openai_api_key, en_word=subtitle['text'])
                f.write(f"{fr_text}\n\n")


# STREAMLIT UI
def run_app():
    st.set_page_config(page_title="Video Subtitle generator and translator", layout="wide")
    st.title("Welcome To Script Sync! 🤖")

    with st.sidebar:
        st.header("CHOOSE YOUR PREFERENCES")
        video_filename = save_user_file()
        translation_option = st.selectbox(
            'What translation do you want to do?',
            ("English to French", "French to English")
        )
        generate_sub_btn = st.button("Display video and subtitle")

    if generate_sub_btn:
        video_file = st.session_state['video_file']

        with st.spinner("Loading video and generating subtitle..."):
            audio_filepath = get_audio_file(video_file=video_filename)
            if translation_option == "French to English":
                transcript = transcribe_video(api_key=openai_api_key, audio_file_path=audio_filepath)
            else:
                transcript = translate_video(api_key=openai_api_key, audio_file_path=audio_filepath)

            json_to_vtt(
                transcription_segments=transcript.segments,
                vtt_file='subtitles.vtt',
                translation_format=translation_option)
            st.video(data=video_file, format="video/mp4", subtitles="subtitles.vtt")
            st.success("Subtitles generated successfully! Enjoy your movie!")

            with open("subtitles.vtt") as sub_file:
                st.download_button(label="Download subtitle", data=sub_file, file_name="subtitles.vtt'")


if __name__ == "__main__":
    run_app()
