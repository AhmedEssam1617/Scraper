# Google Maps Restaurant Scraper

This script scrapes restaurant information from Google Maps, including names, phone numbers, and websites.

## Features

- Scrapes restaurants for multiple cities (defined in german_cities.txt)
- Extracts restaurant names, phone numbers, and websites
- Saves data to CSV files
- Works with Arabic Google Maps interface
- Designed to run on GitHub Codespaces

## Prerequisites

- Python 3.7+
- Chrome browser
- The necessary Python packages (see requirements.txt)

## Setup Instructions for GitHub Codespaces

1. Create a GitHub Codespace from your repository
2. The Codespace will automatically install dependencies from requirements.txt
3. You'll need to install Chrome in the Codespace:

```bash
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt update
sudo apt install -y ./google-chrome-stable_current_amd64.deb
```

## Running the Scraper

```bash
python Scrapper.py
```

This will:
1. Read city names from german_cities.txt
2. For each city, search for restaurants on Google Maps (in Arabic interface)
3. Scrape information for all found restaurants
4. Save the data to CSV files named `restaurants_CITYNAME.csv`

## Adding More Cities

Edit the `german_cities.txt` file to add more cities, one per line.

## Troubleshooting

If you encounter issues:

1. Make sure Chrome is installed in the Codespace
2. Ensure your internet connection is stable
3. Check that you have proper permissions to install packages
4. Increase timeouts if the script fails due to slow loading

## License

This project is for educational purposes only. Use responsibly and in accordance with Google's terms of service. 