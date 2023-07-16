# Installation and Start
## Linux

Create a shithead directory on your machine:
```
$ cd ~/my_path
$ mkdir shithead
```
Copy the executable to this directory:
```
$ cp masters-of-shithead/bin/shithead ~/my_path/shithead/.
```
and make sure it can be executed:
```
$ chmod ugo+x ~/my_path/shithead/shithead
```
If you want to create a desktop shortcut (Ubuntu), also copy the desktop-file and the icon to this directory:
```
$ cp masters-of-shithead/src/shithead.desktop ~/my_path/shithead/.
$ cp masters-of-shithead/src/shithead/shithead4.ico ~/my_path/shithead/.
```
Start the game from the command line (with the console to check the log and error messages):
```
$ ~/my_path/shithead/shithead
```
To create a desktop shortcut edit shithead.desktop and enter the full path ('~' is not expanded) for executable and icon:
```
$ vi ~/my_path/shithead/shithead.desktop
[Desktop Entry]
...
Exec=/home/my_user/my_path/shithead/shithead
Path=
Icon=/home/my_user/my_path/shithead/shithead4.ico
...
```
Copy shithead.desktop to the desktop:
```
$ cp ~/my_path/shithead/shithead.desktop ~/Desktop/.
```
and make sure it is executable:

$ chmod ugo+x ~/Desktop/shithead.desktop

Now you should see the 'Shithead' icon on the desktop:
```
[right mouse click] on the icon
Select 'Allow Launching'
```
Now you should be able to start the shithead game with a double click on the icon. Note, that this comes with the disadvantage, of not having a console to show errors and log messages.

## Windows

Create a shithead folder on your machine (e.g. 'D:\Games\Shithead)

Copy shithead.exe to this folder.

Start the game from the command prompt:
```
Press [Windows-Key] + [X]
[Run] cmd.exe [OK]
```
In the command prompt enter:
```
C:\Users\my_user>D:\Games\Shithead\shithead.exe
```
To create a desktop shortcut:
```
[right mouse click] on desktop
[New] -> [Shortcut] Location: 'D:\Games\Shithead\shithead.exe' [Next]
Name: 'Shithead' -> [Finish]
```
Now the icon should appear on the desktop (it's already included in shithead.exe) and the game can be started with a double click.
This opens a console, where errors and log messages are displayed, but unfortunately Windows cannot display all of the used unicode characters (♢, ♡ ,↻, ↺).

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
Configuration files are stored at the location of the executable (e.g. '~/my_path/shithead/.)

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
- **Degugging**: Logs the whole game state in JSON format. Not very readable, but can be used to reconstruct a game state for debugging.

**LogFile**
- **No**: Doesn't log to a file.
- **Yes**: Logs to a file, using the specified log level.
- **Dbg**: Logs to a file, using the log level 'Debugging'. This allows for having readable console output simultaneously with debugging info recording for game state reconstruction.

**FileName**
Name of the log file. Log files are stored at the executable's location (e.g. '~\my_path\shithead\.).Note, that an old log with same name will be overwritten.

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
After the last player with cards has been announced the Shithead, a mouse click brings you to the result screen. The ranking in the result table is done with the number of times a player has been shithead, with the current shithead marked in red. There's also a score calculated by adding the number of remaining players at the time a player gets rid of his last card. These numbers are stored in the configuration file, i.e. they are carried over to later games with the same configuration.  
From here you can click **'NEXT GAME'** to play another round, or **'EXIT GAME'** to do exactly that.


# Known Bugs

## Linux

None

## Windows

- ♢, ♡ ,↻, and ↺ are not displayed in the console.
- Text quality of game messages is poor and ↺ is barely recognizable.
- The 'EXIT GAME' button doesn't work (just close the window).




