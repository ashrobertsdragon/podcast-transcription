import os
import subprocess
import sys

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

def define_folders(base_name: str, folder_type: str) -> tuple[str, str]:
  base_folder = os.path.join("downloads", base_name)
  os.makedirs(base_folder, exist_ok=True)
  segment_folder = os.path.join(base_folder, folder_type)
  os.makedirs(segment_folder, exist_ok=True)
  return base_folder, segment_folder

def count_files(folder_path: str) -> int:
  if not os.path.isdir(folder_path):
    print(f"The path {folder_path} is not a valid directory.")
    return 0
  files = [entry for entry in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, entry))]
  file_count = len(files)
  return file_count


def split_file(file_path: str) -> tuple[str, str]:
  ffmpeg_path = os.getenv("ffmpeg_path")
  _, filename = os.path.split(file_path)
  base_name, extension = os.path.splitext(filename)
  _, output_folder = define_folders(base_name, "audio")
  output_file = os.path.join(output_folder, f"{base_name}%03d{extension}")

  ffmpeg_command = [
    ffmpeg_path, "-i", file_path, "-f", "segment", "-segment_time", "300",
    "-c", "copy", output_file
  ]

  try:
    subprocess.run(
      ffmpeg_command, 
      check=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE
    )
  except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}")
    with open("ffmpeg_error.txt", "w") as f_err:
      f_err.write(e.stderr.decode("utf-8"))

  return base_name, extension

def whisper_api(base_name: str, extension: str):
  base_folder, segment_folder = define_folders(base_name, folder_type = "audio")
  output_folder = os.path.join(base_folder, "transcripts")
  os.makedirs(output_folder, exist_ok=True)
  if count_files(segment_folder) == count_files(output_folder):
    return
  for i, segment in enumerate(os.listdir(segment_folder)):
    if not segment.endswith(extension):
      continue
    segment_path = os.path.join(segment_folder, segment)

    transcript = None
    try:
      with open(segment_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
          model="whisper-1", file=audio_file
        )
        print(f"Segment {i+1} of {len(os.listdir(segment_folder))} transcribed for {base_name}")
    except Exception as e:
      print(e)
    if transcript:
      output_path = os.path.join(output_folder, f"{segment}.txt")
      with open(output_path, "w") as f:
        f.write(transcript.text)

def summarize_transcript(base_name: str):
  base_folder, segment_folder = define_folders(base_name, folder_type = "transcripts")
  for i, text_file in enumerate(os.listdir(segment_folder)):
    if not text_file.endswith(".txt"):
      continue
    summary = ""
    text_path = os.path.join(segment_folder, text_file)
    print(f"Summarizing segment {i+1} of {len(os.listdir(segment_folder))} of {base_name}")
    
    with open(text_path, "r") as f:
      text = f.read()
    response = None
    response = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
        {"role": "system", "content": (
          "You are a chatbot that answers questions. "
          "Please provide an in-depth summary of the following transcript"
        )},
        {"role": "user", "content": f"{text}"}
      ],
      temperature=0.7,
      max_tokens=500,
    )
    if response and response.choices[0].message.content:
      summary = response.choices[0].message.content + "\n"
      with open(os.path.join(base_folder, "summary.txt"), "a") as f:
        f.write(summary)

def get_file_from_input():
  accepted_formats = [
    "flac", "m4a", "mp3", "mp4", "mpeg",
    "mpga", "oga", "ogg", "wav", "webm"
  ]
  input_folder = "downloads"

  valid_files = [
    os.path.join(input_folder, f) for f in os.listdir(input_folder)
    if os.path.splitext(f)[1][1:] in accepted_formats
  ]

  if not valid_files:
    print("No valid files found in the 'input' folder.")
    return None
  elif len(valid_files) == 1:
    return os.path.join(input_folder, valid_files[0])
  else:
    print("Multiple files found. Please select a file:")
  for i, file in enumerate(valid_files, start=1):
    print(f"{i}. {file}")
  while True:
    choice = input("Enter the number of the file to transcribe or A for all: ")
    if choice.upper() == "A":
      return valid_files
    
    elif 1 <= int(choice) <= len(valid_files):
      return valid_files[int(choice) - 1]
    else:
      print("Invalid selection. Please enter a number from the list.")

def sanitize_filename(filename: str) -> str:
  dir_path, file = os.path.split(filename)
  sanitized_filename = "".join(char if char.isalnum() or char in " ._" else "_" for char in file)
  sanitized_file_path = os.path.join(dir_path, sanitized_filename)
  os.rename(filename, sanitized_file_path)
  return sanitized_file_path

def process_files():
  file_path = get_file_from_input()

  if not file_path:
    print("no files found. Exiting")
    sys.exit(1)
  if isinstance(file_path, list):
    for file in file_path:
      file = sanitize_filename(file)
      base_name, extension = split_file(file)
      whisper_api(base_name, extension)
      summarize_transcript(base_name)
  else:
    base_name, extension = split_file(file_path)
    whisper_api(base_name, extension)
    summarize_transcript(base_name)
    