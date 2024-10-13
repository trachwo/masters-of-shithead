'''
State class for the Shithead game.

It stores the current state of a Shithead game:
    - the state of each player (face down/up table cards and hand cards).
    - the state of the talon (draw stack).
    - the state of the discard pile.
    - the current player.
    - the number of cards the current player has played this turn.
    - the current direction of play.

Together with the Game class, the State class forms the Shithead state machine.
Applying one of the legal plays with the Game.next_state() method to the
current state, we get to the next state of the game.
The State class contains the methods for logging a state and for randomly
creating alternative game states used to simulate possible outcomes of a play.

23.08.2022  Wolfgang Trachsler
'''

#from cards_sh import Card, Deck, Hand, Discard
#from play_sh import Play
from math import comb
from random import randrange
import json
import sys

# local imports (modules in same package)
from .cards import Deck
from .discard import Discard

# class representing a Shithead game state
class State:
    '''
    Class representing a State of the shithead game.

    Together with the Game class the State class forms a state machine, where
    plays applied to the current game state define the next game state.
    '''

    def __init__(self, players, dealer, n_decks, log_info):
        '''
        Create the initial shithead game state.

        Stores a copy of the player list and the index of the dealer (usually
        the shithead of the previous round). In case of an invalid index (<0),
        this is the very first round and we have to select one of the players
        as dealer randomly.
        Creates a talon consisting of the specified number of card decks.
        Creates an empty burnt cards pile.
        Creates an empty discard pile.
        Creates an empty removed cards pile.

        Note, that we make actual copies of players, talon, discard, etc.,
        i.e. if we change the state, the structures outside are not changed.
        E.g. after removing a player from self.players because he is out of the
        game, does not affect the list of players used to initialize this state.

        :param players: list of shithead players.
        :type players:  list
        :param dealer:  dealer (prev. shithead) of the game (index for player)
        :type dealer:   int
        :param n_decks: number of card decks used.
        :type n_decks:  int
        :param log_info:log level, 'log to file'-flag, log file name.
        :type log_info: tuple
        '''
        # we don't want to change the original player list (e.g. when a player
        # went out), therefore we make a copy
        self.players = []
        for player in players:
            self.players.append(player.copy())

        #self.players = deepcopy(players)
        # deepcopy() doesn't work in threads !!!
        # => TypeErrTypeError: cannot pickle '_thread.lock' object
        # get the number of players

        n_players = len(players)

        # set the dealer of this round
        if dealer < 0:
            # must be the very 1st round => select dealer at random.
            self.dealer = randrange(0, n_players)
        else:
            # the shithead of the previous round is the dealer
            self.dealer = dealer

        # the initial current player is the player following the dealer in
        # clockwise direction
        self.player = (self.dealer + 1) % n_players

        # create a talon with the specified number of decks
        self.talon = Deck()  # the talon consists of at least one deck (id=0)
        for i in range(1, n_decks):
            self.talon += Deck(i)    # additional decks 1, 2, ...
        self.n_decks = n_decks

        # create empty discard pile
        self.discard = Discard()

        # create empty burnt cards pile
        self.burnt = Deck(empty=True)
        self.n_burnt = len(self.burnt)

        # create empty removed cards pile
        self.killed   = Deck(empty=True)

        # the initial direction is clockwise
        self.direction = True   # CLOCKWISE

        # supposed direction next turn (i.e. no 'K's) is also clockwise
        self.next_direction = True  # => CLOCKWISE

        # supposed player next turn (i.e. no '8's) is the player after the current player
        self.next_player = (self.player + 1) % n_players

        # number of cards played this turn
        self.n_played = 0

        # number of '8's played this turn (=> players skipped)
        self.eights = 0

        # number of 'K's played this turn (=> direction changes)
        self.kings = 0

        # turn counter (it's 1st used to count player's during card swapping)
        self.turn_count = 0

        # game phases (SWAPPING_CARDS, FIND_STARTER, PLAY_GAME, SHITHEAD_FOUND)
        self.game_phase = 0 # => SWAPPING_CARDS

        # card which must be shown to get starting player
        self.starting_card = 0  # => 4 of clubs

        # list of players (index into players) still in the starting player auction
        self.auction_members = [(self.player + i) % n_players for i in range(n_players)]

        # list of players (index into players) which have shown the requested card.
        self.shown_starting_card = []

        # score and turn count per player for this round of the game
        # this is used to revert scores in case of an abort
        self.result = {}
        for player in self.players:
            self.result[player.name] = [0, 0]

        # player, action, and card causing this state
        self.log_player = None
        self.log_action = None
        self.log_card = None

        # log info
        self.log_info = log_info

        # game history = list of plays leading up to this state
        self.history = []


    def get_unknown_cards(self):
        '''
        Returns list of unknown cards.

        Returns all cards in this state which have never been face up.
        This is used to generate possible states for play selection by
        simulation (i.e. the AI makes assumptions about the card distribution).

        :return:    unknown cards.
        :rtype:         Deck
        '''

        unknown = Deck(empty=True)
        # talon and burnt cards are unknown
        unknown += self.talon
        unknown += self.burnt
        for player in self.players:
            for card in player.hand:
                if not card.seen:
                    # player's hand cards which have never been seen face up
                    # are unknown
                    unknown.add_card(card)
            for card in player.face_down:
                    # all face down table cards are unknown
                    unknown.add_card(card)
        unknown.sort()
        return unknown

    def get_seen_cards(self):
        """
        Get a list of cards we know are in the opponent hands.

        To calculate the playability of the hand cards for the current player,
        we need not only the unknown cards, but also the cards we know are in
        the hands of opponents, because they have been face up during the game,
        because they were swapped or taken with the discard pile.

        :return:    opponent hand cards which have been face up.
        :rtype:     list
        """
        seen_cards = []
        for player in self.players:
            if player != self.players[self.player]:
                # not the current player => opponent of current player
                seen_cards += [card for card in player.hand if card.seen]

        return seen_cards

    def estimate_remaining_draws(self, size):
        """
        Estimate the number of times the current player can refill his hand.

        We assume that every player can exactly play 1 card on his turn.
        Players with more than 3 cards just reduce their hands by 1 card.
        Players with 3 cards reduce the talon by 1 card, while their hand size
        stays at 3 cards.
        The size parameter is used for the current player in order to be able
        to estimate the impact on taking the discard pile on the number of
        remaining turns.

        :param size:    number of cards in hand of current player.
        :type size:     int
        :return:        number of remaining turns, refills by current player,
                        number of current player's hand cards.
        :rtype:         Tuple
        """
        hands = []  # list of players hand sizes with current player at index 0
        n_talon = len(self.talon)       # number of cards in talon
        n_players = len(self.players)  # number of players
        current = self.player          # index of current player in players
        for i in range(n_players):
            # create list with numbers of hand cards
            if i == 0:
                hands.append(size)
            else:
                hands.append(len(self.players[(current + i) % n_players].hand))
        n_turns = 0     # turn counter
        n_draws = 0     # number of draws by current player
        while n_talon > 0:
#            print(f"n_turns: {n_turns} player: {n_turns % n_players} hands: {hands} n_talon: {n_talon}")
            if hands[n_turns % n_players] > 3:
                # don't refill from talon
                hands[n_turns % n_players] -= 1
            else:
                # refill from talon
                n_talon -= 1
                if n_turns % n_players == 0:
                    # count draws of current player
                    n_draws += 1
            # next turn
            n_turns += 1

#        print(f"### n_turns: {n_turns} n_draws: {n_draws} n_hands: {hands[0]}")
        return (n_turns, n_draws, hands[0])

    def log_one_line(self, turn_count):
        '''
        Creates log message with one line overview over game state.

        :param turn_count:  number of current turn.
        :type turn_count:   int
        :return:            log message.
        :rtype:             str
        '''
        # find the maximum player name length to improve the log formatting
        max_name = 0
        for player in self.players:
            if len(player.name) > max_name:
                max_name = len(player.name)

        turn = f'{turn_count:>3}'
        if self.next_direction:
            # dir = '\u27f3'    # clockwise (closed)
            dir = '\u21bb'      # clockwise (open)
        else:
            # dir = '\u27f2'    # counterclockwise (closed)
            dir = '\u21ba'      # counterclockwise (open)
        talon = f'Talon:{len(self.talon):>3}'
        discard = f'Discard:{len(self.discard):>3}'
        player = f'{self.log_player}:'
        if max_name > 15:
            player = f'{player:<20}'
        elif max_name > 10:
            player = f'{player:<16}'
        else:
            player = f'{player:<11}'
        action = f'{self.log_action:<7}'
        card = f'{self.log_card:<3}'
        # add turn count, direction, talon size, player name, action, card
        # and discard pile size to string
        log_msg = f'{turn}   {dir}   {talon}   {player} {action} {card}   {discard}    '
        # add top cards of discard pile to string
        log_msg += self.discard.get_top_string()
        return log_msg


    def log_no_secrets(self, turn_count):
        '''
        Creates log message with game overview and everything disclosed.

        :param turn_count:  number of current turn.
        :type turn_count:   int
        '''
        # add turn count, direction, player name, action, and played card
        log_msg = f'Turn:    {turn_count:>3}   '
        if self.next_direction:
            log_msg += '\u21bb   '
        else:
            log_msg += '\u21ba   '
        log_msg += f'{self.log_player}: {self.log_action} {self.log_card}\n'

        # add unknown cards size and unknown cards to string
        unknown = self.get_unknown_cards()
        log_msg += f'Unknown: {len(unknown):>3}   '
        log_msg += unknown.get_string() + '\n'

        # add talon size and talon cards to string
        log_msg += f'Talon:   {len(self.talon):>3}   '
        log_msg += self.talon.get_string() + '\n'

        # add discard size and discard pile cards to string
        log_msg += f'Discard: {len(self.discard):>3}   '
        log_msg += self.discard.get_top_string(None, True) + '\n'

        # add one line per player to the string
        cur = self.players[self.player]
        nxt = self.players[self.next_player]
        for idx, player in enumerate(self.players):
            # add current/next indicator
            if player == cur and player == nxt:
                log_msg += 'current/next ---> '
            elif player == cur:
                log_msg += '     current ---> '
            elif player == nxt:
                log_msg += '        next ---> '
            else:
                log_msg += '                  '
            # add player's name, facedown, faceup, and hand cards to string
            log_msg += player.get_string(None, 3) + '\n'

        return log_msg

    def log_game_display(self, turn_count, remember=False):
        '''
        Creates log message with all information visible to the human player.

        :param turn_count:  number of current turn.
        :type turn_count:   int
        :param remember:    True => reveal cards which have been face up.
        :type remember:     bool
        :return:            log message
        :rtype:             str
        '''
        # add turn count, direction, player name, action, and played card
        log_msg = f'Turn:    {turn_count:>3}   '
        if self.next_direction:
            log_msg += '\u21bb   '
        else:
            log_msg += '\u21ba   '
        log_msg += f'{self.log_player}: {self.log_action} {self.log_card}\n'

        # add unknown cards size, talon size, discard pile size, and top discard pile cards.
        unknown = self.get_unknown_cards()
        log_msg += f'Unknown: {len(unknown):>3}   '
        log_msg += f'Talon:   {len(self.talon):>3}   '
        log_msg += f'Discard: {len(self.discard):>3}   '
        log_msg += self.discard.get_top_string() + '\n'

        # add one line per player to the string
        cur = self.players[self.player]
        nxt = self.players[self.next_player]
        for idx, player in enumerate(self.players):
            # add current/next indicator
            if player == cur and player == nxt:
                log_msg += 'current/next ---> '
            elif player == cur:
                log_msg += '     current ---> '
            elif player == nxt:
                log_msg += '        next ---> '
            else:
                log_msg += '                  '
            # add player's name, facedown, faceup, and hand cards to string
            if player.is_human:
                # reveal human player's hand cards
                log_msg += player.get_string(None, 2)
            else:
                # AI player cards
                if remember:    # reveal seen hand cards
                    log_msg += player.get_string(None, 1)
                else:           # don't reveal hand cards
                    log_msg += player.get_string(None, 0)
            log_msg += '\n'

        return log_msg

    def log_debugging(self):
        '''
        Create JSON string with info for state reconstruction.

        To be able to reconstruct a intermediate game state we need the card
        distribution (talon, removed cards, players, and discard pile), the
        current player and the current direction.

        :return:            log message
        :rtype:             str
        '''
        log_dict = {}
        log_dict['turn_count'] = self.turn_count
        log_dict['log_player'] = self.log_player
        log_dict['log_action'] = self.log_action
        log_dict['log_card'] = self.log_card
        log_dict['players'] = []
        for player in self.players:
            log_dict['players'].append(player.get_state())
        log_dict['dealer'] = self.dealer
        log_dict['player'] = self.player
        log_dict['talon'] = self.talon.get_state()
        log_dict['n_decks'] = self.n_decks
        log_dict['discard'] = self.discard.get_state()
        log_dict['burnt'] = self.burnt.get_state()
        log_dict['n_burnt'] = self.n_burnt
        log_dict['killed'] = self.killed.get_state()
        log_dict['direction'] = self.direction
        log_dict['next_direction'] = self.next_direction
        log_dict['next_player'] = self.next_player
        log_dict['n_played'] = self.n_played
        log_dict['eights'] = self.eights
        log_dict['kings'] = self.kings
        log_dict['game_phase'] = self.game_phase
        log_dict['starting_card'] = self.starting_card
        log_dict['auction_members'] = self.auction_members
        log_dict['shown_starting_card'] = self.shown_starting_card
        log_dict['result'] = self.result
        log_dict['log_info'] = self.log_info
        log_dict['history'] = self.history

        # create the JSON string
        json_str = json.dumps(log_dict)
        return json_str

    def print(self):
        '''
        Prints overview over game state.

        According to the selected log-level, a log message is generated from
        the current game state and printed to the terminal.
        If log_to_file has been selected, the log message is also written to
        the specified log-file.
        '''
        # before the actual game starts the turn number is always 0
        if self.game_phase == 2:    # PLAY_GAME
            turn_count = self.turn_count
            # states with 'END' action already show the number of the next turn
            if self.log_action == 'END':
                turn_count -= 1
        else:
            turn_count = 0

        # seperator line for multi-line logs
        sep = '------------------------------------------------------------------------------\n'

        # get the log_level from log_info
        log_level = self.log_info[0]
        # generate a log message according to this level from the game state
        if log_level == 'No Secrets':
            # reveal all cards
            log_msg = sep + self.log_no_secrets(turn_count)
        elif log_level == 'Game Display':
            # reveal all cards visible to the human player
            log_msg = sep + self.log_game_display(turn_count)
        elif log_level == 'Perfect Memory':
            # reveal all cards visible to or seen by the human player
            log_msg = sep + self.log_game_display(turn_count, True)
        elif log_level == 'Debugging':
            # log JSON string of info necessary for game state reconstruction
            log_msg = sep + self.log_debugging()
        else:
            # just print a one line message with minimal information
            log_msg = self.log_one_line(turn_count)

        # print the log message to the terminal
        print(log_msg)

        if self.log_info[1]:                                # log-to-file selected
            if self.log_info[2]:                            # log debugging to file
                # log JSON string of info necessary for game state reconstruction
                log_msg = sep + self.log_debugging()

            with open(self.log_info[3], 'a') as log_file:   # open log-file for appending
                log_file.write(log_msg + '\n')              # add log-message to log-file

#        print(f'### n_played: {self.n_played}')
#        print(f'### get_fup: {self.players[self.player].get_fup}')
#        print(f'### get_fup_rank: {self.players[self.player].get_fup_rank}')


    def hash(self):
        '''
        Hash key unambiguously identifying this state.

        Each state is unambiguously identified by the play history leading up
        to this state. We create a hash by concatinating the string
        representations of the plays in the play history of this state to a
        single string.

        :return:    hash unambiguously identifying this state.
        :rtype:     str
        '''
        return  ''.join(self.history)

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of shithead state (not just reference).
        :rtype:         State
        '''
        #create a new state for the current list of players
        new_state = State(self.players, self.dealer, self.n_decks, self.log_info)

        # but this creates a talon containing n_decks
        # => we have to replace it with the original talon
        new_state.talon = self.talon.copy()

        # overwrite the attributes of the new state with copies from the
        # current state.
        new_state.discard = self.discard.copy()
        new_state.burnt = self.burnt.copy()
        new_state.killed = self.killed.copy()
        new_state.player = self.player
        new_state.next_player = self.next_player
        new_state.direction = self.direction
        new_state.next_direction = self.next_direction
        new_state.n_played = self.n_played
        new_state.eights = self.eights
        new_state.kings = self.kings
        new_state.turn_count = self.turn_count
        new_state.game_phase = self.game_phase
        new_state.starting_card = self.starting_card
        new_state.auction_members = self.auction_members[:]
        new_state.shown_starting_card = self.shown_starting_card[:]
        # score and turn count per player for this round of the game
        new_state.result = {}
        for key in self.result.keys():
            new_state.result[key] = self.result[key]
        # copy the log info
        new_state.log_info = self.log_info
        # copy the play history
        new_state.history = self.history[:]
        # finally return the copy of the state
        return new_state

    def is_player(self, name):
        """
        Check if current player has specified name.

        :param name:        name of player.
        :type name:         str
        :return:            True if current player is named player.
        :rtype:             bool
        """
        if self.players[self.player].name == name:
            return True
        else:
            return False

    @classmethod
    def simulation_state(cls, state, sim_player=None):
        '''
        Create a game state for simulation.

        For a simulation we cannot use the real game state, that would be
        cheating. If we had a perfect memory, we knew where all cards, which
        were face up once during the game (face up table cards, cards played on
        discard pile) are (discard pile, player hand, or out of the game).
        For all other cards (talon, face down table cards, and hand cards dealt
        and not shown or swapped, or drawn from talon) we must assume a state.
        Therefore, we collect all unknown player cards (cards not marked with
        the fup-flag except the ones of the simulated player) and all burnt
        cards and put them back on the talon. Then we shuffle the talon and
        give each player the same ammount of cards back from the talon. We also
        remove the same amount of burnt cards from the talon. This way we get
        an equivalent game state without copying the actual game state.

        :param state:       original shithead game state.
        :type state:        State
        :param sim_player:  name of simulated player.
        :type sim_player:   str
        :return:            game state with redistributed unknown cards.
        :rtype:             State
        '''
        # simulation states starts out as copy of the original state
        sim = state.copy()

        # remember number of burnt cards in original game
        n_burnt = len(sim.burnt)
        # remove cards from burnt cards and put them back to the talon
        for i in range(n_burnt):
            sim.talon.add_card(sim.burnt.pop_card())

        # the simulated player is different, he knows all his hand cards.
        if sim_player is None:
            # current player is simulated player by default
            sim_player = sim.players[sim.player].name
        n_players = {}
        for player in sim.players:
            # put unknown cards from player's hand back to talon
            n_hand = 0
            if player.name != sim_player:   # not the simulated player
                # make a list of unkown cards in this player's hand
                unknown = [card for card in player.hand if not card.seen]
                n_hand = len(unknown)
                for card in unknown:
                    sim.talon.add_card(player.remove_card('HAND',card))

            # put player's face down table cards back to talon
            unknown = [card for card in player.face_down]
            n_fdown = len(unknown)
            for card in unknown:
                sim.talon.add_card(player.remove_card('FDOWN', card))
            # remember number of cards removed from hand and table
            n_players[player.name] = [n_hand, n_fdown]

        # shuffle talon and redistribute the cards
        sim.talon.shuffle()

        # remove burnt cards from talon
        for i in range(n_burnt):
            sim.burnt.add_card(sim.talon.pop_card())

        # refill hand and facedown table cards of players
        for player in sim.players:
            # refill hand with n_hand cards
            for i in range(n_players[player.name][0]):
                player.take_card('HAND', sim.talon.pop_card())
            # refill face down table cards with n_fdown cards
            for i in range(n_players[player.name][1]):
                player.take_card('FDOWN', sim.talon.pop_card())
        return sim

    @classmethod
    def calc_nof_simulation_states(cls, state):
        '''
        Calculate the number of different simulation states.

        We count the total number of unknown cards (uk_tot) and the number of
        unknown hand cards (uk_hand) and unknown face down table cards
        (uk_fdown) per player.
        Next we calculate the number of possible hands and face down sets for the 1st player:
            n_hands1 = comb(uk_tot, uk_hand1)
            n_fdowns1 = comb(uk_tot - uk_hand1, uk_fdown1)

        and for the 2nd player:
            n_hands2 = comb(uk_tot - uk_hand1 - uk_fdown1, uk_hand2)
            n_fdown2 = comb(uk_tot - uk_hand1 - uk_fdown1 - uk_hand2, uk_fdown2)

        and so on.
        The total number of possible redistributions is the product
            n_sim_states = n_hands1 * n_fdowns1 * n_hands2 * n_fdowns2 * ...

        :param state:   original shithead game state.
        :type state:    State
        :return:        number of different simulation states.
        :rtype:         int
        '''
        # count number of burnt cards in original state
        uk_tot = len(state.burnt)
        uk_pl = []  # list for number of uknown player hand and face down table cards

        # the current player is different, he knows all his hand cards.
        current_player = state.players[state.player]
        for player in state.players:
            # count players unknown hand cards
            uk_hand = 0
            if player != current_player:
                for card in player.hand:
                    if not card.seen:
                        uk_hand += 1
            uk_tot += uk_hand
            uk_pl.append(uk_hand)

            # count player's face down table cards
            uk_fdown = len(player.face_down)
            uk_tot += uk_fdown
            uk_pl.append(uk_fdown)

        #print(f'### total unknown: {uk_tot}')
        #print(uk_pl)

        # calculate the number of possible redistributions
        n_sim_states = 1    # all player cards known
        for uk in uk_pl:
            n_sim_states *= comb(uk_tot, uk)
            uk_tot -= uk

        return n_sim_states