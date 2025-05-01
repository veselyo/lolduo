# TFT Double Up Stats

Double Up is a queue type in Team Fight Tactics (TFT), which is a game from Riot
Games. This game mode can be played alone with a random partner or with any of
your friends. This project uses the Riot Games API to fetch match history of one
player and filter out their Double Up games played together with a selected
friend. This way the user can see how the two players have been doing together
in Double Up as there is no easy way to get this information from Riot in game
or in a different web application. This project took me 20+ hours to complete
as it took me time to learn about the Riot Games API and how to use it, and how
to work in the Windssurf IDE and how to efficiently use Cascade. Sometimes
rather than helping it was frustrating as it made changes and I didn't push my
old version to GitHub and I had trouble getting it back, or sometimes it
generates overcomplicated code that I had to delete or completely change so I
ended up coding a lot from scratch.

## Features

- Look up player Double Up rank across any server 
- Look up two players' match history together in Double Up game mode
- Display most important traits of each player in each match
- Calculate favorite traits for both players across all games played together
- Cooldown protection for updating stats to avoid API rate limits
- Fetch information about matches from the current Set (13) and not beyond

## Setup & Running
API Key:
- Sign up and get your own API key from https://developer.riotgames.com/

First time running the application:
```bash
make        # Installs requirements for the application and runs it
```

Available commands:
```bash
make install   # Install requirements
make run       # Checks if API key is set and runs the server
make test      # Run the test suite
make clean     # Clear cache and any temporary files
make kill      # Force stop the server if needed
```

Note: Press Ctrl+C in the terminal to stop the server normally.

## Usage

- Enter riot ID and choose a server
- Click "Update Data" to fetch fresh stats and wait for the update to complete
- Examples for grading: (characters after # are tags) 
  - Enter BigDrej#yAb and harvardsupp#NA1 on NA server for two players that 
      have games together
  - Enter gibberish in the input fields and click "Update Data", and message
      will be displayed saying player does not exist
  - Enter yAbVezzy#EUW and OttoFerocity#4896 on EUW server for two players that 
      have games together on a different server
  - Enter NZXK#NA1 and BigDrej#yAb on NA server for two players that do not have
      games together and one player has no games at all

## Contributors

- Ondrej Vesely - Project Developer


## Screenshot
![TFT Double Up Stats Dashboard](images/hw1.png)
