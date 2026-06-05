import random
import os
from elevenlabs.client import ElevenLabs
from secrets import API_KEY

goth_id = "bnJkjXM3OhHlifSujPxu"
batman_id = "5TRyo5dDe1hMz5KEeXhW"

name = ""


batman_voicelines = {
    "place": [
        "Another shadow falls exactly where I need it.",
        "Securing this perimeter.",
        "Every move is calculated.",
        "The trap is set."
    ],
    "remove": [
        "Your mistake just cost you this ground.",
        "You're careless.",
        "One less threat to deal with.",
        "That asset has been neutralized."
    ],
    "lose_piece": [
        "A temporary setback; the night is far from over.",
        "I can adapt to this.",
        "You're pushing your luck.",
        "A calculated sacrifice."
    ],
    "think": [
        "Analyzing your tactical patterns... you're predictable.",
        "There's always a weakness.",
        "I'm looking at every possible outcome.",
        "Quiet. I need to map this out."
    ],
    "win": [
        "Justice prevails, and the board is secure.",
        "This city is under my protection. You lose.",
        "It's over. You had no chance.",
        "The night belongs to me."
    ],
    "lose": [
        "I will learn from this defeat... this isn't over.",
        "This isn't the end of the night.",
        "You fought well, but I will return.",
        "An unexpected outcome. Back to the cave."
    ]
}

goth_lady_voicelines = {
    "place": [
        "Setting the stage for a beautifully dark conclusion.",
        "A little piece of darkness, just for you.",
        "Let's put this right where it hurts.",
        "Placing a shadow in your light."
    ],
    "remove": [
        "And just like that, your little friend vanishes.",
        "Poof. Gone. Like all your hopes.",
        "I've always enjoyed a good execution.",
        "Say goodbye to your little toy."
    ],
    "lose_piece": [
        "Slightly annoying, but I always did love a tragic twist.",
        "Oh, did you think that hurt me?",
        "How painfully predictable of you.",
        "A minor tragedy. How poetic."
    ],
    "think": [
        "Just pondering the sheer futility of your next move.",
        "So many ways to destroy you... which to choose?",
        "Don't rush me, the existential dread is setting in nicely.",
        "Staring into the abyss takes time."
    ],
    "win": [
        "A flawless victory, wrapped in absolute despair.",
        "The darkness always wins in the end.",
        "Beautifully brutal. Just how I like it.",
        "You look so exquisite in defeat."
    ],
    "lose": [
        "Losing has its own melancholy charm, I suppose.",
        "A tragic ending. Delightful.",
        "You won, but the void remains.",
        "Whatever. Winning is mainstream anyway."
    ]
}


def generate_wav_from_text(text: str, output_dir: str, filename: str,  voice_id: str, api_key: str = None) -> str:
    """
    Generates a WAV audio file using the updated ElevenLabs SDK layout.
    """
    # Initialize the client correctly
    client = ElevenLabs(api_key=API_KEY)

    # Setup directory and path validation
    os.makedirs(output_dir, exist_ok=True)
    if not filename.endswith('.wav'):
        filename = f"{os.path.splitext(filename)[0]}.wav"
    full_output_path = os.path.join(output_dir, filename)

    print(f"Generating audio for text...")

    # FIX: Use client.text_to_speech.convert instead of client.generate
    # Note parameter changes: voice_id and model_id
    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
    )

    # Consolidate the generator chunks into a single bytes object
    audio_bytes = b"".join(audio_generator)

    # Save the bytes to disk
    with open(full_output_path, "wb") as f:
        f.write(audio_bytes)

    print(f"Success! File saved to: {full_output_path}")
    return os.path.abspath(full_output_path)


if __name__ == "__main__":
    # Example usage
    voice_id = goth_id  # or batman_id
    for mood in goth_lady_voicelines:
        for line in goth_lady_voicelines[mood]:
            text_to_convert = line
            output_filename = f"{mood}_{line.replace(' ', '_').lower()[:10]}.wav"
            if voice_id == goth_id:
                name = "goth"
            elif voice_id == batman_id:
                name = "batman"
            output_directory = f"output/{name}"
            generate_wav_from_text(
                text_to_convert, output_directory, output_filename, voice_id)
