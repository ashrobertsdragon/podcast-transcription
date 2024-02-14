import json
import os
import xml.etree.ElementTree as ET

import requests


def fetch_podcast_feed(url):
  try:
    response = requests.get(url)
    response.raise_for_status()
    return response.text
  except requests.exceptions.RequestException as e:
    print(f"Error fetching podcast feed: {e}")
    return None

def parse_rss_feed(feed_xml):
  root = ET.fromstring(feed_xml)
  episodes = []

  for item in root.findall("./channel/item"):
    episode = {
      "title": item.find("title").text,
      "description": item.find("description").text,
      "audio_url": item.find("enclosure").attrib["url"],
      "pub_date": item.find("pubDate").text
    }
    episodes.append(episode)

  return episodes

def store_episodes_as_json(episodes, file_name="episodes.json"):
  with open(file_name, "w") as json_file:
    json.dump(episodes, json_file, indent=2)

def display_episodes_and_prompt_selection(episodes):
  print("\nAvailable Episodes:")
  for idx, episode in enumerate(episodes, start=1):
    print(f"{idx}. {episode["title"]} (Published on {episode["pub_date"]})")

  selected_indices = input("\nEnter the numbers of the episodes you'd like to download, separated by commas (e.g., 1, 3, 5): ")
  selected_indices = [int(idx.strip()) for idx in selected_indices.split(",") if idx.strip().isdigit()]

  # Filter episodes based on selected indices, adjusting for 1-based indexing
  selected_episodes = [episodes[idx-1] for idx in selected_indices if 0 < idx <= len(episodes)]
  return selected_episodes

def download_audio_file(audio_url, file_name):
  safe_file_name = file_name.replace(" ", "_").replace(os.path.sep, "_")
  file_path = os.path.join("downloads", safe_file_name + ".mp3")
  
  try:
    response = requests.get(audio_url)
    response.raise_for_status()  # Check if the request was successful
    with open(file_path, "wb") as audio_file:
      audio_file.write(response.content)
    print(f"Downloaded audio file to {file_path}")
  except requests.exceptions.RequestException as e:
    print(f"Error downloading audio file: {e}")

def podcast(podcast_url):
  feed_xml = fetch_podcast_feed(podcast_url)
  if feed_xml:
    episodes = parse_rss_feed(feed_xml)
    selected_episodes = display_episodes_and_prompt_selection(episodes)
    for episode in selected_episodes:
      download_audio_file(episode["audio_url"], episode["title"])
      print(f"Downloaded {episode['title']}")
    print(f"Downloaded {len(selected_episodes)} selected episodes.")
