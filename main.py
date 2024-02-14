from get_podcast import podcast
from transcribe import process_files

def main():
  podcast_url = input("Enter URL for podcast feed > ")
  podcast(podcast_url)
  process_files()

if __name__ == "__main__":
  main()