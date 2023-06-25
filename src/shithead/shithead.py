"""
Shithead game with gui using arcade library.

The commandline is parsed in main() and a shithead game is started according
to the specified options:
    no option (default)
        Start a default shithead game against 1 - 5 AI players using the gui.

    -d DEBUGGING -f FILENAME
        Start a shithead game from a logged intermediate state using the gui.
        The intermediate state is loaded from the json-file DEBUGGING
        and the configuration is loaded from the json-file FILENAME.

    -c
        Start a shithead game against 1 - 5 AI players using the command line
        interface.

    -t
        Start a series of AI only games to evaluate different AI types.
        Number and types of players are hardcoded in ai_test().

    -g
        Start a series of AI only games with random face up table cards to
        generate a table, which helps the AI players to decide which cards to
        swap at the beginning of the game.

06.10.2022 Wolfgang Trachsler
"""

import arcade
import argparse
from random import randrange
import math
from time import sleep
import json

# local imports (modules in same package)
from .cards import Card
from .game import Game, SWAPPING_CARDS, FIND_STARTER, PLAY_GAME, SHITHEAD_FOUND
from .fup_table import FupTable, FUP_TABLE_FILE, TEXT_FILE
from .state import State
from .play import Play
from .stats import Statistics
from .gui import GameView
from . import discard
from . import start
from . import player as plr # to avoid confusion with 'player' used as variable name
from . import rules

# Screen title and size
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Sh*thead"

#-----------------------------------------------------------------------------
def gui_start():
    """
    Play Shithead against 1..5 AIs using the GUI.

    Opens the game window and makes the title screen the active view.
    It shows us the title of the game in an animated sequence and prints
    additional information like version, credits, etc.
    2 buttons allow us to open additional windows with English and/or German
    rules.
    A 3rd button lets us continue to the configuration screen.
    """
    # open a window with predefined size and title
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

    # create a StartView (Title, version, rules)
    start_view = start.StartView()
    # and make it the view shown in the window
    window.show_view(start_view)

    # sets up the starting view:
    # setups title, version, etc.
    # sets up buttons for english and german rules,
    # and to continue to the config screen.
    start_view.setup()

    # start the game loop,
    # from now on all state changes are controlled in the on_update() method
    # of the current view:
    arcade.run()

def load_state_from_file(config_file, state_file):
    '''
    Start a game from a logged state.

    Loads the game configuration and its current state from JSON-files and
    starts the gui-game from this state.

    :param config_file: name of configuration JSON-file
    :type config_file:  str
    :param state_file:  name of state JSON-file
    :type config_file:  str
    '''
    try:
        # load configuration from json-file
        filename = config_file
        with open(filename, 'r') as json_file:
            config = json.load(json_file)
    except OSError as exception:
        print(f"### Error: couldn't load file {filename}")
        return
    try:
        # load state from json-file
        filename = state_file
        with open(filename, 'r') as json_file:
            state_info = json.load(json_file)
    except OSError as exception:
        print(f"### Error: couldn't load file {filename}")
        return
    # print the loaded configuration
    config_str = json.dumps(config, indent=4)
    print(config_str)
    # print the loaded game state
    state_info_str = json.dumps(state_info, indent=4)
    print(state_info_str)

    # open a window with predefined size and title
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    # create a GameView with the loaded configuration
    game_view = GameView(config)
    # and make it the view shown in the window
    window.show_view(game_view)

    # setup a game starting from the loaded game state.
    game_view.setup_from_state(state_info)

    # start the game loop
    # from now on all state changes are controlled in the on_update() method:
    #   - wait for the card mover to finish.
    #   - ask current player for his next (legal) play.
    #   - program the card mover to show an animation of this play.
    #   - apply this play to the game state to get the next game state.
    arcade.run()

def play_round(players, shithead, fup_table=None, stats=None, auto=False):
    '''
    Play one round of shithead without GUI.
    Can be used to play a round of Shithead against some AI players over the
    keyboard (-> gameplay_test) or just let some AI players play against each
    other (-> fup_table_generator).
    A human player can use the 'QUIT' play to terminate the round without
    result.
    In a play with only AI players it's possible to get into a deadlock.
    In this case each of the AI players can use the 'ABORT' play to end the
    round without result, if a maximum number of turns has been reached.
    Otherwise, play continues in a loop until only 1 player remains in the game.
    The name of the shithead and the number of turns played is then returned.

    :param players:     list of players => player specific rules.
    :type players:      list
    :param shithead:    shithead of the previous round => dealer
                        None => select dealer randomly
    :type shithead:     str
    :param fup_table:   face up table (not None => update fup_table).
    :type fup_table:    FupTable
    :param stats:       statistic => score, number of turns, number of games.
    :type stats:        Statistic
    :param auto:        True => do not prompt after AIPlayers.
    :type auto:         bool
    :return:            'QUIT', 'ABORT', or name of shithead
                        and number of turns played
    :rtype:             tuple
    '''
    # number of players
    n_players = len(players)

    # find index of previous shithead in players list => dealer
    if shithead is not None:
        for idx, player in enumerate(players):
            if player.name == shithead:
                dealer = idx
                break
        else:
            raise Exception(f"Shithead {shithead} not found in list of players!")
    else:
        # very first round => select dealer randomly
        dealer = -1

    # calculate the number of necessary card decks
    n_decks = Game.calc_nof_decks(n_players)

    # create the logging info from the configuration
    log_level = 'No Secrets'
    log_to_file = False
    log_debug = False
    log_file = ''
    log_info = (log_level, log_to_file, log_debug, log_file)

    # create the initial game state with list of players,
    # the specified dealer (-1 => random, or shithead of previous round),
    # and the number of decks necessary for this number of players.
    state = State(players, dealer, n_decks, log_info)

    # shuffle the talon
    state = Game.next_state(state, Play('SHUFFLE'), fup_table, stats)

    # remove some talon cards to match the player count
    state = Game.next_state(state, Play('BURN'), fup_table, stats)

    # deal 3 face down, 3 face up, and 3 hand cards to each player
    state = Game.next_state(state, Play('DEAL'), fup_table, stats)

    # game loop
    while len(state.players) > 1:
        # play until only one player is left
        if not auto:
            state.print()
        if state.game_phase == SWAPPING_CARDS:
            if not auto:
                print('--- swap face up table with hand cards ---')
        elif state.game_phase == FIND_STARTER:
            suit = plr.STARTING_SUITS[state.starting_card % 4]
            rank = plr.STARTING_RANKS[state.starting_card // 4]
            card = Card(0, suit, rank)
            if not auto:
                print(f'--- show {card} to start the game ---')
        elif state.game_phase == PLAY_GAME:
            if not auto:
                print('--- play ---')
        # let the current player play one action
        player = state.players[state.player]
        while(True):
            play = player.play(state)
            if play is not None:
                break
            # player not ready => wait 100 ms
            sleep(0.1)
        if not auto:
            print(f'Plays: {play.action}-{play.index}')
        if play.action == 'QUIT':
            Game.reset_result(state)    # no winners
            # human player wants to quit the game
            return ('QUIT', 0)
        if play.action == 'ABORT':
            Game.reset_result(state)    # no winners
            # AI-test in deadlock, abort without result
            return ('ABORT', 0)
        # apply this  action to the current state to get to the next state
        state = Game.next_state(state, play, fup_table, stats)
        if not auto:
            print('---------------------------')
        if not auto and isinstance(player, plr.AiPlayer):
            # request prompt from human player after AI play.
            input('Press <Return> to continue')

    # return name of shithead (last player still in the game)
    return (state.players[0].name, state.turn_count)

def fup_table_generator():
    '''
    Generates or updates the face up table.
    Lets 3 AI players of same level play multiple games with random face up
    table cards (no swapping). The result of each game is used to update the
    face up table files.
    '''
    # statistic counters
    n_finished = 0  # number of finished games
    n_aborted = 0   # number of aborted games
    n_quit = 0      # number of quit games
    n_turns = 0     # number of turns played

    # create face up table
    fup_table = FupTable()

    # load face up table from file
    fup_table.load(FUP_TABLE_FILE)

    # create statistics
    stats = Statistics()

    print('### Face Up Table Generator ###')
    # get number of players
    while True:
        n = input('Enter number of players (>1): ' )
        try:
            n_players = int(n)
        except:
            print('Please enter an integer >1!')
            continue
        if n_players > 1:
            break

    # get number of games
    while True:
        n = input('Enter number games: ' )
        try:
            n_games = int(n)
        except:
            print('Please enter an integer >0!')
            continue
        if n_games > 0:
            break

    # create specified number of players with generic names
    players =[]
    for i in range(0, n_players):
        # add players without face up table => random face up table cards.
        players.append(plr.CheapShit(f'Player{i}'))

    # no shithead yet => select dealer randomly
    shithead = None

    for i in range(n_games):
        # play the specified number of rounds
        shithead, turns = play_round(players, shithead, fup_table, stats, True)
        if shithead == 'QUIT':
            # player has quit the game (can't happen ???)
            # => no result for this round
            n_quit += 1
            shithead = None
        elif shithead == 'ABORT':
            # round aborted because of AI deadlock => no result for this round
            n_aborted +=1
            shithead = None
        else:
            # finished rount => count result, number of turns
            n_finished += 1
            n_turns += turns

            # update face up table
            fup_table.score(shithead, 0)

            # update statistics for shithead
            stats.update(shithead, 0, turns)

        if n_finished % 100 == 0:
            # report every 100 finished rounds
            print(f'finished:{n_finished:<10} aborted:{n_aborted:<3} turns:{n_turns:<12}')
    if n_finished % 100 != 0:
        # final reporting for last rounds not already reported
        print(f'finished:{n_finished:<10} aborted:{n_aborted:<3} turns:{n_turns:<12}')
    print()
    # print final statistics
    stats.print()
    print()
    # print face up table
    fup_table.print()
    # write the table to new files to avoid inadvertably overwriting existing files.
    fup_table.save('face_up_table_new.json')
    fup_table.write_to_file('readable_fup_table_new.json')

def play_ai_evaluation_round(players, stats=None):
    '''
    Play one round per player with the same cards.

    In order to evaluate the AI players, we play one round per player with the
    same shuffled talon and a different dealer for each of these rounds.
    I.e. each player plays once with the exact same table and hand cards as any
    other player. To eliminate luck even further the players should pick the
    face down cards always in the same order (left to right).

    :param players:     list of players => player specific rules.
    :type players:      list
    :param stats:       statistic => score, number of turns, number of games.
    :type stats:        Statistic
    :return:            number of aborted rounds, number of finished rounds,
                        and total number of turns played
    :rtype:             tuple
    '''

    # statistic counters
    n_finished = 0  # number of finished games
    n_aborted = 0   # number of aborted games
    n_turns = 0     # number of turns played
    n_talon = 0     # number of talon cards
    n_refills = 0   # number of refill turns

    # number of players
    n_players = len(players)

    # calculate the number of necessary card decks
    n_decks = Game.calc_nof_decks(n_players)

    # create the logging info from the configuration
    log_level = 'No Secrets'
    log_to_file = False
    log_debug = False
    log_file = ''
    log_info = (log_level, log_to_file, log_debug, log_file)

    # create the initial game state with list of players,
    # the specified dealer (-1 => random, or shithead of previous round),
    # and the number of decks necessary for this number of players.
    start_state = State(players, -1, n_decks, log_info)

    # shuffle the talon
    start_state = Game.next_state(start_state, Play('SHUFFLE'), None, stats)

    # remove some talon cards to match the player count
    # => one round per player will be played from this state
    start_state = Game.next_state(start_state, Play('BURN'), None, stats)
    # play with each of the players as dealer one round with the same talon
    # => each player plays each set of table/hand cards.
    for i in range(n_players):
        # make a copy of the start state
        state = start_state.copy()
        # reset the turn with refill counter
        refill_turns = -1
        # different dealer on each round
        # => same sets of table/hand cards for different player each round
        state = Game.next_state(state, Play('DEALER', i), None, stats)

        # deal 3 face down, 3 face up, and 3 hand cards to each player
        state = Game.next_state(state, Play('DEAL'), None, stats)
        talon_size = len(state.talon)

        while len(state.players) > 1:
            # let the current player play one action
            player = state.players[state.player]
            while(True):
                play = player.play(state)
                if play is not None:
                    break
                # player not ready => wait 100 ms
                sleep(0.1)

            if play.action == 'ABORT':
                Game.reset_result(state)    # no winners
                n_aborted +=1
                break

            # apply this  action to the current state to get to the next state
            state = Game.next_state(state, play, None, stats)
#            print(f"talon: {len(state.talon)} turn: {state.turn_count}")
            # count number of turns till talon is empty
            if len(state.talon) == 0 and refill_turns < 0:
                refill_turns = state.turn_count - 1
#                print(f"talon: {talon_size} turns: {refill_turns} refills per turn: {talon_size / refill_turns}")

        if len(state.players) == 1:
            # shithead found
            shithead = state.players[0].name
            turns = state.turn_count
            stats.update(shithead, 0, turns)
            # update the statistic counters
            n_finished += 1
            n_turns += turns
            n_talon += talon_size
            n_refills += refill_turns

    return (n_aborted, n_finished, n_turns, n_talon, n_refills)

def ai_test():
    '''
    Testing out different AIs.

    Let different AIs play multiple fully automatic games.
    Each game is played multiple times with the same start state (burnt cards
    and shuffled talon), so that each player has to play one game with the same
    hand and table cards as any other player. To further mitigate randomness
    all players play their face down table cards from left to right.
    Prints final scores per AI.
    '''

    # statistic counters
    n_finished = 0  # number of finished games
    n_aborted = 0   # number of aborted games
    n_turns = 0     # number of turns played
    n_talon = 0     # number of talon cards
    n_refills = 0   # number of refills

    talon_cards = 0
    talon_turns = 0

    # create face up table
    fup_table = FupTable()

    # create statistics
    stats = Statistics()

    # load face up table from file (in package)
    fup_table.load(FUP_TABLE_FILE, True)

    print('### AI Test ###')

    # create players with generic names
    players = []
#    players.append(plr.CheapShit('Player1', fup_table, False))
#    players.append(plr.CheapShit('Player2', fup_table, False))
#    players.append(plr.CheapShit('Player3', fup_table, False))
    players.append(plr.TakeShit('Player1', fup_table, False))
    players.append(plr.TakeShit('Player2', fup_table, False))
#    players.append(plr.TakeShit('Player3', fup_table, False))
#    players.append(plr.TakeShit('Player4', fup_table, False))
#    players.append(plr.TakeShit('Player5', fup_table, False))
#    players.append(plr.TakeShit('Player6', fup_table, False))
#    players.append(plr.BullShit('Player3', fup_table, False))
    players.append(plr.DeepShit('Player3', fup_table, False))
    n_players = len(players)

    # get number of games
    while True:
        n = input('Enter number of games: ' )
        try:
            n_games = int(n)
        except:
            print('Please enter an integer >0!')
            continue
        if n_games > 0:
            break

    for i in range(n_games):
        # play a round, don't update face up table, update player statistics
        aborts, finished, turns, talon, refills = play_ai_evaluation_round(players, stats)
        n_aborted += aborts
        n_finished += finished
        n_turns += turns
        n_talon += talon
        n_refills += refills


        # report every 10 finished games
        if n_finished % (10 * n_players) == 0:
            print(f'finished:{n_finished:<10} aborted:{n_aborted:<3} turns:{n_turns:<12} refills/turn: {n_talon / n_refills}')

    # report remaining games
    if n_finished % (10 * n_players) != 0:
        print(f'finished:{n_finished:<10} aborted:{n_aborted:<3} turns:{n_turns:<12} refills/turn: {n_talon / n_refills}')
    print()

    # print final statistics
    stats.print()

    # write statistics to human readable file
    stats.write_to_file('ai_test_stats.txt')

    # save statistics to json file
    stats.save('ai_test_stats.json')

def gameplay_test():
    '''
    Shithead game with one human player against 1..5 AIs.

    Shows all cards.
    Human player has to prompt any AI play.
    '''
    # create face up table
    fup_table = FupTable()

    # load face up table from file in package
    fup_table.load(FUP_TABLE_FILE, True)

    print('### Gameplay Test ###')
    # get number of players
    while True:
        n = input('Enter number of players (>1): ' )
        try:
            n_players = int(n)
        except:
            print('Please enter an integer >1!')
            continue
        if n_players > 1:
            break

    # create specified number of players with generic names
    players = []
    # create human player not using GUI
    players.append(plr.HumanPlayer('Wolfi', False))
    for i in range(1, n_players):
        # add AI player with fup_table => card swapping
        players.append(plr.DeepShit(f'Player{i}', fup_table))

    # no shithead yet => select dealer randomly
    shithead = None

    shithead, turns = play_round(players, shithead)
    if shithead != 'QUIT' and shithead != 'ABORT':
        print(f'{shithead} is the Shithead!!!')

def test_state_copy():
    """
    Test copying a game state.

    Creates an initial game state.
    Burns some cards, shuffles the talon, and deals cards to the players.
    Makes a copy of the resulting game state and prints it out.
    """
    # create face up table, the AIs use it for optimum card swapping
    fup_table = FupTable()

    # load face up table from file in package
    fup_table.load(FUP_TABLE_FILE, True)
    #fup_table.print()

    # create statistics
    stats = Statistics()

    # get number of players
    while True:
        n = input('Enter number of players (2..6): ' )
        try:
            n_players = int(n)
        except:
            print('Please enter an integer >1!')
            continue
        if n_players > 1 and n_players < 7:
            break

    # create specified number of players with generic names
    players = []
    # The human player is always at index 0 (only as long as he's in the game!!!),
    # TODO ask for name
    # create a human player using gui
    players.append(plr.HumanPlayer('Wolfi', True))
    for i in range(1, n_players):
        name = f'Player{i}'
        # add AI player with fup_table => card swapping
        players.append(plr.DeepShit(name, fup_table))

    # create state for these players
    state = State(players, -1, 2)
    state.print()
    state = Game.next_state(state, Play('SHUFFLE'))
    state.print()
    state = Game.next_state(state, Play('BURN'))
    state.print()
    state = Game.next_state(state, Play('DEAL'))
    state.print()
    state = state.copy()
    state.print()

def main():
    """
    Starts a shithead game according to the specified command line option:
        no option (default)
        Start a default shithead game against 1 - 5 AI players using the gui.

        -d DEBUGGING -f FILENAME
        Start a shithead game from a logged intermediate state using the gui.
        The intermediate state is loaded from the json-file DEBUGGING
        and the configuration is loaded from the json-file FILENAME.

        -c
        Start a shithead game against 1 - 5 AI players using the command line
        interface.

        -t
        Start a series of AI only games to evaluate different AI types.
        Number and type of players is hardcoded.

        -g
        Start a series of AI only games with random face up table cards to
        generate a table, which helps the AI players to decide which cards to
        swap at the beginning of the game.
    """
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=False)

    group.add_argument("-g", "--gen-fuptab", help="generate a lookup table for the face up table card swapping", action="store_true")
    group.add_argument("-t", "--test-ai", help="run a number of games to test the AI players", action="store_true")
    group.add_argument("-c", "--cli-game", help="play game with human player using the command line interface", action="store_true")
    group.add_argument("-d", "--debugging", type=str, help="load a game state from a JSON-file written with log-level 'Debugging'")

    parser.add_argument("-f", "--filename", type=str, help="config file used when state was written with log-level 'Debugging'")

    args = parser.parse_args()

    if args.gen_fuptab:
        fup_table_generator()
    elif args.test_ai:
        ai_test()
    elif args.cli_game:
        gameplay_test()
    elif args.debugging:
        if args.filename is None:
            raise Exception(f"Specify config file used with this debugging state with option '-f'!")
        load_state_from_file(args.filename, args.debugging)
    else:
        gui_start()

#-----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
    #test_state_copy()