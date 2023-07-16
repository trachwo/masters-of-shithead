# Introduction
Play a game of **Shithead** against 1 to 5 AI players using the arcade library.  
Shithead is a **UNO** (**Mau Mau**, **Tschau Sepp**) type of card game, where each player tries to get rid of his cards as fast as possible.  
There's no winner, but the last player with cards is declared **Shithead** and has to deal for the next round.
# Installation

## Python

Install Python3 (PIP is included by default in version 3.4 or higher):  
-> <https://realpython.com/installing-python/>

## 

## Install the masters-of-shithead Package locally

Download the masters-of-shithead folder to a convenient place on your machine.

### Linux

Create (only the 1st time) and activate a virtual environment in the masters-of-shithead directory:
```
$ cd ~/my-path/masters-of-shithead
$ python3 -m venv venv --prompt="shithead"
$ source venv/bin/activate
(shithead) $
```
Install the arcade and the setuptools packages:
```
(shithead) $ pip install arcade
(shithead) $ pip install setuptools
```
Install the masters-of-shithead package locally:
```
(shithead) $ cd ~/my-path/masters-of-shithead
(shithead) $ python -m pip install -e .
```
Now the shithead game can be started from everywhere:
```
(shithead) $ cd
(shithead) $ shithead -h
usage: shithead [-h] [-g | -t | -c | -d DEBUGGING | -r RULES] [-f FILENAME]
...
```
**Note**, that configuration- and log-files are stored in the directory, where you started the program.

To deactivate the virtual environment:
```
(shithead) $ deactivate
$
```

### Windows
Open a windows command-line shell:
```
[Windows-Key] + [X]
[Run] cmd.exe [OK]
C:\Users\my-user\>
```
Get the path to the Python executable:
```
C:\Users\my-user\> where.exe python
C:\Users\my-user\AppData\Local\Programs\Python\Python310\python.exe
```
Create (only the 1st time) and activate a virtual environment in the masters-of-shithead folder:
```
C:\Users\my-user\> cd my_path\masters-of-shithead
C:\...\masters-of-shithead\> C:\Users\my_user\AppData\Local\Programs\Python\Python310\python -m venv venv --prompt="shithead"
C:\...\masters-of-shithead\> venv\Scripts\activate
(shithead) C:\...\masters-of-shithead\>
```
Install the arcade and the setuptools packages:
```
(shithead) C:\...\masters-of-shithead\> pip install arcade
(shithead) C:\...\masters-of-shithead\> pip install setuptools
```
Install the masters-of-shithead package locally:
```
(shithead) C:\...\masters-of-shithead\> cd ~/my-path/masters-of-shithead
(shithead) C:\...\masters-of-shithead\> python -m pip install -e .
```
Now the shithead game can be started from everywhere:
```
(shithead) C:\...\masters-of-shithead\> cd C:\Users\my-user
(shithead) C:\Users\my-user\> shithead -h
usage: shithead [-h] [-g | -t | -c | -d DEBUGGING | -r RULES] [-f FILENAME]
...
```
**Note**, that configuration- and log-files are stored in the directory, where you started the program.

To deactivate the virtual environment:
```
(shithead) C:\Users\my-user\> deactivate
C:\Users\my-user\>
```
# Start

First activate the virtual environment with:
```
$ cd ~/my-path/masters-of-shithead
$ source venv/bin/activate
```
or
```
C:\Users\my-user\> cd my-path\masters-of-shithead
C:\Users\my-user\my-path\masters-of-shithead\> venv\Scripts\activate
```
## Commands

To play a game against 1 to 5 AI opponents in the GUI:
```
(shithead) $ shithead
```
To play a game using the command line interface:
```
(shithead) $ shithead -c
```
To generate a new face up table for AI card swapping:
```
(shithead) $ shithead -g
```
To start a GUI game from a game state recorded with log-level 'Debugging':
```
(shithead) $ shithead -d STATE -f CONFIG
```
Where STATE is a JSON-file containing the game state and CONFIG is a JSON-file containing the configuration used for the recorded game.

To start an AI test game (with hardcoded configuration):
```
(shithead) $ shithead -t
```

# Play the Game

## Start

A green window should open and after a short animated sequence, you are presented with 3 buttons:

**RULES**  
Opens a separate window with English shithead rules.

**REGELN**  
Opens a separate window with German shithead rules.

**CONTINUE**  
Changes to the configuration view.

## Configuration

**ConfigFile**  
If you have played the game before, you can enter the name of the configuration file and press the 'LOAD' button. This will load the players (including their scores) and all other configuration parameters.  
Or you can enter a name to store a new configuration.
Configuration files are stored in the directory from where we started the game.

**Players**  
*Player0* is always the human player.  
*Player1-Player5* are AI players.  
*Player1* must alway be in the game (minimum of 2 players).  
*Player2-Player5* can be added for a 3 to 6 player game, by selecting an AI-Type.  
Player names can be entered into the corresponding fields.

**AI-Types**  
1. **ShitHappens**:
	- Randomly selects one of the possible plays.
2. **CheapShit**:
	- Plays the less valid cards ('4', '5', '6',...) first.
3. **TakeShit**:
	- Plays the less valid cards ('4', '5', '6',...) first.
	- Voluntarily takes the discard pile if it contains good cards.
	- Plays '3' before '2' on 'A', 'K', or '7' ('Druck mache!').
4. **DeepShit**:
	- Plays the less valid cards ('4', '5', '6',...) first.
	- Voluntarily takes the discard pile if it contains good cards.
	- Plays '3' before '2' on 'A', 'K', or '7' ('Druck mache!').
	- Uses simulation to find the best play when in the end game (only 2 players left and talon empty).
5. **BullShit**:
	- Uses statistics to find the best play and therefore plays very bad.


**FastPlay**
- **No**: Game waits for mouse click after each AI player turn.
- **Yes**: Game continues automatically.

**LogLevel**
- **One Line**: Logs one line per per play (turn, direction, talon, player, play, discard pile). Provides the best possibility to trace back, if you missed an opponent's play (unfortunately, microsoft doesn't know the unicodes for ♢, ♡ ,↻, and ↺).
- **Game Display**: Logs all information visible to the human player (i.e. his own hand but not the other players' hands) as in a game using the CLI instead of the GUI.
- **Perfect Memory**: Logs all information visible to the human player, plus it shows you cards in the opponents' hands, which have been face up once during the game (to level the field against DeepShit and BullShit, which have perfect memory).
- **No Secret**: Discloses all cards in the game. Put in for debugging, but also great for cheaters.
- **Debugging**: Logs the whole game state in JSON format. Not very readable, but can be used to reconstruct a game state for debugging.

**LogFile**
- **No**: Doesn't log to a file.
- **Yes**: Logs to a file, using the specified log level.
- **Dbg**: Logs to a file, using the log level 'Debugging'. This allows for having readable console output simultaneously with debugging info recording for game state reconstruction.

**FileName**
Name of the log file. Log files are stored in the directory from where we started the game. Note, that an old log with same name will be overwritten.

**Buttons**
- **LOAD**: Loads the specified configuration file.
- **START**: Stores the configuration to the specified file and then starts the game.

## Game

**Burning Cards**  
In games with 2, 4, or 5 players some cards are randomly removed from the talon.

**Dealing Cards**  
The dealer (randomly selected for the 1st round or the shithead of the last round) gives each player 3 face down table cards, followed by 3 faceup table cards, and finally 3 hand cards.

**Swapping Cards**  
Starting with the player following the dealer in clockwise direction, each player may exchange any of his face up table cards with a hand card, ending with 3 face up table cards in front of him. The human player's cards are marked with bright green frames, if they can be swapped. Press the 'DONE' button when you are satisfied with your selection.

**Starting Player Auction**  
The player with the lowest card in hand starts the game. Starting with the player following the dealer in clockwise direction, players are asked to show 4♣ 4♠ 4♡ 4♢ 5♣ and so on. If a player can show the requested card, he becomes the starting player. In a game with 2 packs of cards it's possible that 2 players show the requested card, in this case (only) these players continue with the auction until a starting player is found. The human player is asked to click on the requested card, if it's in his hand, or is otherwise skipped (but he also may click on 'DONE' to not show the card).

**Playing Hand Cards**  
Now players play their regular turns until the shithead is found.
Whenever it's your turn, the game marks your options with bright green frames.  
Moving the mouse over a card will give you a short description of actions and special card effects.
- Take the discard pile (if there's a discard pile and it's your 1st action).
- Play one of your hand cards.
- You are forced to refill your hand to 3, as long as there's a talon.
- Kill the discard pile, if there are 4 or more cards of same rank on top.
- End your turn with 'DONE', although you could play more cards of same rank.

**Playing Face Up Table Cards**  
If you have no hand cards left, you have to play your face up table cards.
If none of your face up cards can be played, you have to take the discard pile **and then are ask to also pick up one (or several of same rank) of your face up cards**.

**Playing Face Down Table Cards**  
If you have neither hand nor face up cards left, it's time to play your face down table cards.  
Just pick one blindly and see what happens. If it doesn't match, you get it together with the discard pile on your hand.

**Shithead found**  
After the last player with cards has been declared Shithead, a mouse click brings you to the result screen. The ranking in the result table is done with the number of times a player has been shithead, with the current shithead marked in red. There's also a score calculated by adding the number of remaining players at the time a player gets rid of his last card. These numbers are stored in the configuration file, i.e. they are carried over to later games with the same configuration.  
From here you can click **'NEXT GAME'** to play another round, or **'EXIT GAME'** to do exactly that.

# Files
## Modules
- **shithead.py**:  
  Contains **main()** with argument parser (entry-point).
	- GUI start.
	- CLI game.
	- Face up table generator.
	- AI test.

- **start.py**:  
  Start screen.
	- Title animation.
	- *RULES* button => open window with English rules.
	- *REGELN* button => open window with German rules.
	- *CONTINUE* button => change to configuration screen.

- **config.py**:  
	Configuration screen.
	- Load previous configuration.
	- Add or remove players and select their AI type.
	- Activate or deactivate *fast play*.
	- Configure logging.

- **gui.py**:  
	Actual game screen.
	- Marks the places where cards can go on the screen with dark green mats.
	- Creates a sprite for every card in the game.
	- Creates the *DONE* button.
	- Game loop:
		- Moves card sprites.
		- Updates card counters.
		- Prints game information to the screen.
		- Highlights names of current and next player.
		- Highlights actions available to the human player.
		- Processes input from the human player (mouse movement and clicks).
		- Changes the game state according to the action selected by the current player.

- **result.py**:  
	Result screen with game statistics displayed after shithead was found.
	- *NEXT GAME* button => start the next round.
	- *EXIT GAME* button => exit the game.

- **cards.py**:  
	The classes at the heart of the game.
	- Card => rank, suit, deck ID.
	- Deck => set of 52 cards.

- **discard.py**:  
 	Deck representing the shithead discard pile.

- **player.py**:  
	Class holding the state (name, cards, etc.) of a single player. 
	- Human player => methods for human player to select his next play.
	- AI player => methods for different AI types to select their next play.

- **play.py**:  
	Play selected by the current player.
	- Game action.
	- Card played in this action.

- **state.py**:  
	Representation of a game state.
	- Players, current player, next player.
	- Talon, discard pile.
	- Turn, cards played this turn, game direction.
	- Logging.
	- Creation of alternative states based on known and unknown cards (for simulation).

- **game.py**:  
	Implementation of Shithead rules as state machine (current state + selected play => next state).

- **stats.py**:  
	Game statistics updated after shithead has been found.

- **fup_table.py**:  
	Loads a table with ranked face up table card combinations from a JSON-file to help AI players to find the best combination during card swapping.

- **analyzer.py**:  
	Provides methods for AI players to select a play based on card statistics.

- **rules.py**:  
	Opens a new window to display the game rules loaded from a JSON-file.
	- Different languages (English or German).
	- Different operating systems (size of window, font, etc.)

- **card_writer.py**:  
	Helper program for the creation of title sequence letters.

## Additional Files

- **title.json**:  
	Coordinates and direction of cards in title sequence.

- **face_up_table.json**:  
	Ranking of card combinations used by AI players during card swapping.

- **ms_rules_eng.json**:  
	English shithead rules (Windows).

- **ms_rules_ger.json**:  
	German shithead rules (Windows).

- **rules_eng.json**:  
	English shithead rules (Linux).

- **rules_ger.json**:  
	German shithead rules (Linux).



# Known Bugs

## Linux

None

## Windows

- ♢, ♡ ,↻, and ↺ are not displayed in the console.
- Text quality of game messages is poor and ↺ is barely recognizable.
- The 'EXIT GAME' button doesn't work (just close the window).

