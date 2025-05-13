import librosa
from openai import OpenAI
import sounddevice as sd
import nltk
from nltk.corpus import words

# Ensure that the NLTK word list is downloaded
nltk.download('words')

# Get the list of English words (using NLTK's word corpus)
english_words = set(words.words())



def generate_speech(text, openai_api_key, output_file="output_speech.mp3", model="tts-1", voice="alloy"):
    """
    Converts text to speech using OpenAI's TTS API and saves it to a file.

    Parameters:
        text (str): The text to be converted to speech.
        output_file (str): Path to save the output audio file.
        model (str): The TTS model to use (default: "tts-1").
        voice (str): The voice to use for speech synthesis (default: "alloy").
    """
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_api_key)

        # Create speech from text
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
        )

        # Stream the response to the specified output file
        response.stream_to_file(output_file)
        print(f"Speech successfully saved to {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")


def play_audio(file_path):
    """
    Plays an audio file using librosa for loading and sounddevice for playback.

    Parameters:
        file_path (str): The path to the audio file to be played.
    """
    try:
        # Load the audio file
        audio_data, sample_rate = librosa.load(file_path, sr=None)  # sr=None preserves original sample rate
        
        # Play the audio
        print("Playing audio...")
        sd.play(audio_data, samplerate=sample_rate)
        sd.wait()  # Wait until the audio finishes playing
        print("Audio playback finished.")
    except Exception as e:
        print(f"An error occurred during playback: {e}")

def rephrase_text(api_key, text_to_rephrase):
    """
    Rephrases the input text using OpenAI's GPT-4 model.

    Parameters:
        api_key (str): Your OpenAI API key.
        text_to_rephrase (str): The text to be rephrased.

    Returns:
        str: The rephrased text.
    """
    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model= "gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an assistant that specializes in rephrasing text in a playful and friendly way, while retaining its original meaning."},
                {"role": "user", "content": f"Please rephrase the following text:\n{text_to_rephrase}"},
                # {"role": "assistant", "content": f"the rephrased text is: "}
            ],
            temperature=1
        )

        # Extract the rephrased text from the response
        rephrased_text = response.choices[0].message.content.strip()
        # print(rephrased_text)
        return rephrased_text

    except Exception as e:
        print(f"An error occurred {e}")




def light_tagger(text):
    # Split the sentence into words
    words_in_sentence = text.split()
    
    # List to hold the word and language pairs
    word_language_tags = []

    # Process each word in the sentence
    for word in words_in_sentence:
        # Clean the word: remove punctuation and convert to lowercase
        word_clean = word.lower().strip(".,!?")  # Remove common punctuation marks and lowercase the word
        
        # Check if the word is in the English dictionary
        if word_clean in english_words:
            word_language_tags.append((word, 'en'))  # English
        else:
            word_language_tags.append((word, 'yo'))  # Yoruba (if not found in English)

    return word_language_tags

# Function to convert a list of tuples into a list of dictionaries
def tag(data):
    return [{"word": word, "language": language} for word, language in data]

# Function to convert a list of dictionaries back into a list of tuples
def reverse_tag(data):
    return [(entry["word"], entry["language"]) for entry in data]