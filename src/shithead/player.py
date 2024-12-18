'''
Player class for the Shithead game.

The Player class has 2 subclasses.
HumanPlayer represents a human player using a gui (mouse) or a command line
interface (keyboard) to enter his plays.
AiPlayer represents the AI opponents and has further subclasses representing
different AI strategies (strengths).

The Player base class keeps the face down and face up table cards, as well as
the hand cards of each player. It tells us from which of these card lists this
player has to play his next card, and if this player is out of the game (has no
cards left). It comes with a range of methods used by all subclasses.

The HumanPlayer subclass provides additional methods necessary to select the
human players next play either with a mouse click in the gui or by entering a
number (referencing one of the legal plays) over the keyboard.

The AiPlayer subclass provides an additional method used by all AI players to
swap hand against face up table cards at the start of a round.

A range of AiPlayer subclasses represents AI opponents of different strengths,
each adding its own select_play() method used to select the next play from a
list of legal plays:
    - ShitHappens (weak):
      Selects his card plays at random.

    - BullShit (weak):
      Uses statistics to select his next play.

    - CheapShit (medium):
      Plays his cheapest cards ('4', '5', '6', ...) before his most valuable
      cards (.., 'K', 'A', '10', '2', '3').

    - TakesShit (medium):
      Improves on CheapShit by volunarily taking the discard pile if this could
      be of advantage.

    - DeepShit (strong):
      Improves on TakeShit by using simulation for his end game.

23.08.2022  Wolfgang Trachsler
'''

import random
from threading import Thread
from collections import Counter

# local imports (modules in same package)
from .cards import Card, Deck
from .state import State, SWAPPING_CARDS, FIND_STARTER
from .play import Play
from .game import Game
from .monte_carlo import MonteCarlo
from .analyzer import Analyzer

# rank to value mapping.
# value of a card according to it's rank.
# 4,5,6,7,8,9,J,Q,K,A => the higher the better.
# 10 => can be played on every card except 7.
# 2 => can be played on every card, but next player can also play every card.
# 3 => can be played on every card, but next player must match last non-3 card.
RANK_TO_VALUE = {'4': 0, '5': 1, '6': 2, '7': 3, '8': 4, '9': 5, 'J': 6,
                 'Q': 7, 'K': 8, 'A': 9, '10': 10, '2': 11, '3': 12}
# alternative map => play '3' before '2' (e.g. on '7', 'K', 'A'
# => "Druck mache!!!")
RANK_TO_VALUE_DRUCK = {'4': 0, '5': 1, '6': 2, '7': 3, '8': 4, '9': 5, 'J': 6,
                       'Q': 7, 'K': 8, 'A': 9, '10': 10, '3': 11, '2': 12}

# Ranks with value >= HOLD_BACK_VALUE don't play more than 1 card
HOLD_BACK_VALUE = 7

# has been better than RANK_TO_VALUE in tests with only CheapShit players
RANK_TO_VALUE_CHEAP_SHIT = {'4': 0, '5': 1, '6': 2, '7': 3, '8': 4, '9': 5,
                            'J': 6, 'Q': 7, 'K': 8, 'A': 9, '3': 10, '2': 11,
                            '10': 12}

# In pure AiPlayer games, the game could get into a deadlock
# => abort after a maximum number of turns per player
MAX_NOF_TURNS_PER_PLAYER = 100

# When selecting a play by simulation
# run this number of simulations per possible play,
# i.e. each time create a state with a 'new' distribution of the unknown cards
# and run a simulation from this state using one of the possible plays as
# opening play.
NOF_SIMULATIONS_PER_PLAY = 30

# Maximum number of find_best_playability() recursions before aborting
# recursions and just play the worst playable card.
MAX_RECURSIONS = 500

# number of loops with randomly distributed unknown cards to evaluate the
# playability after a REFILL.
REFILL_LOOPS = 3

# Estimated number of cards still in current player's hand when the 1st player
# gets rid of all hand cards, which is considered tolerable
TAKE_LIMIT = 1


# -----------------------------------------------------------------------------
class Player:
    '''
    Class representing a shithead player
    '''
    def __init__(self, name):
        '''
        Initialize a shithead player.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.
        Setting the fdown_random flag to false allows for additional
        elimination of randomness when using play_ai_evaluation_round().

        :param name:            player's name.
        :type name:             str
        '''
        self.name = name        # player's name
        self.turn_count = 0     # number of turns played
        self.face_down = Deck(empty=True)  # player's face down table cards
        self.face_up = Deck(empty=True)    # player's face up table cards
        self.hand = Deck(empty=True)       # player's hand cards.
        self.get_fup = False    # True => take face up table card as 2nd play
        self.get_fup_rank = None  # rank of face up table card taken on hand
        self.is_human = False   # True => human player
        self.fup_table = None       # human player never uses FUP table.

    def select_swap(self, plays):
        '''
        Select play during card swapping.

        :param plays:   possible plays.
        :type plays:    list
        :return:        plays GET-0, GET-0, GET-0, PUT-x, PUT-y, PUT-z, END
        :rtype:         Play
        '''
        raise NotImplementedError("This method must be implemented in the"
                                  " subclass")

    def deal(self, card):
        '''
        Deal a card to this player.
        The 1st 3 cards are dealt face down.
        The 2nd 3 cards are dealt face up (=> set face up flag).
        The 3rd 3 cards are dealt face down as hand cards.

        :param card: card dealt to player.
        :type card: Card
        '''
        if len(self.face_down) < 3:
            # the 1st 3 cards are dealt as face down table cards
            self.face_down.add_card(card)
        elif len(self.face_up) < 3:
            # the next 3 cards are dealt as face up table cards.
            card.face_up()      # flip this card face up
            card.seen = True    # => we know where this card is.
            self.face_up.add_card(card)
        elif len(self.hand) < 3:
            # the final 3 cards are dealt as face down hand cards.
            self.hand.add_card(card)
            self.hand.sort()    # keep hand cards sorted
        else:
            raise ValueError("Only 9 cards are dealt to player!")

    def reset(self):
        """
        Remove all of the player's cards.
        """
        self.face_down = Deck(empty=True)   # player's face down table cards
        self.face_up = Deck(empty=True)     # player's face up table cards
        self.hand = Deck(empty=True)        # player's hand cards.

    def get_string(self, score=None, visibility=0):
        '''
        Create string representation of player's cards.

        Used for logging and for playing the game without gui.

        :param score:       number indicating the value of the hand
        :type score:        float
        :param visibility:  0 => hide all cards.
                            1 => reveal hand cards which have been face up.
                            2 => reveal hand cards.
                            3 => reveal all cards.
        :type all:          int
        :return:            string with player cards overview
        :rtype:             str
        '''
        if visibility == 3:     # reveal all cards
            fdown_str = str(self.face_down)
        else:
            # display cards face down with selection index
            # => 'X0X X1X X2X'
            fdown_str = ' '.join(f'X{i}X' for i in range(len(self.face_down)))

        if visibility == 3 or visibility == 2:   # reveal all hand cards
            hand_str = str(self.hand)
        elif visibility == 1:   # reveal seen cards
            # create a list of the hand cards we have seen before
            fup = [card for card in self.hand if card.seen]
            # first display the unknown hand cards as 'XX XX ...'
            hand_str = (len(self.hand) - len(fup)) * 'XX '
            # then add the hand cards we have seen before face up
            hand_str += ' '.join([str(card) for card in fup])
        else:
            # display all hand cards as 'XX XX ...'
            hand_str = len(self.hand) * 'XX '

        player_str = f'{self.name:12} '                 # print name
        player_str += f'FDOWN: {fdown_str:12} '         # print face down cards
        player_str += f'FUP: {str(self.face_up):12} '   # print face up cards
        if score is None:
            player_str += f'HAND: {hand_str}'           # print hand cards
        else:
            player_str += f'HAND: {hand_str}   {score}'  # hand cards andscore
        return player_str

    def print(self, score=None, visibility=0, end='\n'):
        '''
        Print player's cards.

        :param score:       number indicating the value of the hand
        :type score:        float
        :param visibility:  0 => hide all cards.
                            1 => reveal hand cards which have been face up.
                            2 => reveal hand cards.
                            3 => reveal all cards.
        :type all:          int
        :param end:         last character printed (usually '' or '\n')
        :type end:          str
        '''
        print(self.get_string(score, visibility), end=end)

    def get_card_source(self):
        '''
        Get cards from which player has to play next card.

        As long as the player has hand cards he must play from his hand.
        If all hand cards are gone, he must play from the face up cards.
        If all face up cards are also gone, he must play his face down cards.
        If all face down cards are gone, this player is out of the game.

        :return: action used to create Play object plus card list.
        :rtype: (action, list)
        '''
        if len(self.hand) > 0:
            return ('HAND', [card for card in self.hand])
        elif len(self.face_up) > 0:
            return ('FUP', [card for card in self.face_up])
        elif len(self.face_down) > 0:
            return ('FDOWN', [card for card in self.face_down])
        else:
            return ('OUT', [])

    def play_card(self, source, index):
        '''
        Remove the card at the index from the source and return it.

        :param  source: 'HAND', 'FUP', or 'FDOWN'.
        :type source:   str
        :param index:   index of card in source list.
        :type index:    int
        :return:        card removed from source at index.
        :rtype:         Card
        '''
        if source == 'HAND':
            card = self.hand.pop_card(index)
        elif source == 'FUP':
            # remove from face up table cards
            card = self.face_up.pop_card(index)
        elif source == 'FDOWN':
            # remove from face down table cards
            card = self.face_down.pop_card(index)
        else:
            raise ValueError(f'Unexpected card source {source}!')
        return card

    def remove_card(self, source, card):
        '''
        Remove the specified card from the source and return it.

        :param  source: 'HAND', 'FUP', or 'FDOWN'.
        :type source:   str
        :param card:    card we want to remove.
        :type card:     Card
        :return:        card removed from source at index.
        :rtype:         Card
        '''
        if source == 'HAND':
            card = self.hand.remove_card(card)
        elif source == 'FUP':
            # remove from face up table cards
            card = self.face_up.remove_card(card)
        elif source == 'FDOWN':
            # remove from face down table cards
            card = self.face_down.remove_card(card)
        else:
            raise ValueError(f'Unexpected card source {source}!')
        return card

    def take_card(self, target, card):
        '''
        Add the card to the target.

        :param card:    card to be added.]
        :type card:     Card
        :param  target: 'HAND', 'FUP', or 'FDOWN'.
        :type target:   str
        :param index:   index of card in source list.
        :type index:    int
        '''
        if target == 'HAND':
            # add to hand
            self.hand.add_card(card)
            self.hand.sort()
        elif target == 'FUP':
            # add to face up table cards
            self.face_up.add_card(card)
        elif target == 'FDOWN':
            # add to face down table cards
            self.face_down.add_card(card)
        else:
            raise ValueError(f'Unexpected card target {target}!')

    def find_cheapest_play(self, plays, vmap):
        '''
        Find the cheapest card to play from a list of legal plays.

        If several cards can be played, it's usually a good strategy to play
        the card with the lowest value first (e.g. on a '2' better play a '4'
        than an 'A').

        :param plays:   possible plays.
        :type plays:    list
        :param vmap:    maps ranks to value.
        :type vmap:     dictionary.
        :return:        play of card with lowest value.
        :rtype:         Play
        '''
        # initialize with a value larger than the most expensive rank.
        min_val = max(vmap.values()) + 1
        # initialize index of cheapest play found with invalid value.
        cheapest = -1
        for i, play in enumerate(plays):
            if play.action == 'HAND':
                val = vmap[self.hand[play.index].rank]
            elif play.action == 'FUP':
                val = vmap[self.face_up[play.index].rank]
            elif play.action == 'GET':
                # take cheapest face up table card after taking discard pile
                val = vmap[self.face_up[play.index].rank]
            else:
                val = min_val   # all others are don't care
            if val < min_val:
                # new minimum found
                min_val = val
                cheapest = i
        # return the play using the cheapest card
        if cheapest < 0:
            raise ValueError("Error trying to find cheapest card!")
        return plays[cheapest]

    def play_again_or_end(self, plays):
        '''
        Indicates, that we can play another card or end turn.

        Returns True if plays contains a 'HAND' or 'FUP' action as well as an
        'END' action. I.e. if the player could play another card of same rank
        as before or end his turn to save it for later.

        :param plays:   possible plays.
        :type plays:    list
        :return:        True => 'HAND' or 'FUP' and 'END' in plays.
        :rtype:         bool
        '''
        actions = [play.action for play in plays]
        return ('HAND' in actions or 'FUP' in actions) and 'END' in actions

    def refill_or_play_again(self, plays):
        '''
        Indicates, that we can refill or play another card.

        Returns True if plays contains a 'HAND' action as well as an 'END'
        action. I.e. if the player could play another card of same rank
        as before from hand or refill his hand from the talon.

        :param plays:   possible plays.
        :type plays:    list
        :return:        True => 'HAND' and 'REFILL' in plays.
        :rtype:         bool
        '''
        actions = [play.action for play in plays]
        return 'HAND' in actions and 'REFILL' in actions

    def kill_or_play_again(self, plays):
        '''
        Indicates, that we can kill the discard pile or play another card.

        Returns True if plays contains a 'HAND' or 'FUP' action as well as a
        'KILL' action. I.e. the player could play another card of same rank
        as before or kill the discard pile because there are already >=4 cards
        of same rank at the top.

        :param plays:   possible plays.
        :type plays:    list
        :return:        True => 'HAND' or 'FUP' and 'KILL' in plays.
        :rtype:         bool
        '''
        actions = [play.action for play in plays]
        return ('HAND' in actions or 'FUP' in actions) and 'KILL' in actions

    def estimate_turns_per_hand(self, hand):
        """
        Estimate how many turns it takes to get rid of a hand of cards.

        This is used to decide, whether to voluntarily take the discard pile,
        or to play a card from hand and refill.

        :param hand:    list of card ranks in hand.
        :type hand:     List
        :return:        number of turns to get rid of this hand
        :rtype:         int
        """

        count = Counter(hand)   # count ranks in hand
        # since all cards with same rank can be played in one turn, we start
        # with one turn per rank in this hand
        turns = len(count)
        # but after playing the '10's, 'Q's, or each set of >=4 cards of same
        # rank, we can play one rank for free.
        for rank, cnt in count.items():
            if rank == '10':
                turns -= 1  # kills the discard pile, next rank free
            elif rank == 'Q':
                turns -= 1  # must be covered, next rank free
            elif cnt >= 4:
                turns -= 1  # kills the discard pile, next rank free

        return turns

    def take_discard_or_not(self, state):
        """
        Check if voluntarily taking the discard pile is worth it.

        We should take the discard pile if we already have >3 cards on hand and
        taking the discard pile would help us to get rid of them faster by
        giving us sets of 4 or more cards with the same rank.
        With 3 cards on hand we only should take the discard pile if it has
        good cards in it and if we have a chance to get our hand back down to
        3 again before the talon runs out (note that taking cards with ranks
        we already have on hand doesn't increase the necessary number of
        turns!).

        :param state:   game state.
        :type state:    State
        :return:        True => take the discard pile.
        :rtype:         bool
        """
        # only take the discard pile if it contains cards we already have on
        # hand plus good cards ('2', '3', 'K', 'A').
        hand = [card.rank for card in self.hand]
        discard = [card.rank for card in state.discard]
        if len(discard) == 0:
            # No discard pile
            return False

        if len(hand) > 3:   # already more than 3 cards on hand
            # check if taking the discard pile will help to get rid of the hand
            # cards faster
            no_take_turns = self.estimate_turns_per_hand(hand)
            take_turns = self.estimate_turns_per_hand(hand + discard)
            # if we take the discard pile we use 1 additional turn
            return take_turns + 1 < no_take_turns

        # only 3 cards or less on hand and talon is empty
        # => don't take the discard pile
        if len(state.talon) == 0:
            return False

        # if we have only 3 cards on hand, we only consider taking the discard
        # pile if it contains only ranks we have already in hand (doesn't hurt)
        # + the good ranks '2', '3', 'Q', 'K', 'A'.
        allowed = hand + ['2', '3', 'Q', 'K', 'A']
        allowed = set(allowed)
        good_cards = 0
        for rank in discard:
            if rank not in allowed:
                # don't take the discard pile
                return False
            if rank in ['2', '3', 'A']:
                good_cards += 1

        # the discard pile should contain at least 1 good card
        if good_cards == 0:
            return False

        # estimate how many turns it takes to get rid of the hand after taking
        # the discard pile and add 1 turn (taking the discard pile)
        take_turns = self.estimate_turns_per_hand(hand + discard) + 1

        # We use this number, but at least 3 as hand size of the current player
        # to estimate the remaining turns till the talon runs out.
        if take_turns <= 3:
            return True    # taking the discard pile makes no difference

        # >3 turns to get rid of hand cards after taking the discard pile
        # => use number of turns as starting hand size to estimate the number
        #    of cards in this player's hand, when the 1st player gets rid of
        #    all hand cards.
        rem_hand = state.estimate_remaining_hand(take_turns)
        # Too many cards on hand when 1st opponent gets rid of all hand
        # cards => don't voluntarily take the discard pile
        return rem_hand <= TAKE_LIMIT

    def select_simulated_play(self, plays, state):
        '''
        Play selection used by all players during simulation.

        If we want to simulate the outcome of a specific play on a game,
        we use this method instead of the select_play() method normally used by
        AI and human players:
            - swaps cards if fup_table has been specified.
            - always shows the starting card, if it's on hand.
            - never voluntarily takes the discard pile.
            - only plays again if it's a low card (4, 5, 6, 7, 8, 9, J) or if
              the talon is empty.
            - when playing from hand:
                -- selects the cheapest playable card,
                   but '3' over '2' on '7', 'K', 'A' (Druck mache!)
            - when playing from face up table cards:
                -- selects the cheapest playable card.
                   but '3' over '2' on '7', 'K', 'A' (Druck mache!)
                -- no playable cards => select the cheapest card at random.
            - when playing from face down table cards:
                -- selects any card at random.
            - doesn't play another '8' if only 2 players are left.
              => plays '8', ends turn, other player skipped, plays '8', ...
            - always refills on 'Q' or empty discard pile.
            - plays as many bad cards (4, 5, 6, 7) as possible before refill,
              but refills before playing another good (2, 3, 10, Q, K, A)
              or medium card (8, 9, J).
        '''
        discard = state.discard     # discard pile

        # handle all cases with only one option:
        if len(plays) == 1:
            # only one option ('TAKE', 'REFILL', 'KILL', 'END', 'OUT')
            # => do it.
            return plays[0]

        # swap face up table cards with hand cards.
        if state.game_phase == SWAPPING_CARDS:
            if self.fup_table is None:
                return Play('END')  # don't swap cards.
            return self.select_swap(plays)

        # handle starting player auction:
        if state.game_phase == FIND_STARTER:
            # we only get here, if there's a card to show .
            # otherwise 'END' would be the only possible play.
            return plays[0]

        # never take discard pile voluntarily
        # => remove 'TAKE' from possible plays.
        plays = [play for play in plays if play.action != 'TAKE']
        if len(plays) == 1:
            return plays[0]

        # play another card of same rank or end turn?
        if self.play_again_or_end(plays):
            # don't play '8' if only 2 players left.
            top_rank = discard.get_top_rank()
            if top_rank == '8' and len(state.players) == 2:
                return Play('END')  # => end turn

            # play card if talon is empty or its value is < 7 ('Q')
            if (len(state.talon) == 0 or
                    RANK_TO_VALUE[state.discard.get_top_rank()] < 7):
                # remove 'END' play => play card
                plays = [play for play in plays if play.action != 'END']
            else:
                return Play('END')  # => end turn

        # play another card of same rank or refill first
        if self.refill_or_play_again(plays):
            # alway refill 1st on 'Q' or empty discard pile.
            top_rank = discard.get_top_rank()   # None => empty
            if top_rank is None or top_rank == 'Q':
                return Play('REFILL')
            if (top_rank == '4' or top_rank == '5' or top_rank == '6' or
                    top_rank == '7'):
                # play bad cards before refilling => kill pile first
                # remove 'REFILL' => play card
                plays = [play for play in plays if play.action != 'REFILL']
            else:
                # refill before playing another good or medium card.
                return Play('REFILL')

        # play another card of same rank or kill the discard pile?
        if self.kill_or_play_again(plays):
            # prefere playing as many cards as possible before killing
            # the discard pile => remove 'KILL' from possible plays
            plays = [play for play in plays if play.action != 'KILL']

        # use the 'index >= 0' to make sure, that only card plays are left.
        plays = [play for play in plays if play.index >= 0]
        if len(plays) == 0:
            raise ValueError("Left with empty list of plays!")

        # play random face down table card.
        fdown_plays = [play for play in plays if play.action == 'FDOWN']
        if len(fdown_plays) > 0:
            # select a face down card at random
            return random.choice(fdown_plays)

        # select from the remaining face up table or hand card plays.
        top_non3 = discard.get_top_non3_rank()
        if top_non3 == '7' or top_non3 == 'K' or top_non3 == 'A':
            vmap = RANK_TO_VALUE_DRUCK   # '3' cheaper than '2'
        else:
            vmap = RANK_TO_VALUE         # '2' cheaper than '3'

        # play the cheapest legal 'HAND' or 'FUP' card.
        return self.find_cheapest_play(plays, vmap)

    def rank_to_play(self, rank, plays):
        """
        Find the card play with the specified rank.

        For card plays containing the action 'HAND', 'FUP', FDOWN, or 'GET'
        (pick face up table card(s) after taking the discard pile). 'FDOWN'
        cards are played blindly and therefore not considered here.
        In case of 'HAND', 'FUP', and 'GET' the play's index points at a card
        in the hand or the face up table cards of the player.

        :param rank:    rank of card we want to play.
        :type rank:     str
        :param plays:   list of legal plays.
        :type plays:    List
        :return:        card play of the specified rank or None => no match
        :rtype:         Play
        """
        for play in plays:
            if (play.action == 'HAND'
                    and self.hand[play.index].rank == rank):
                return play

            elif (play.action == 'FUP'
                  and self.face_up[play.index].rank == rank):
                return play

            elif (play.action == 'GET'
                  and self.face_up[play.index].rank == rank):
                return play

        # if we get here, there's no match
        return None

    def play_to_hash(self, play):
        '''
        Hash play for use in play sequence.

        We need a string representation of plays to create play sequence
        strings which can be used as keys into the playability cache.
        For plays where no actual card is played (TAKE, KILL, END, ...),
        we just use the action.
        For card plays (HAND, FUP, GET, ...) we use the rank of the card.

        :param play:        play
        :type play:         Play
        :return:            hash of play
        :rtype:             str
        '''
        # for card plays return the rank of the card.
        if play.action == 'HAND':
            if play.index > len(self.hand) - 1:
                print(f"### Play: {str(play)} Hand: {str(self.hand)}")
            return self.hand[play.index].rank
        elif play.action == 'FUP':
            return self.face_up[play.index].rank
        elif play.action == 'GET':
            return self.face_up[play.index].rank
        elif play.action == 'FDOWN':
            return self.face_down[play.index].rank
        elif play.action == 'PUT':
            return self.hand[play.index].rank
        elif play.action == 'SHOW':
            return self.hand[play.index].rank
        else:
            # for all others just return the action attribut
            return play.action

    def select_play(self, plays, state):
        '''
        Select one play from the list of legal plays.
        Abstract function implemented in the subclass (human or AI player).

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        '''
        raise NotImplementedError("This method must be implemented in the"
                                  " subclass")

    def play(self, state):
        '''
        Player plays one of the allowed actions.

        Depending on the curent game state, the player gets a list of possible
        plays (actions). He selects one and returns it.
        :param state:   shithead game state
        :type state:    State
        :return:        selected play
        :rtype:         Play
        '''
        # abort game if it's going too long
        if state.turn_count > len(state.players) * MAX_NOF_TURNS_PER_PLAYER:
            return Play('ABORT')
        plays = state.get_legal_plays()
        # select one of the legal plays according to sub-class strategy
        # and return it.
        return self.select_play(plays, state)

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        raise NotImplementedError("This method must be implemented in the"
                                  " subclass")

    def get_state(self):
        '''
        Get dictionary with player attributes.

        :return:    dictionary with player attributes.
        :rtype:     dict
        '''
        raise NotImplementedError("This method must be implemented in the"
                                  " subclass")

    def load_from_state(self, state):
        '''
        Loads player from state.

        :param state:    dictionary with player attributes.
        :type state:     dict
        '''
        raise NotImplementedError("This method must be implemented in the"
                                  " subclass")


# -----------------------------------------------------------------------------
class HumanPlayer(Player):
    '''
    Class representing a human shithead player.
    => human player is asked which of the legal plays he wants to play
       and selects either with a mouse click (gui), or by entering a number on
       the keyboard (cli).

    '''
    def __init__(self, name, gui=True, auto_end=False):
        '''
        Initialize a human shithead player.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.

        :param name:    player's name.
        :type name:     str
        :param gui:     True => uses graphical user interface for selection.
        :type gui:      bool
        :auto_end:      True => AI players don't wait for mouse click before
                                continuing.
        '''
        super().__init__(name)
        self.gui = gui              # True => gui, False => cli
        self.auto_end = auto_end    # True => automatically return 'END' play
        self.clicked_play = None    # play selected by mouse click.
        self.is_human = True        # True => human player
        self.fup_table = None       # human player never uses FUP table.

    def select_swap(self, plays):
        '''
        Select play during card swapping.

        Just a dummy function to avoid, that calling select_swap() in
        select_simulated_play() is marked as error by pylint.

        :param plays:   possible plays.
        :type plays:    list
        :return:        plays GET-0, GET-0, GET-0, PUT-x, PUT-y, PUT-z, END
        :rtype:         Play
        '''
        return Play('END')

    def set_clicked_play(self, play):
        '''
        The human player selects his play, by clicking on cards or buttons.

        Sets play = (action, index) in attribut 'clicked_play'.
        Resets selected play to None, if human player has not clicked on a
        card or button.
        'play' will not be None, if the human player is the current player and
        he has clicked on a card or button. But at this point, we do not check
        if this is a legal play. When the human player's select_play_by_gui()
        method is called, the selected play set with this method will be
        checked against the list of legal plays and reset to None unless it
        is in this list.

        :param play:    action, index set by mouse click.
        :type play:     Play or None
        '''
        self.clicked_play = play

    def select_play_by_cli(self, plays):
        '''
        Select one play from the list of legal plays with keyboard.

        Let human player select play.

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :return:        selected play.
        :rtype:         Play
        '''
        # a human player has the additional possibility to quit (end) the game.
        plays.append(Play('QUIT'))
        # present available plays to human player.
        for i, play in enumerate(plays):
            action = play.action
            index = play.index
            if action == 'HAND':
                print(f'{i}:PLAY-{self.hand[index]}', end=' ')
            elif action == 'FUP':
                print(f'{i}:PLAY-{self.face_up[index]}', end=' ')
            elif action == 'FDOWN':
                print(f'{i}:PLAY-{index}', end=' ')
            elif action == 'GET':
                print(f"{i}:GET-{self.face_up[index]}", end=' ')
            elif action == 'PUT':
                print(f"{i}:PUT-{self.hand[index]}", end=' ')
            elif action == 'SHOW':
                print(f"{i}:SHOW-{self.hand[index]}", end=' ')
            else:
                # actions with no index (card)
                print(f'{i}:{action}', end=' ')

        # loop until player has made a valid selection
        while True:
            s = input(f'\nSelect Play (0-{len(plays)-1}):')
            try:
                sel = int(s)
            except ValueError as err:
                print(err)
                print(f'Please enter an integer between 0 and {len(plays)-1}!')
                continue
            if sel < len(plays):
                # return the selected play
                return plays[sel]

    def select_play_by_gui(self, plays):
        '''
        Wait for human player to select legal play with mouse click.

        First resets the 'clicked_play' attribute and then waits in a loop for
        the human player to select a play by clicking on a card or button.
        If the selected play is in the list of legal plays, return it,
        otherwise reset 'clicked_play' and wait for another input.

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :return:        selected play or None if it wasn't legal.
        :rtype:         Play
        '''
        # if the human player is out 'OUT' is the only legal play
        if plays[0].action == 'OUT':
            return plays[0]

        play = None
        if self.clicked_play:
            # if human player has clicked on a card or button
            # create list of legal play strings
            legal_plays = [str(play) for play in plays]
            if str(self.clicked_play) in legal_plays:
                play = self.clicked_play

        # reset the clicked play (return it only once)
        self.clicked_play = None
        return play

    def select_play(self, plays, state):
        '''
        Human player makes one legal play.

        When using the gui, the human player is different than the AI players.
        While the AI players just select one of the legal plays, the human can
        select any play by clicking on a card or button. Only after the click,
        it is checked if this is a legal play. If not, 'None' is returned and
        the human player has to try again, i.e. the human player's 'play()'
        method is called 60 times per second by 'on_update()' until a valid
        selection has been made.
        The human player's mouse click during his turn sets the corresponding
        play as attribut 'clicked_play'. If 'clicked_play' has been set and
        is in the list of legal plays, it is returned and will be used to
        generate the next game state.
        Otherwise the 'clicked_play' attribut is reset to 'None' and 'None'
        is returned (displayed in the gui as player is thinking...), while
        select_play() is called again from on_update() with the same list of
        legal plays, since we are still in the same state.

        If the gui is not used, the player gets list of possible plays
        (actions) depending on the current game state.
        He selects one of them and returns it.

        :param plays:   possible plays.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play or None if selected play wasn't legal.
        :rtype:         Play
        '''
        if (self.auto_end and len(plays) == 1 and plays[0].action == 'END'):
            return Play('END')

        if self.gui:
            # select game with mouse click => may return None
            play = self.select_play_by_gui(plays)
        else:
            # select game with keyboard => always returns play
            play = self.select_play_by_cli(plays)

        return play

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        new_player = HumanPlayer(self.name, self.gui, self.auto_end)
        # number of turns played
        new_player.turn_count = self.turn_count
        # player's face down table cards
        new_player.face_down = self.face_down.copy()
        # player's face up table cards
        new_player.face_up = self.face_up.copy()
        # player's hand cards.
        new_player.hand = self.hand.copy()
        # must take face up table card as 2nd play
        new_player.get_fup = self.get_fup
        # rank of face up table card taken on 2nd play
        new_player.get_fup_rank = self.get_fup_rank
        # play 'END' automatically if it's the only option
        new_player.auto_end = self.auto_end

        return new_player

    def get_state(self):
        '''
        Get dictionary with player attributes.

        :return:    dictionary with player attributes.
        :rtype:     dict
        '''
        state = {}
        state['name'] = self.name
        state['turn_count'] = self.turn_count
        state['face_down'] = self.face_down.get_state()
        state['face_up'] = self.face_up.get_state()
        state['hand'] = self.hand.get_state()
        state['get_fup'] = self.get_fup
        state['get_fup_rank'] = self.get_fup_rank
        state['is_human'] = self.is_human
        state['gui'] = self.gui
        state['auto_end'] = self.auto_end
        return state

    def load_from_state(self, state):
        '''
        Loads player from state.

        :param state:    dictionary with player attributes.
        :type state:     dict
        '''
        self.name = state['name']
        self.turn_count = state['turn_count']
        self.face_down.load_from_state(state['face_down'])
        self.face_up.load_from_state(state['face_up'])
        self.hand.load_from_state(state['hand'])
        self.get_fup = state['get_fup']
        self.get_fup_rank = state['get_fup_rank']
        self.is_human = state['is_human']
        self.gui = state['gui']
        self.auto_end = state['auto_end']


# -----------------------------------------------------------------------------
class AiPlayer(Player):
    '''
    Class representing an AI shithead player.
    '''
    def __init__(self, name, fup_table, fdown_random=True):
        '''
        Initialize an AI shithead player.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.

        :param name:        player's name.
        :type name:         str
        :param fup_table:   face up table (None => don't swap).
        :type fup_table:    FupTable
        :param fdown_random:    True => select face down table cards at random.
        :type fdown_random:     bool
        '''
        super().__init__(name)      # set player's name
        self.fup_table = fup_table  # table with best fup card combinations.
        self.swap_count = 0         # state of face up table cards swapping
        self.best_fup = []          # list of 3 best face up table cards.
        # False => pick face down table cards from left to right (not random).
        self.fdown_random = fdown_random

    def select_swap(self, plays):
        '''
        Select play during card swapping.

        Selects 'GET' play during the 1st 3 plays => 6 cards on hand.
        Asks the face up table to provide the 3 card combination out of these 6
        hand cards with the highest score.
        Selects 'PUT' play for the 1st card in the best combination, as the
        next 3 plays, with each play also removing the 1st card from the best
        combination => loop through all 3 cards of best combination.
        Finally, select 'END' play to finish swapping cards.

        :param plays:   possible plays.
        :type plays:    list
        :return:        plays GET-0, GET-0, GET-0, PUT-x, PUT-y, PUT-z, END
        :rtype:         Play
        '''
        if self.swap_count < 3:
            # get face up table cards
            _plays = [play for play in plays if play.action == 'GET']
            if len(_plays) > 0:
                self.swap_count += 1
                return _plays[0]
            else:
                raise ValueError("Error getting face up table cards on hand!")
        elif self.swap_count >= 3 and self.swap_count < 6:
            # put hand to face up table cards
            if self.swap_count == 3:
                # 6 cards on hand => get best face up combination
                self.best_fup = self.fup_table.find_best(
                    [card for card in self.hand])

            # filter out 'PUT' plays
            _plays = [play for play in plays if play.action == 'PUT']

            # find 'PUT' play for 1st card in best_fup
            _plays = [play for play in _plays
                      if Card.cmp(
                          self.hand[play.index], self.best_fup[0]) == 0]
            if len(_plays) > 0:
                self.swap_count += 1
                self.best_fup.pop(0)    # remove 1st (put) card from best_fup
                return _plays[0]
            else:
                raise ValueError("Error putting hand cards to table!")
        else:
            # 3 cards on hand and best 3 cards on table
            _plays = [play for play in plays if play.action == 'END']
            if len(_plays) > 0:
                self.swap_count = 0     # reset swap counter
                return _plays[0]
            else:
                raise ValueError("Error swapping cards!")

    def select_play(self, plays, state):
        '''
        Select one play from the list of legal plays.
        Abstract function implemented in the subclass (e.g. DecepShit).

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        '''
        raise NotImplementedError("This method must be implemented in the"
                                  " subclass")

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        raise NotImplementedError("This method must be implemented in the"
                                  " subclass")

    def get_state(self):
        '''
        Get dictionary with player attributes.

        Note: we skip the reference to the fup_table,
        since it cannot be serialized (JSON).

        :return:    dictionary with player attributes.
        :rtype:     dict
        '''
        state = {}
        state['name'] = self.name
        state['turn_count'] = self.turn_count
        state['face_down'] = self.face_down.get_state()
        state['face_up'] = self.face_up.get_state()
        state['hand'] = self.hand.get_state()
        state['get_fup'] = self.get_fup
        state['get_fup_rank'] = self.get_fup_rank
        state['is_human'] = self.is_human
        state['swap_count'] = self.swap_count
        state['fdown_random'] = self.fdown_random
        state['best_fup'] = []
        for card in self.best_fup:
            state['best_fup'].append(card.get_state())
        return state

    def load_from_state(self, state):
        '''
        Loads player from state.

        :param state:    dictionary with player attributes.
        :type state:     dict
        '''
        self.name = state['name']
        self.turn_count = state['turn_count']
        self.face_down.load_from_state(state['face_down'])
        self.face_up.load_from_state(state['face_up'])
        self.hand.load_from_state(state['hand'])
        self.get_fup = state['get_fup']
        self.get_fup_rank = state['get_fup_rank']
        self.is_human = state['is_human']
        self.swap_count = state['swap_count']
        self.fdown_random = state['fdown_random']
        self.best_fup = []
        for cst in state['best_fup']:
            card = Card(cst['id'], cst['suit'], cst['rank'])
            card.seen = cst['seen']
            card.shown = cst['shown']
            card.is_face_up = cst['is_face_up']
            # add this card to the best_fup list
            self.best_fup.append(card)


# -----------------------------------------------------------------------------
class ShitHappens(AiPlayer):
    '''
    Class representing an AI player playing its cards at random.
    '''
    _count = 0   # counts number of ShitHappens instances.

    def __init__(self, name, fup_table=None, fdown_random=True):
        '''
        Initialize ShitHappens.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.

        :param name:            player's name.
        :type name:             str
        :param fup_table:       face up table (None => don't swap).
        :type fup_table:        FupTable
        :param fdown_random:    True => select face down table cards at random.
        :type fdown_random:     bool
        '''
        ShitHappens._count += 1   # count number of ShitHappens instances
        # set name, fup lookup table, and fdown mode in super class.
        super().__init__(name, fup_table, fdown_random)

    def select_play(self, plays, state):
        '''
        Select one play from the list of legal plays.

        ShitHappens:
            - swaps face up table with hand cards,
              if the fup lookup table has been set.
            - always shows the starting card, if it's on hand.
            - never voluntarily takes the discard pile.
            - always tries to play as many cards as possible.
            - when playing from hand:
                -- selects a playable card at random.
            - when playing from face up table cards:
                -- selects a playable card at random.
                -- after taking the discard pile,
                   get any face up card at random.
            - when playing from face down table cards:
                -- selects any card at random.

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        '''
        # handle all case where there is only one option:
        if len(plays) == 1:
            # only one option ('TAKE', 'REFILL', 'KILL', 'END', 'OUT')
            # => do it.
            return plays[0]

        # swap face up table cards with hand cards.
        if state.game_phase == SWAPPING_CARDS:
            if self.fup_table is None:
                return Play('END')  # don't swap cards.
            return self.select_swap(plays)

        # handle starting player auction:
        if state.game_phase == FIND_STARTER:
            # we only get here, if there's a card to show .
            # otherwise 'END' would be the only possible play.
            return plays[0]

        # never take discard pile voluntarily
        # => remove 'TAKE' from possible plays.
        plays = [play for play in plays if play.action != 'TAKE']
        if len(plays) == 1:
            return plays[0]

        # prefere playing cards to kill discard pile
        # => remove 'KILL' from possible plays
        plays = [play for play in plays if play.action != 'KILL']
        if len(plays) == 1:
            return plays[0]

        # prefere playing cards to end turn
        # => remove 'END' from possible plays
        plays = [play for play in plays if play.action != 'END']
        if len(plays) == 1:
            return plays[0]

        # if refill is an option do it (but, it should be a single option)
        refill = [play for play in plays if play.action == 'REFILL']
        if len(refill) > 0:
            return refill[0]

        # use 'index >= 0'
        # to make sure, that there are only card plays left.
        plays = [play for play in plays if play.index >= 0]
        if len(plays) == 0:
            raise ValueError("Left with empty list of plays!")

        # At this point the only legal plays left should be:
        #   - play a matching hand card
        #   - play a matching face up table card
        #   - get a face up table card on hand after taking the discard pile
        #   - playing any of the face down table cards
        # select one play at random
        return random.choice(plays)

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        new_player = ShitHappens(self.name, self.fup_table, self.fdown_random)
        new_player.swap_count = self.swap_count     # swap phase state
        new_player.best_fup = self.best_fup[:]      # best face up table cards
        new_player.turn_count = self.turn_count     # number of turns played
        new_player.face_down = self.face_down.copy()  # face down table cards
        new_player.face_up = self.face_up.copy()    # face up table cards
        new_player.hand = self.hand.copy()          # hand cards.
        # True => must take face up table card as 2nd play
        new_player.get_fup = self.get_fup
        # rank of face up table card taken on 2nd play
        new_player.get_fup_rank = self.get_fup_rank

        return new_player


# -----------------------------------------------------------------------------
class CheapShit(AiPlayer):
    '''
    Class representing an AI player always playing the cheapest card.
    '''
    _count = 0   # counts number of CheapShit instances.

    def __init__(self, name, fup_table=None, fdown_random=True):
        '''
        Initialize CheapShit.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.

        :param name:            player's name.
        :type name:             str
        :param fup_table:       face up table (None => don't swap).
        :type fup_table:        FupTable
        :param fdown_random:    True => select face down table cards at random.
        :type fdown_random:     bool
        '''
        CheapShit._count += 1
        super().__init__(name, fup_table, fdown_random)

    def select_play(self, plays, state):
        '''
        Select one play from the list of legal plays.

        CheapShit:
            - swaps face up table with hand cards,
              if the fup_table has been specified.
            - always shows the starting card, if it's on hand.
            - never voluntarily takes the discard pile.
            - only plays another card with value < 7 if the talon is not empty.
            - when playing from hand:
                -- selects the cheapest playable card.
            - when playing from face up table cards:
                -- selects the cheapest playable card.
                -- after taking the discard pile,
                   get the cheapest face up table card.
            - when playing from face down table cards:
                -- selects any card at random.

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        '''
        # handle all case where there is only one option:
        if len(plays) == 1:
            # only one option ('TAKE', 'REFILL', 'KILL', 'END', 'OUT')
            # => do it.
            return plays[0]

        # swap face up table cards with hand cards.
        if state.game_phase == SWAPPING_CARDS:
            if self.fup_table is None:
                return Play('END')  # don't swap cards.
            return self.select_swap(plays)

        # handle starting player auction:
        if state.game_phase == FIND_STARTER:
            # we only get here, if there's a card to show .
            # otherwise 'END' would be the only possible play.
            return plays[0]

        # never take discard pile voluntarily
        # => remove 'TAKE' from possible plays.
        plays = [play for play in plays if play.action != 'TAKE']
        if len(plays) == 1:
            return plays[0]

        # prefere playing cards to kill discard pile
        # => remove 'KILL' from possible plays
        plays = [play for play in plays if play.action != 'KILL']
        if len(plays) == 1:
            return plays[0]

        # if refill is an option do it
        refill = [play for play in plays if play.action == 'REFILL']
        if len(refill) > 0:
            return refill[0]

        # check if we could play another card or end the turn:
        if self.play_again_or_end(plays):
            # play card if talon is empty or its value is < 7 ('Q')
            if (len(state.talon) == 0
                    or RANK_TO_VALUE_CHEAP_SHIT[state.discard.get_top_rank()]
                    < HOLD_BACK_VALUE):
                # remove 'END' play => play card
                plays = [play for play in plays if play.action != 'END']
            else:
                return Play('END')  # => end turn

        # use 'index >= 0'
        # to make sure, that there are only card plays left.
        plays = [play for play in plays if play.index >= 0]
        if len(plays) == 0:
            raise ValueError("Left with empty list of plays!")

        # At this point the only legal plays left should be:
        #   - play a matching hand card
        #   - play a matching face up table card
        #   - get a face up table card on hand after taking the discard pile
        #   - playing any of the face down table cards
        if plays[0].action == 'FDOWN':
            if self.fdown_random:
                # select face down table cards randomly
                return random.choice(plays)
            else:
                # for AI evaluation pick from left to right\
                # => each AI player plays once with all card sets
                #    => minimize randomness when evaluating players.
                return plays[0]
        else:
            # play the cheapest hand or face up table card,
            # or take the cheapest face up table card on hand.
            # CheapShit uses a slightly different map than other AI players.
            cheapest = self.find_cheapest_play(plays, RANK_TO_VALUE_CHEAP_SHIT)
            return cheapest

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        new_player = CheapShit(self.name, self.fup_table, self.fdown_random)
        new_player.swap_count = self.swap_count     # swap phase state
        new_player.best_fup = self.best_fup[:]      # best face up table cards
        new_player.turn_count = self.turn_count     # number of turns played
        new_player.face_down = self.face_down.copy()  # face down table cards
        new_player.face_up = self.face_up.copy()     # face up table cards
        new_player.hand = self.hand.copy()           # hand cards.
        # True => must take face up table card as 2nd play
        new_player.get_fup = self.get_fup
        # rank of face up table card taken on 2nd play
        new_player.get_fup_rank = self.get_fup_rank

        return new_player


# -----------------------------------------------------------------------------
class TakeShit(AiPlayer):
    '''
    Class representing an AI player with some improvements (?) to CheapShit.

    TakeShit voluntarily takes the discard pile, if it has good cards in it and
    there's a chance to get rid of them before the talon runs out.
    '''
    _count = 0   # counts number of TakeShit instances.

    def __init__(self, name, fup_table=None, fdown_random=True):
        '''
        Initialize TakeShit.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.

        :param name:            player's name.
        :type name:             str
        :param fup_table:       face up table (None => don't swap).
        :type fup_table:        FupTable
        :param fdown_random:    True => select face down table cards at random.
        :type fdown_random:     bool
        '''
        TakeShit._count += 1
        super().__init__(name, fup_table, fdown_random)

    def select_play(self, plays, state):
        '''
        Select one play from the list of legal plays.

        TakeShit:
            - swaps cards if fup_table has been specified.
            - always shows the starting card, if it's on hand.
            - if possible, plays a card of same rank as the top discard pile
              card as 1st card, if there are 3 cards of same rank at the top
              of the discard pile.
            - voluntarily takes the discard pile:
                -- if he has more than 3 cards on hand and taking the discard
                   pile decrements the number of turns to get rid of these
                   cards.
                -- if the discard pile contains only ranks he already has on
                   hand plus good cards ('2', '3', 'Q', 'K', 'A') and if it
                   should be possible to get back to 3 hand cards before the
                   talon runs out.
            - only plays again if it's a low card (4, 5, 6, 7, 8, 9, J) or if
              the talon is empty.
            - when playing from hand:
                -- selects the cheapest playable card,
                   but '3' over '2' on '7', 'K', 'A' (Druck mache!)
            - when playing from face up table cards:
                -- selects the cheapest playable card.
                   but '3' over '2' on '7', 'K', 'A' (Druck mache!)
                -- after taking the discard pile,
                   get the cheapest face up table card.
            - when playing from face down table cards:
                -- selects any card at random.
            - doesn't play another '8' if only 2 players are left.
              => plays '8', ends turn, other player skipped, plays '8', ...
            - always refills on 'Q' or empty discard pile.
            - plays as many bad cards (4, 5, 6, 7) as possible before refill,
              but refills before playing another good (2, 3, 10, Q, K, A)
              or medium card (8, 9, J).

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        '''
        discard = state.discard     # discard pile

        # handle all case where there is only one option:
        if len(plays) == 1:
            # only one option ('TAKE', 'REFILL', 'KILL', 'END', 'OUT')
            # => do it.
            return plays[0]

        # swap face up table cards with hand cards.
        if state.game_phase == SWAPPING_CARDS:
            if self.fup_table is None:
                return Play('END')  # don't swap cards.
            return self.select_swap(plays)

        # handle starting player auction:
        if state.game_phase == FIND_STARTER:
            # we only get here, if there's a card to show .
            # otherwise 'END' would be the only possible play.
            return plays[0]

        # always try to kill the discard pile with the 1st play
        if state.n_played == 0 and state.discard.get_ntop() == 3:
            # find the 'HAND' or 'FUP' play with the same rank as the card at
            # the top of the discard pile
            play = self.rank_to_play(state.discard.get_top_rank(), plays)
            if play is not None:
                discard = [card.rank for card in state.discard]
                return play

        _plays = [play for play in plays if play.action == 'TAKE']
        if len(_plays) > 0:
            # 'TAKE' is one of several legal plays => check if we should do it
            if self.take_discard_or_not(state):
                return Play('TAKE')

        # play another card of same rank or end turn?
        if self.play_again_or_end(plays):
            # don't play '8' if only 2 players left.
            top_rank = discard.get_top_rank()
            if top_rank == '8' and len(state.players) == 2:
                return Play('END')  # => end turn

            # play card if talon is empty or its value is < 7 ('Q')
            if (len(state.talon) == 0 or
                    RANK_TO_VALUE[state.discard.get_top_rank()] < 7):
                # remove 'END' play => play card
                plays = [play for play in plays if play.action != 'END']
            else:
                return Play('END')  # => end turn

        # play another card of same rank or refill first
        if self.refill_or_play_again(plays):
            # alway refill 1st on 'Q' or empty discard pile.
            top_rank = discard.get_top_rank()   # None => empty
            if top_rank is None or top_rank == 'Q':
                return Play('REFILL')
            if (top_rank == '4'
                    or top_rank == '5'
                    or top_rank == '6'
                    or top_rank == '7'):
                # play bad cards before refilling => kill pile first
                # remove 'REFILL' => play card
                plays = [play for play in plays if play.action != 'REFILL']
            else:
                # refill before playing another good or medium card.
                return Play('REFILL')

        # play another card of same rank or kill the discard pile?
        if self.kill_or_play_again(plays):
            # prefere playing as many cards as possible before killing
            # the discard pile => remove 'KILL' from possible plays
            plays = [play for play in plays if play.action != 'KILL']

        # 'index >= 0'
        # to make sure, that there are only card plays left.
        plays = [play for play in plays if play.index >= 0]
        if len(plays) == 0:
            raise ValueError("Left with empty list of plays!")

        # At this point the only legal plays left should be:
        #   - play a matching hand card
        #   - play a matching face up table card
        #   - get a face up table card on hand after taking the discard pile
        #   - playing any of the face down table cards
        if plays[0].action == 'FDOWN':
            if self.fdown_random:
                # select face down table cards randomly
                return random.choice(plays)
            else:
                # for AI evaluation pick from left to right
                # => each AI player plays once with all card sets
                #    => minimize randomness when evaluating players.
                return plays[0]
        elif plays[0].action == 'GET':
            # select one of the cheapest face up table cards to take on hand.
            return self.find_cheapest_play(plays, RANK_TO_VALUE)
        else:
            # when playing matching hand or face up table cards wie use the
            # 'Druck mache!' strategie, i.e. if there's a '7', 'K', or 'A' on
            # the discard pile, we play a '3' before the '2' to turn on the
            # heat for the next player.
            top_non3 = discard.get_top_non3_rank()
            if top_non3 == '7' or top_non3 == 'K' or top_non3 == 'A':
                vmap = RANK_TO_VALUE_DRUCK   # '3' cheaper than '2'
            else:
                vmap = RANK_TO_VALUE         # '2' cheaper than '3'
            return self.find_cheapest_play(plays, vmap)

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        new_player = TakeShit(self.name, self.fup_table, self.fdown_random)
        new_player.swap_count = self.swap_count     # swap phase state
        new_player.best_fup = self.best_fup[:]      # best face up table cards
        new_player.turn_count = self.turn_count     # number of turns played
        new_player.face_down = self.face_down.copy()  # face down table cards
        new_player.face_up = self.face_up.copy()    # face up table cards
        new_player.hand = self.hand.copy()          # hand cards.
        # True => must take face up table card as 2nd play
        new_player.get_fup = self.get_fup
        # rank of face up table card taken on 2nd play
        new_player.get_fup_rank = self.get_fup_rank

        return new_player


# -----------------------------------------------------------------------------
class BullShit(AiPlayer):
    '''
    Class representing an AI player using the analyzer module.

    Uses probability calculations to selecet a play.
    !!! Doesn't work as expected, therefore called BullShit !!!.
    '''
    _count = 0   # counts number of BullShit instances.

    def __init__(self, name, fup_table=None, fdown_random=True):
        '''
        Initialize Analyzer.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.

        :param name:            player's name.
        :type name:             str
        :param fup_table:       face up table (None => don't swap).
        :type fup_table:        FupTable
        :param fdown_random:    True => select face down table cards at random.
        :type fdown_random:     bool
        '''
        BullShit._count += 1
        super().__init__(name, fup_table, fdown_random)

    def find_take_playability(self, state):
        """
        Find playability when player voluntarily takes the discard pile.

        'TAKE' is only possible as very first action in a player's turn and
        immediately ends his turn. I.e. there's no recursion involved.
        We just evaluate the player's hand after the 'TAKE' action to find its
        playability and the smallest number of turns necessary to get rid of
        these cards. We use the found number of turns as initial hand size to
        estimate the number of cards this player will have in hand, than the
        1st player has gotten rid of his hand cards and starts playing face up
        table cards. If the estimated number is too large, the playability is
        reduced to 0, because it's too risky to take the discard pile.

        :param state:       current state of the game.
        :type state:        State
        :return:            playability after 'TAKE' play.
        :rtype:             float
        """
        if len(state.talon) == 0:
            # talon is empty => never take the discard pile voluntarily
            return 0

        # make a copy of the current state
        next_state = state.copy()

        # apply 'TAKE' play to the current state
        next_state = Game.next_state(next_state, Play('TAKE'))

        # player takes discard pile voluntarily
        # 'TAKE' ends players turn => evaluate players hand
        analyzer = Analyzer(next_state, self.name)
        # calculate the average playability of the hand cards
        playab = analyzer.calc_avg_playability(False)
        # and the minimum number of turns to get rid of them
        n_turns = analyzer.get_number_of_turns(False)

        # estimate the number of cards in player's hand, when the 1st player
        # gets rid of all hand cards.
        # we assume that the player can get rid of 1 card per turn, therefore
        # we set his initial hand size equal to the number of turns calculated
        # by the analyzer.
        rem_hand = state.estimate_remaining_hand(n_turns)
        if rem_hand > TAKE_LIMIT:
            # Too many cards on hand when 1st opponent gets rid of all hand
            # cards => don't voluntarily take the discard pile
            playab = 0

        return playab

    def find_refill_playability(self, state, depth, cache, playseq):
        """
        Find playability when player refills its hand.

        Since the 'REFILL' action uncovers the top talon card, using the
        original state would be cheating. Therefore, we replace the top talon
        card with a dummy card (rank = '0') before refilling the hand.
        The replaced cards are added to the burnt cards, they are still unknown
        (we need them for the playability calculation).
        After the refill, it is possible that more cards can be played (same
        rank as 1st card, or after '10'/'Q' etc., but not the dummy cards!!!).
        I.e. we call find_best_playability() recursively. Since 'REFILL' is
        only a legal play if the player has less than 3 cards on hand, we
        shouldn't get into the 'too many recursions' problem.
        The recursion ends after an 'END' play or if there are only dummy cards
        left in the player's hand.
        NOTE: if there are 3 dummy cards on hand after killing the discard pile
              or playing a 'Q', we have to calculate the hand playability
              prematurely, since dummy cards cannot be played on the discard
              pile.
        When calculating the playability of the remaining hand cards, each
        dummy card has the average playability of the remaining unknown cards.

        :param state:       current state of the game.
        :type state:        State
        :param depth:       recursion depth
        :type depth:        int
        :param cache:       playability cache.
        :type cache:        dict
        :param playseq:     key for playability cache.
        :type playseq:      str
        :return:            playability after 'TAKE' play.
        :rtype:             float
        """
        if len(state.talon) == 0:
            # talon is empty => cannot refill hand
            # should not happen (=> get_legal_plays()), just to be sure
            return 0

        # make a copy of the current state
        next_state = state.copy()
        # refilling means uncovering unknown cards, doing this with the
        # current state would be cheating.
        # => replace the top talon cards (-> burnt) with dummy cards
        nof_refills = 3 - len(next_state.players[next_state.player].hand)
        nof_refills = min(nof_refills, len(next_state.talon))
        for _ in range(nof_refills):
            # move top talon cards to the burnt cards
            next_state.burnt.add_card(next_state.talon.pop_card())
            next_state.n_burnt += 1
        for _ in range(nof_refills):
            # put same number of dummy cards on top of the talon
            next_state.talon.add_card(Card(0, 'Clubs', '0'))
        # apply specified play to the current state
        # => dummy cards are moved from talon to player's hand
        next_state = Game.next_state(next_state, Play('REFILL'))
        # count number of dummy cards in hand
        hand = next_state.players[next_state.player].hand
        dummies = [card for card in hand if card.rank == '0']
        if len(dummies) == 3:
            # 3 dummy cards on hand => stop recursion
            # return the average playability of 3 talon cards
            analyzer = Analyzer(state, self.name)
            playab = analyzer.calc_avg_playability(False)
            return playab

        # => play more cards or 'END'
        best_playab = 0
        legal_plays = next_state.get_legal_plays()
        for next_play in legal_plays:
            playab = self.find_best_playability(
                next_state, next_play, depth + 1, cache, playseq)
            if playab == -1:
                # finding best playability failed (too many recursions)
                return -1
            best_playab = max(playab, best_playab)

        return best_playab

    def find_best_playability(self, state, play, depth, cache, playseq):
        """
        Find best playability for play applied to specified state.

        Apply the specified play to the specified state. If the resulting state
        has a new current player, calculate the playablility of the previous
        player's hand or face up table cards and return it. Otherwise, call
        find_best_playability() recursively for each of the legal plays of this
        new state and return the highest playability found this way.

        :param state:           game state.
        :type state:            State
        :param play:            legal play in this game state.
        :type play:             Play
        :param depth:           recursion depth
        :type depth:            int
        :param cache:           playability cache
        :type cache:            dict
        :param playseq:         play sequence
        :type playseq:          str
        :return:                best playability after this play.
        :rtype:                 float
        """
        if len(playseq) > 0:
            # expand existing play sequence
            playseq += '-'
        # add play to play sequence
        playseq += self.play_to_hash(play)

        if cache is not None:
            if playseq in cache:
                # we already know the playability for this sequence
                return cache[playseq]

            if len(cache) > MAX_RECURSIONS:
                # cache grows too big => recursion takes too long
                return -1   # break out of recursion

        if play.action == 'TAKE':
            # playability after taking the discard pile voluntarily
            return self.find_take_playability(state)

        if play.action == 'REFILL':
            # refilling means uncovering unknown cards, doing this with the
            # original state would be cheating.
            # => refill with dummy cards (= average talon card playability)
            return self.find_refill_playability(state, depth, cache, playseq)

        if play.action == 'HAND' and self.hand[play.index].rank == '0':
            # don't recursively follow the play of dummy cards
            return 0

        # all other cases, apply play to a copy of the current state
        next_state = state.copy()
        next_state = Game.next_state(next_state, play)
        best_playab = 0
        # check if this player's turn is finished
        if next_state.players[next_state.player].name != self.name:
            # current player has changed
            # => calculate value of previous player's remaining cards.
            analyzer = Analyzer(next_state, self.name)
            best_playab = analyzer.calc_avg_playability(False)
        else:
            plays = next_state.get_legal_plays()
            # call find_best_playability() recursively for each of the legal
            # plays of the new state and return the highest value found.
            for next_play in plays:
                playab = self.find_best_playability(
                    next_state, next_play, depth + 1, cache, playseq)
                if playab == -1:
                    return -1   # break out of recursions
                best_playab = max(playab, best_playab)
        if cache is not None:
            # add playability found for this sequence of play to the cache
            cache[playseq] = best_playab
        return best_playab

    def select_by_playability(self, plays, state):
        """
        Select play with best playability.

        Select the best play by calculating the playability of the player's
        remaining cards after each possible play has been applied to the
        current state.

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        """
        cache = {}      # playability cache
        playseq = ''    # play sequence used as key for the playability cache
        best_playab = 0
        best_play = plays[0]

        if len(state.talon) == 0 and len(plays) > 1:
            # remove 'END" from possible plays
            # => always play more cards of same rank if talon is empty
            plays = [play for play in plays if play.action != 'END']

        if len(plays) == 1:
            # only one play left after removing 'END'
            return plays[0]

        # find play with best playability
        for play in plays:
            playab = self.find_best_playability(
                state, play, 1, cache, playseq)
            if playab == -1:
                # finding best playability failed (too many recursions)
                return Play('ABORT')
            if playab > best_playab:
                best_playab = playab
                best_play = play
        return best_play

    def select_play(self, plays, state):
        '''
        Select one play from the list of legal plays.

        BullShit:
            - swaps cards if fup_table has been specified.
            - always shows the starting card, if it's on hand.
            - calculates playability of hand cards after 'TAKE' and the minimum
              number of turns to get rid of these cards, in order to decide
              whether taking the discard pile is worth it.
            - calculates playability for each possile play combination this
              turn to decide which card to play first.
            - calculates playability for each possile play combination this
              turn to decide, whether to play another card or to kill the
              discard pile.
            - calculates playability for each possile play combination this
              turn to decide, whether to play another card or to end.
            - calculates playability for each possile play combination this
              turn to decide, which card(s) to pick up after taking the discard
              pile, playing from face up table cards.
            - plays '3' before '2' if '7', 'K', or 'A' is on top of the discard
              pile (Druck mache!).
            - when playing from face down table cards:
                -- selects any card at random.
            - TODO doesn't play another '8' if only 2 players are left.
              => plays '8', ends turn, other player skipped, plays '8', ...

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        '''
        # handle all cases where there is only one option:
        if len(plays) == 1:
            # only one option ('TAKE', 'REFILL', 'KILL', 'END', 'OUT')
            # => do it.
            return plays[0]

        # swap face up table cards with hand cards.
        if state.game_phase == SWAPPING_CARDS:
            if self.fup_table is None:
                return Play('END')  # don't swap cards.
            return self.select_swap(plays)

        # handle starting player auction:
        if state.game_phase == FIND_STARTER:
            # we only get here, if there's a card to show .
            # otherwise 'END' would be the only possible play.
            return plays[0]

        # get a list of available actions
        actions = set([play.action for play in plays])

        # check if we have to play a face down table card
        if 'FDOWN' in actions:
            _plays = [play for play in plays if play.action == 'FDOWN']
            if self.fdown_random:
                # select face down table cards randomly
                return random.choice(_plays)
            # for AI evaluation pick from left to right
            return _plays[0]

        # if we get here, we are in the PLAY_GAME phase,
        # with more than 1 plays to select from, no FDOWN plays,
        # => select play by calculating playability after play
        best_play = self.select_by_playability(plays, state)
        if best_play.action != 'ABORT':
            return best_play

        # finding play with best playability failed (too many recursions)
        # => just play the worst playable card (CheapShit strategy)
        if 'HAND' in actions:
            # player plays from hand cards
            if 'END' in actions:
                # not 1st play this turn
                # => play another hand card (same rank as before)
                _plays = [play for play in plays if play.action == 'HAND']
                rank = self.hand[_plays[0].index].rank
                if rank in ('2', '3', 'A', 'K', '10'):
                    # don't waste good cards
                    return Play('END')

                # play another card with this rank
                return _plays[0]

            # 1st play this turn
            # => play the worst playable card
            hand_plays = [play for play in plays if play.action == 'HAND']
            cheapest = self.find_cheapest_play(
                hand_plays, RANK_TO_VALUE_CHEAP_SHIT)
            return cheapest

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        new_player = BullShit(self.name, self.fup_table, self.fdown_random)
        new_player.swap_count = self.swap_count     # swap phase state
        new_player.best_fup = self.best_fup[:]      # best face up table cards
        new_player.turn_count = self.turn_count     # number of turns played
        new_player.face_down = self.face_down.copy()  # face down table cards
        new_player.face_up = self.face_up.copy()    # face up table cards
        new_player.hand = self.hand.copy()          # hand cards.
        # True => must take face up table card as 2nd play
        new_player.get_fup = self.get_fup
        # rank of face up table card taken on 2nd play
        new_player.get_fup_rank = self.get_fup_rank

        return new_player


def run_simulation(state, play):
    '''
    Run a simulation of the current state for the specified play.

    We make a copy of the specified state and apply the specified play for
    the current player. From there, we play out the game using the same
    strategy ('Player.select_simulated_play()') for each of the players.
    Finally we return the score (number of players left then going out,
    0 => shithead) of the current player.

    :param state:   original state from which we start the simulation.
    :type state:    State
    :param play:    play for which we run the simulation.
    :type play:     Play
    :return:        score which tells us the outcome of the simumaltion for
                    the current player, or -1 => game aborted.
    :rtype:         int
    '''
    # copy the state.
    sim = state.copy()
    # store the name of the simulated player
    # (= current player at the begin of the simulation)
    sim_player = sim.players[sim.player].name
    # maximum number of turns after which the game shall be aborted
    max_nof_turns = len(sim.players) * MAX_NOF_TURNS_PER_PLAYER
    # start the simulation with the specified play
    sim = Game.next_state(sim, play, None, None)
    # Now we keep playing the game using 'Player.select_simulated_play()'
    while len(sim.players) > 1:
        # let the current player play one action
        player = sim.players[sim.player]

        # abort game if it's going too long
        if sim.turn_count > max_nof_turns:
            return -1   # deadlock => abort this simulation
        else:
            # get legal plays for this state
            plays = sim.get_legal_plays()
            # we use the same select function for all players
            next_play = player.select_simulated_play(plays, sim)

        # check if the simulated player is out => return score
        if next_play.action == 'OUT' and player.name == sim_player:
            return len(sim.players) - 1

        # apply this  action to the current state to get to the next state
        sim = Game.next_state(sim, next_play, None, None)

    # if we get here, the simulated player is the shithead => return score 0
    return 0


# -----------------------------------------------------------------------------
class SelectSimulatedPlayThread(Thread):
    """
    Thread for running multiple simulations for game state.

    Running multiple simulations from a game state to find the best possible
    play may take some time. Therefore, we start it in a seperate thread.
    """
    def __init__(self, state, plays):
        '''
        Initializer.

        :param state:   original state from which we start the simulation.
        :type state:    State
        :param plays:   list of possible plays for which we run the simulation.
        :type plays:    List
        '''
        Thread.__init__(self)       # call super class initializer
        self.state = state.copy()   # copy of the original game state
        self.plays = plays          # possible plays we have to select from
        self.selected_play = None   # used to return the the found best play

    def run(self):
        '''
        Thread function to simulating the outcome of legal plays.

        Copies the specified state and randomly redistribute all unknown cards
        (except for the unknown cards in the current player's hand).
        Runs based on this new state one simulation per entry in the list of
        plays and uses the returned score (number of opponents still in the
        game, when the current player went out) to select the best play.
        '''
        # initialize score list with one entry per play
        scores = [0 for x in self.plays]
        # calculate the number of different simulation states
        for _ in range(NOF_SIMULATIONS_PER_PLAY):
            # copy the original state and redistribute the unknown cards.
            sim = State.simulation_state(self.state)
            for j, play in enumerate(self.plays):
                score = run_simulation(sim, play)
                if score < 0:
                    # treat deadlocks like lost games
                    score = 0
                # add to total score of this play
                scores[j] += score
        # find the highest value in the score list.
        max_score = max(scores)
        # combine plays and scores
        scored_plays = zip(self.plays, scores)
        # make a new list containing only plays with maximum score
        best_plays = [x[0] for x in list(scored_plays) if x[1] == max_score]
        # randomly select one of the best plays
        self.selected_play = random.choice(best_plays)


# -----------------------------------------------------------------------------
class DeepShit(AiPlayer):
    '''
    Class representing an AI player which uses simulation.
    '''
    _count = 0   # counts number of DeepShit instances.

    def __init__(self, name, fup_table=None, fdown_random=True):
        '''
        Initialize DeepShit.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.

        :param name:        player's name.
        :type name:         str
        :param fup_table:   face up table (None => don't swap).
        :type fup_table:    FupTable
        '''
        DeepShit._count += 1
        super().__init__(name, fup_table, fdown_random)
        # thread for play selection by simulation
        self.thread = None
        # flag indicating, that thread has already been started.
        self.thread_started = False

    def select_play(self, plays, state):
        '''
        Select one play from the list of legal plays.

        Uses the same initial strategy as TakeShit:
            - swaps cards if fup_table has been specified.
            - always shows the starting card, if it's on hand.
            - if possible, plays a card of same rank as the top discard pile
              card as 1st card, if there are 3 cards of same rank at the top
              of the discard pile.
            - voluntarily takes the discard pile:
                -- if he has more than 3 cards on hand and taking the discard
                   pile decrements the number of turns to get rid of these
                   cards.
                -- if the discard pile contains only ranks he already has on
                   hand plus good cards ('2', '3', 'Q', 'K', 'A') and if it
                   should be possible to get back to 3 hand cards before the
                   talon runs out.
            - only plays again if it's a low card (4, 5, 6, 7, 8, 9, J) or if
              the talon is empty.
            - when playing from hand:
                -- selects the cheapest playable card,
                   but '3' over '2' on '7', 'K', 'A' (Druck mache!)
            - when playing from face up table cards:
                -- selects the cheapest playable card.
                   but '3' over '2' on '7', 'K', 'A' (Druck mache!)
                -- after taking the discard pile,
                   get the cheapest face up table card.
            - when playing from face down table cards:
                -- selects any card at random.
            - doesn't play another '8' if only 2 players are left.
              => plays '8', ends turn, other player skipped, plays '8', ...
            - always refills on 'Q' or empty discard pile.
            - plays as many bad cards (4, 5, 6, 7) as possible before
              refilling, but refills before playing another good (2, 3, 10, Q,
              K, A) or medium card (8, 9, J).

        But during the end game (i.e. talon is empty and  only 2 player's left)
        he uses simulation to find the best play. Multiple simulation with the
        possible distributions of still unknown cards are run, each time using
        one of the specified legal plays as opening play. The rest of each
        simulated game is played out using the 'Player.select_simulated_play()'
        method for each of the players. The result is then used to score the
        opening play and the play with the highest score after all simulations
        are run, is finally selected to be played in the actual game.

        Since running multiple simulations may take some time, we do this in a
        seperate thread. We 1st check if a thread has already been started by
        checking the 'thread_started' flag:
            - yes => if thread is still running return None (thinking...)
                  => if thread has finished reset the 'thread_started' flag
                     and return the play selected by the thread.
            - no => 1st handle the simple cases (only one play in list, etc.)
                    2nd create a new thread, start it,
                    and set the 'thread_started' flag.
                    Then return None, so the caller can continue.

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        '''
        # check if the SelectSimulatedPlayThread has been started before
        if self.thread and self.thread_started:
            # check if the SelectSimulatedPlayThread has finished
            if self.thread.is_alive():
                # not finished yet
                return None  # => tell caller that AI player is still thinking
            else:
                # thread has finished => return selected play
                self.thread_started = False     # reset flag
                return self.thread.selected_play

        # no pending thread => 1st handle the simple cases
        # handle all case where there is only one option:
        if len(plays) == 1:
            # only one option ('TAKE', 'REFILL', 'KILL', 'END', 'OUT')
            # => do it.
            return plays[0]

        # swap face up table cards with hand cards.
        if state.game_phase == SWAPPING_CARDS:
            if self.fup_table is None:
                return Play('END')  # don't swap cards.
            return self.select_swap(plays)

        # handle starting player auction:
        if state.game_phase == FIND_STARTER:
            # we only get here, if there's a card to show .
            # otherwise 'END' would be the only possible play.
            return plays[0]

        # if we can play face down table cards always select one at random
        # (never take the discard pile).
        fdown_plays = [play for play in plays if play.action == 'FDOWN']
        if len(fdown_plays) > 0:
            if self.fdown_random:
                return random.choice(fdown_plays)
            else:
                # eliminate randomness by playing face down table cards
                # from left to right for AI evaluation.
                return fdown_plays[0]

        # as long as the talon is not empty and there are more than 2 players
        # we use the usual strategies
        if len(state.talon) > 0 or len(state.players) > 2:

            # shortcut to discard pile
            discard = state.discard

            # always try to kill the discard pile with the 1st play
            if state.n_played == 0 and state.discard.get_ntop() == 3:
                # find the 'HAND' or 'FUP' play with the same rank as the card
                # at the top of the discard pile
                play = self.rank_to_play(state.discard.get_top_rank(), plays)
                if play is not None:
                    return play

            _plays = [play for play in plays if play.action == 'TAKE']
            if len(_plays) > 0:
                # 'TAKE' is one of several legal plays
                # => check if we should do it
                if self.take_discard_or_not(state):
                    return Play('TAKE')

            # play another card of same rank or end turn?
            if self.play_again_or_end(plays):
                # play card if its value is < 7 ('Q')
                if RANK_TO_VALUE[state.discard.get_top_rank()] < 7:
                    # remove 'END' play => play card
                    plays = [play for play in plays if play.action != 'END']
                else:
                    return Play('END')  # => end turn

            # play another card of same rank or refill first
            if self.refill_or_play_again(plays):
                # alway refill 1st on 'Q' or empty discard pile.
                top_rank = discard.get_top_rank()   # None => empty
                if top_rank is None or top_rank == 'Q':
                    return Play('REFILL')
                if (top_rank == '4'
                        or top_rank == '5'
                        or top_rank == '6'
                        or top_rank == '7'):
                    # play bad cards before refilling => kill pile first
                    # remove 'REFILL' => play card
                    plays = [play for play in plays if play.action != 'REFILL']
                else:
                    # refill before playing another good or medium card.
                    return Play('REFILL')

            # play another card of same rank or kill the discard pile?
            if self.kill_or_play_again(plays):
                # prefere playing as many cards as possible before killing
                # the discard pile => remove 'KILL' from possible plays
                plays = [play for play in plays if play.action != 'KILL']

            # use 'index >= 0'
            # to make sure, that there are only card plays left.
            card_plays = [play for play in plays if play.index >= 0]
            if len(card_plays) == 0:
                raise ValueError("Left with empty list of plays!")

            # only 'HAND', 'FUP', or 'GET' plays left ('FDOWN' plays were
            # already handled).
            if card_plays[0] == 'GET':
                # take the cheapest face up table card on hand.
                return self.find_cheapest_play(card_plays, RANK_TO_VALUE)
            else:
                # when playing matching hand or face up table cards wie use the
                # 'Druck mache!' strategie, i.e. if there's a '7', 'K', or 'A'
                # on the discard pile, we play a '3' before the '2' to turn on
                # the heat for the next player.
                top_non3 = discard.get_top_non3_rank()
                if top_non3 == '7' or top_non3 == 'K' or top_non3 == 'A':
                    # 7, K, or A => play 3 before 2
                    vmap = RANK_TO_VALUE_DRUCK   # '3' cheaper than '2'
                else:
                    vmap = RANK_TO_VALUE         # '2' cheaper than '3'
                # select the cheapest 'HAND' or 'FUP' play
                return self.find_cheapest_play(card_plays, vmap)
        else:
            # if the talon is empty and there are only 2 players left,
            # we use simulation to find the best play
            self.thread = SelectSimulatedPlayThread(state, plays)
            self.thread.start()
            self.thread_started = True
            return None     # tell caller that AI player is thinking

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        new_player = DeepShit(self.name, self.fup_table, self.fdown_random)
        new_player.swap_count = self.swap_count     # swap phase state
        new_player.best_fup = self.best_fup[:]      # best face up table cards
        new_player.turn_count = self.turn_count     # number of turns played
        new_player.face_down = self.face_down.copy()  # face down table cards
        new_player.face_up = self.face_up.copy()    # face up table cards
        new_player.hand = self.hand.copy()          # hand cards.
        # True => must take face up table card as 2nd play
        new_player.get_fup = self.get_fup
        # rank of face up table card taken on 2nd play
        new_player.get_fup_rank = self.get_fup_rank

        return new_player


# -----------------------------------------------------------------------------
class SelectMctsThread(Thread):
    """
    Thread for running Monte Carlo Tree Search for game state.

    Building a search tree to find the best possible play may take some time.
    Therefore, we start it in a seperate thread.
    """
    def __init__(self, state, timeout=3.0, policy='max', verbose=False):
        '''
        Initializer.

        :param state:   original state from which we start the simulation.
        :type state:    State
        :param plays:   list of possible plays for which we run the simulation.
        :type plays:    List
        :param verbose:     True => print MCTS statistics.
        :type verbose:      bool
        '''
        Thread.__init__(self)   # call super class initializer
        self.state = state.copy()   # copy of the original game state
        self.timeout = timeout
        self.policy = policy
        self.verbose = verbose
        self.mcts = MonteCarlo(Game)    # create search tree
        self.selected_play = None   # attribute to return the found best play

    def run(self):
        '''
        Thread function to run Monte Carlo Tree Search (MCTS).

        Copies the specified state and randomly redistribute all unknown cards
        (except for the unknown cards in the current player's hand).
        Builds based on this new state a search tree to find the best play.
        '''

        # build the search tree with this state as root
        self.mcts.run_search(self.state, self.timeout)

        # check statistics
        self.mcts.check_stats(self.state)

        if self.verbose:
            # print statistics
            print('\n### MCTS Statistics:')
            print(f'Nodes: {len(self.mcts.nodes)}')
            self.mcts.print_stats(self.state)

        # select best play according to specified policy
        best_play = self.mcts.best_play(self.state, self.policy)

        # set selected play as found best plays
        self.selected_play = best_play


# -----------------------------------------------------------------------------
class DeeperShit(AiPlayer):
    '''
    Class representing an AI player which uses Monte Carlo Tree Search (MCTS).
    '''
    _count = 0   # counts number of DeeperShit instances.

    def __init__(self, name, fup_table=None, fdown_random=True, timeout=1.0,
                 policy='max', verbose=False):
        '''
        Initialize DeeperShit.

        Sets the player's name.
        Creates empty Deck objects for face down table cards, face up table
        cards, and hand cards.

        :param name:        player's name.
        :type name:         str
        :param fup_table:   face up table (None => don't swap).
        :type fup_table:    FupTable
        :param timeout:     timeout of tree search [s].
        :type timeout:      float
        :param policy:      MCTS best play policy ('robust', 'max')
        :type policy:       str
        :param verbose:     True => print MCTS statistics.
        :type verbose:      bool
        '''
        DeeperShit._count += 1
        super().__init__(name, fup_table, fdown_random)
        self.timeout = timeout
        self.policy = policy
        self.verbose = verbose
        self.thread = None          # thread for play selection by MCTS
        # flag indicating, that thread has already been started.
        self.thread_started = False

    def select_play(self, plays, state):
        '''
        Select one play from the list of legal plays.

        Uses the same initial strategy as TakeShit:
            - swaps cards if fup_table has been specified.
            - always shows the starting card, if it's on hand.
            - if possible, plays a card of same rank as the top discard pile
              card as 1st card, if there are 3 cards of same rank at the top
              of the discard pile.
            - voluntarily takes the discard pile:
                -- if he has more than 3 cards on hand and taking the discard
                   pile decrements the number of turns to get rid of these
                   cards.
                -- if the discard pile contains only ranks he already has on
                   hand plus good cards ('2', '3', 'Q', 'K', 'A') and if it
                   should be possible to get back to 3 hand cards before the
                   talon runs out.
            - only plays again if it's a low card (4, 5, 6, 7, 8, 9, J) or if
              the talon is empty.
            - when playing from hand:
                -- selects the cheapest playable card,
                   but '3' over '2' on '7', 'K', 'A' (Druck mache!)
            - when playing from face up table cards:
                -- selects the cheapest playable card.
                   but '3' over '2' on '7', 'K', 'A' (Druck mache!)
                -- after taking the discard pile,
                   get the cheapest face up table card.
            - when playing from face down table cards:
                -- selects any card at random.
            - doesn't play another '8' if only 2 players are left.
              => plays '8', ends turn, other player skipped, plays '8', ...
            - always refills on 'Q' or empty discard pile.
            - plays as many bad cards (4, 5, 6, 7) as possible before refill,
              but refills before playing another good (2, 3, 10, Q, K, A)
              or medium card (8, 9, J).

        But during the end game (i.e. talon is empty and  only 2 player's left)
        he uses MCTS to find the best play. A random distribution for unknown
        cards is assumed and a new search tree is started as soon as new
        information is available (i.e. another unknown card was disclosed).
        Since building the search tree takes some time, we do this in a
        seperate thread. We 1st check if a thread has already been started by
        checking the 'thread_started' flag:
            - yes => if thread is still running return None (thinking...)
                  => if thread has finished reset the 'thread_started' flag
                     and return the play selected by the thread.
            - no => 1st handle the simple cases (only one play in list, etc.)
                    2nd create a new thread, start it,
                    and set the 'thread_started' flag.
                    Then return None, so the caller can continue.

        :param plays:   plays legal for this player in this game state.
        :type plays:    list
        :param state:   shithead game state
        :type state:    State
        :return:        selected play.
        :rtype:         Play
        '''
        # check if the SelectMctsThread has been started before
        if self.thread and self.thread_started:
            # check if the SelectMctsThread has finished
            if self.thread.is_alive():
                # not finished yet
                return None  # => tell caller that AI player is still thinking
            else:
                # thread has finished => return selected play
                self.thread_started = False     # reset flag
                return self.thread.selected_play

        # no pending thread and we are not in the end game
        # i.e. the talon is not empty and there are more than 2 players
        # => we use the usual strategies
        if len(state.talon) > 0 or len(state.players) > 2:

            # handle all case where there is only one option:
            if len(plays) == 1:
                # only one option ('TAKE', 'REFILL', 'KILL', 'END', 'OUT')
                # => do it.
                return plays[0]

            # swap face up table cards with hand cards.
            if state.game_phase == SWAPPING_CARDS:
                if self.fup_table is None:
                    return Play('END')  # don't swap cards.
                return self.select_swap(plays)

            # handle starting player auction:
            if state.game_phase == FIND_STARTER:
                # we only get here, if there's a card to show .
                # otherwise 'END' would be the only possible play.
                return plays[0]

            # if we can play face down table cards always select one at random
            # (never take the discard pile).
            fdown_plays = [play for play in plays if play.action == 'FDOWN']
            if len(fdown_plays) > 0:
                if self.fdown_random:
                    return random.choice(fdown_plays)
                else:
                    # eliminate randomness by playing face down table cards
                    # from left to right for AI evaluation.
                    return fdown_plays[0]

            # shortcut to discard pile
            discard = state.discard

            # always try to kill the discard pile with the 1st play
            if state.n_played == 0 and state.discard.get_ntop() == 3:
                # find the 'HAND' or 'FUP' play with the same rank as the card
                # at the top of the discard pile
                play = self.rank_to_play(state.discard.get_top_rank(), plays)
                if play is not None:
                    return play

            _plays = [play for play in plays if play.action == 'TAKE']
            if len(_plays) > 0:
                # 'TAKE' is one of several legal plays
                # => check if we should do it
                if self.take_discard_or_not(state):
                    return Play('TAKE')

            # play another card of same rank or end turn?
            if self.play_again_or_end(plays):
                # play card if its value is < 7 ('Q')
                if RANK_TO_VALUE[state.discard.get_top_rank()] < 7:
                    # remove 'END' play => play card
                    plays = [play for play in plays if play.action != 'END']
                else:
                    return Play('END')  # => end turn

            # play another card of same rank or refill first
            if self.refill_or_play_again(plays):
                # alway refill 1st on 'Q' or empty discard pile.
                top_rank = discard.get_top_rank()   # None => empty
                if top_rank is None or top_rank == 'Q':
                    return Play('REFILL')
                if (top_rank == '4'
                        or top_rank == '5'
                        or top_rank == '6'
                        or top_rank == '7'):
                    # play bad cards before refilling => kill pile first
                    # remove 'REFILL' => play card
                    # if 'REFILL' was the only play it would have been returned
                    # above.
                    plays = [play for play in plays if play.action != 'REFILL']
                else:
                    # refill before playing another good or medium card.
                    return Play('REFILL')

            # play another card of same rank or kill the discard pile?
            if self.kill_or_play_again(plays):
                # prefere playing as many cards as possible before killing
                # the discard pile => remove 'KILL' from possible plays
                plays = [play for play in plays if play.action != 'KILL']

            # use 'index >= 0'
            # to make sure, that there are only card plays left.
            card_plays = [play for play in plays if play.index >= 0]
            if len(card_plays) == 0:
                raise ValueError("Left with empty list of plays!")

            # only 'HAND', 'FUP', or 'GET' plays left ('FDOWN' plays were
            # already handled).
            if card_plays[0] == 'GET':
                # take the cheapest face up table card on hand.
                return self.find_cheapest_play(card_plays, RANK_TO_VALUE)
            else:
                # when playing matching hand or face up table cards we use the
                # 'Druck mache!' strategie, i.e. if there's a '7', 'K', or 'A'
                # on the discard pile, we play a '3' before the '2' to turn on
                # the heat for the next player.
                top_non3 = discard.get_top_non3_rank()
                if top_non3 == '7' or top_non3 == 'K' or top_non3 == 'A':
                    # 7, K, or A => play 3 before 2
                    vmap = RANK_TO_VALUE_DRUCK   # '3' cheaper than '2'
                else:
                    vmap = RANK_TO_VALUE         # '2' cheaper than '3'
                # select the cheapest 'HAND' or 'FUP' play
                return self.find_cheapest_play(card_plays, vmap)
        else:
            # if the talon is empty and there are only 2 players left,
            # we use Monte Carlo Tree Search to find the best play
            self.thread = SelectMctsThread(state, self.timeout, self.policy,
                                           self.verbose)
            self.thread.start()
            self.thread_started = True
            return None     # tell caller that AI player is thinking

    def copy(self):
        '''
        Creates a copy of itself.

        :return:        copy of this player (not just reference).
        :rtype:         Player
        '''
        new_player = DeeperShit(self.name, self.fup_table, self.fdown_random,
                                self.timeout, self.policy, self.verbose)
        # swap phase state
        new_player.swap_count = self.swap_count
        # best face up table cards
        new_player.best_fup = self.best_fup[:]
        # number of turns played
        new_player.turn_count = self.turn_count
        # player's face down table cards
        new_player.face_down = self.face_down.copy()
        # player's face up table cards
        new_player.face_up = self.face_up.copy()
        # player's hand cards.
        new_player.hand = self.hand.copy()
        # True => must take face up table card as 2nd play
        new_player.get_fup = self.get_fup
        # rank of face up table card taken on 2nd play
        new_player.get_fup_rank = self.get_fup_rank

        return new_player


def main():
    """
    Player tests.
    """
    print('\nTest deal cards to player:')
    my_deck = Deck()
    my_deck.shuffle()
    my_deck.print()
    my_player = Player('Wolfi')
    for _ in range(9):
        my_player.deal(my_deck.pop_card())
    my_player.face_up.sort(False)
    my_player.hand.sort(False)
    my_deck.print()
    my_player.print()
    my_player.print(True)

    print('\nTest get_card_source:')
    source, cards = my_player.get_card_source()
    print(source)
    print(' '.join([str(card) for card in cards]))
    for _ in range(9):
        if source == 'HAND':
            my_player.hand.pop_card()
        elif source == 'FUP':
            my_player.face_up.pop_card()
        else:
            my_player.face_down.pop_card()
        source, cards = my_player.get_card_source()
        print(source)
        print(' '.join([str(card) for card in cards]))


if __name__ == '__main__':
    main()
