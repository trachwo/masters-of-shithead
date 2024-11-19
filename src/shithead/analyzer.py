"""
Functions for statistical hand analysis during a shithead game.

This was originally implemented to have a tool to decide whether to voluntarily
take the discard pile or not. The idea is to use the knowledge about the
unknown cards still in the game (burnt cards, talon, and player hand and face
down table cards) and the known cards still in the game (own hand cards,
opponent hand cards taken from discard, face up table cards) to calculate the
probability that a player is able to play a card. And from this we should be
able to calculate the probability to get rid of a specific hand of cards.
If we do this calculation for a hand after voluntarily taking the discard pile,
or after randomly refilling our hand from the talon, we should be able to
decide if taking the discard pile is a good play.
With the same method it should be possible to chose the best card to play in a
certain situation. The AI using this method is called 'BullShit' since it lost
most of the time against the other AIs.

06.05.2023 Wolfgang Trachsler
"""

from random import shuffle
from random import randrange
from itertools import permutations
from collections import Counter
import json

# local imports (modules in same package)
from .cards import Card, Deck, CARD_RANKS
from . import player as plr  # to avoid confusion with variable 'player'
from .game import Game
from .discard import Discard
from .state import State
from .fup_table import FupTable, FUP_TABLE_FILE

# list of cards we can play a specified card on
# NOTE: except for '2' and '3' we don't know if we can play a card on a '3'
#       because we don't know what's below it, i.e. we get slightly lesser
#       probabilities than expected (e.g. P('A') = 1 - P('7') - P('3') )
CAN_BE_PLAYED_ON = {
    '2': ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],
    '3': ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],
    '4': ['2', '4', '7'],
    '5': ['2', '4', '5', '7'],
    '6': ['2', '4', '5', '6', '7'],
    '7': ['2', '4', '5', '6', '7'],
    '8': ['2', '4', '5', '6', '8'],
    '9': ['2', '4', '5', '6', '8', '9'],
    '10': ['2', '3', '4', '5', '6', '8', '9', '10', 'J', 'Q', 'K', 'A'],
    'J': ['2', '4', '5', '6', '8', '9', 'J'],
    'Q': ['2', '4', '5', '6', '8', '9', 'J', 'Q'],
    'K': ['2', '4', '5', '6', '8', '9', 'J', 'Q', 'K'],
    'A': ['2', '4', '5', '6', '8', '9', 'J', 'Q', 'K', 'A'],
}

# to get a good average we take 'SAMPLE_RATE * len(unknown_cards)' samples
SAMPLE_RATE = 2

# number of samples when calculating average talon card playability
N_SAMPLES = 1


class Analyzer:
    """
    Class for player state analysis using card probabilities.
    """
    def __init__(self, state, name):
        """
        Constructor.

        :param state:       shithead game state.
        :type state:        State
        :param name:        name of analized player.
        :type name:         str
        """
        self.state = state
        self.name = name
        self.player = None
        # get specified player
        # None => specified player is already out
        for player in state.players:
            if player.name == name:
                self.player = player
                break

        self.unknown = []
        self.seen = []
        self.unknown_str = ''
        self.seen_str = ''
        self.playabs = {}       # playabilities per rank
        self.play_seq = []      # list of ranks in play order
        self.n_turns = 0        # number of turns 

        # only if specified player is still in the game
        if self.player is not None:
            # get cards from which this player doesn't know where they are
            self.unknown = [c.rank for c in state.get_unknown_cards(name)]
            # get cards from which this player knows the opponents have them
            self.seen = [c.rank for c in state.get_seen_cards(name)]


    def calc_rank_playabilities(self, verbose=False):
        """
        Calculate the probability that a card can be played as 1st play.

        We assume that from all the cards still in the game and not in this
        player's hand, one will randomly appear on the top of the discard pile.
        Now we can calculate for each card in this player's hand the
        probability that it can be played on a random top card.
        At the start of a players turn a card can only be played if its rank
        satisfies the rank of the top discard pile card (e.g. a '4' can only be
        played on '2', '4', or '7'). I.e. we can now calculate for each of the
        hand cards the probability, that a card will be at the top of the
        discard pile, which lets us play this hand card.

        :param verbose:     True => print results.
        :type verbose:      bool
        :return:            rank playabilities
        :rtype:             dict

        """
        ranks = self.unknown + self.seen
        n_cards = len(ranks)
        count_str = []
        probs = {}
        probs_str= []
        playabs_str = []

        # count cards per rank
        count = Counter(ranks) # count per rank
        if verbose:
            for rank in CARD_RANKS:
                if rank in count:
                    count_str.append(f"'{rank}': {count[rank]}")

        # calculate for each rank the probability to be on top of the discard
        # pile
        for rank in CARD_RANKS:
            if rank in count:
                # unknown or seen cards
                probs[rank] = count[rank] / n_cards
            else:
                # out of the game or only in this player's hand/fup cards
                probs[rank] = 0
            if verbose:
                probs_str.append(f"'{rank}': {probs[rank]:.2f}")

        # calculate the playability per rank
        # = probability a rank can be played on a random card
        for rank in CARD_RANKS:
            playab = 0
            for r in CAN_BE_PLAYED_ON[rank]:
                playab += probs[r]
            self.playabs[rank] = playab
            playabs_str.append(f"'{rank}': {playab:.2f}")

        if verbose:
            print(f"### rank count: {' '.join(count_str)}")
            print(f"### rank probabilities: {' '.join(probs_str)}")
            print(f"### rank playabilityes: {' '.join(playabs_str)}")

        # DRUCK MACHE !!!
        # if '7', 'K', or 'A' is on top of the discard pile make '2' slightly
        # more playable than '3' => '3' is played before '2'.
        top_non3 = self.state.discard.get_top_non3_rank()
        if top_non3 in ('7', 'K', 'A'):
            self.playabs['2'] += 0.1

    def calc_refill_playability(self, verbose=False):
        """
        Calculate the average refill playability.

        Before a card is drawn from the talon, it belongs to the unknown cards
        of this game state. To get a feeling for the quality of the remaining
        talon, we can calculate the average playability of all unknown cards.

        :param verbose:     True => print results.
        :type verbose:      bool
        """
        # make sure the rank playabilities have already been calculated
        if len(self.playabs) == 0:
            self.calc_rank_playabilities(verbose)

        # refilled card in player's hand are dummy cards with rank '0'
        self.playabs['0'] = 0
        if len(self.unknown) > 0:
            for rank in self.unknown:
                self.playabs['0'] += self.playabs[rank]
            self.playabs['0'] /= len(self.unknown)
        if verbose:
            print(f"### average refill card playability:"
                  f" {self.playabs['0']:.2f}")

    def calc_seq_playability(self, seq, verbose=False):
        """
        Calculate the average playability for a sequence of ranks.

        With the rank playabilities calculated from unknown cards and seen
        opponent cards we get the playability of each regular card in the
        specified sequence.
        Player's hand cards can also contain dummy cards which are placeholders
        for cards randomly drawn from the talon (= unknown cards). Dummy cards
        have rank '0' which references the average playability of unknown cards
        in the playabilities dictionary.

        :param seq:     sequence of ranks in hand or face up table cards.
        :type seq:      list
        :return:        average playability of this rank sequence.
        :rtype:         list
        """
        # make sure the rank playabilities have been calculated
        if len(self.playabs) == 0:
            self.calc_rank_playabilities(verbose)
        # make sure the average refill playability has been calculated
        if len(self.playabs) == len(CARD_RANKS):
            self.calc_refill_playability(verbose)

        playabs = []
        for rank in seq:
            playabs.append(self.playabs[rank])

        avg = 0
        if len(playabs) > 0:
            avg =  sum(playabs) / len(playabs)

        if verbose:
            playabs_str = [f"{playab:.2f}" for playab in playabs]
            print(f"### sequence playabilities: {' '.join(playabs_str)}")

        return avg

    def calc_avg_playability(self, verbose=False):
        """
        Find the best play sequence to play a large hand of cards.

        In order to decide whether we should take the discard pile or not, we
        have find out how many turns it will take to get rid of all hand cards.
        We sort a hand of cards in a way, that playing it in sequence from 1st
        to last card yields the best probability to get rid of all cards.
        We first sort all cards according to the playability of their rank,
        with the highest playability first and the rank with the worst
        playability last. Starting with the highest playability we play as many
        cards of the same rank as possible. If we can play 4 or more cards of
        the same rank, this will kill the discard pile, i.e. in this case we
        now play the cards with the worst playability. Otherwise we play the
        cards which now have the best playability, from the beginning of the
        list. The '10' is treated specially, since each played '10' kills the
        discard pile, we always play the rank with worst playability before
        playing another '10'. The 'Q' is also treated specially, since we can
        play immediately another card. Usually this will be the card with the
        worst playability, but with the possibility to play 4 'Q's in a row and
        only 1 other rank left, it is preferable to play the 'Q's first.

        :param verbose:     True => print play sequence
        :type verbose:      bool
        :return:            average playability
        :rtype:             float
        """
        play_seq = []       # found play sequence
        eff_seq = []        # effective play sequence (ignored cards removed)
        avg = 0             # average playability for hand/fup cards
        bonus = 0           # bonus for empty hand or empty face up table cards

        # player is already out
        if self.player is None:
            # best possible outcome => return playability 10
            return 10.0

        # make sure the rank playabilities have been calculated
        if len(self.playabs) == 0:
            self.calc_rank_playabilities(verbose)
        # make sure the average refill playability has been calculated
        if len(self.playabs) == len(CARD_RANKS):
            self.calc_refill_playability(verbose)

        if len(self.player.hand) > 0:
            # get a list of ranks in player's hand cards
            ranks = ([card.rank for card in self.player.hand])
        elif len(self.player.face_up) > 0:
            # get a list of ranks in player's face up table cards
            ranks = ([card.rank for card in self.player.face_up])
            bonus = 1   # playability bonus for empty hand
        else:
            # only face down table cards left => nothing to do
            ranks = []
            bonus = 5   # playability bonus for empty hand/fup cards

        # 3 or less cards => calculate average + bonus
        if len(ranks) <= 3:
            avg = self.calc_seq_playability(ranks, verbose) + bonus
            self.n_turns = len(ranks)
            if verbose:
                print(f"### average playability: {avg:.2f}"
                      f" turns: {self.n_turns}")
            return avg

        # >3 cards on hand => find best play sequence
        # default rank order
        rank_order = ['3', '2', '10', 'A', 'K', 'Q', 'J', '9', '8', '7',
                           '6', '5', '4', '0']

        # cards with high playability
        # => never ignore when calculating the average playability
        # all other ranks ignore when played after 'Q', killed discard pile
        # or previously played card of same rank.
        good_ranks = ['3', '2', '10', 'A', 'K', 'Q']

        # sorting key function => gets playability per rank
        def get_rank_playability(rank):
            return self.playabs[rank]

        # get a rank order sorted by playability
        rank_order.sort(key=get_rank_playability, reverse=True)
        if verbose:
            print(f"### rank order: {' '.join(rank_order)}")

        # sorting key function => gets index of rank in rank order
        def get_rank_order(rank):
            return rank_order.index(rank)

        # sort the hand according to the rank_order
        ranks.sort(key=get_rank_order)
        if verbose:
            print(f"### sorted hand: {' '.join(ranks)}")

        # play rank with highest playability first
        play_seq.append(ranks.pop(0))
        eff_seq.append(play_seq[-1])
        self.n_turns = 1        # 1st turn
        same_rank_count = 1     # played 1 card of this rank
        play_best = True        # => play best ranks first

        # loop through remaining cards in the original sequence
        while len(ranks) > 0:
            if play_seq[-1] == '10':
                # we played a '10' and killed the discard pile
                # => we can play any card,
                # i.e. play the one with the worst playability next
                play_seq.append(ranks.pop(-1))
                if play_seq[-1] in good_ranks:
                    eff_seq.append(play_seq[-1])
                play_best = False       # => play from end of list
                same_rank_count = 1     # reset same rank counter

            elif play_seq[-1] == 'Q':
                if play_best:
                    # played 'Q' from start of list, i.e. we could now play any
                    # card with worse playability on the 'Q' or maybe play 4
                    # 'Q's to kill the discard pile.
                    # =>  count number of 'Q's still in cards
                    count = Counter(ranks)
                    if count['Q'] > 0 and count['Q'] + same_rank_count >= 4:
                        # we could play all 'Q's to kill the discard pile
                        # => do it if there's only one other (worse) rank left
                        if len(count) <= 2:
                            # play another 'Q'
                            play_seq.append(ranks.pop(0))
                            if play_seq[-1] in good_ranks:
                                eff_seq.append(play_seq[-1])
                            same_rank_count += 1
                        else:
                            # better play cards with worse playability first
                            play_seq.append(ranks.pop(-1))
                            if play_seq[-1] in good_ranks:
                                eff_seq.append(play_seq[-1])
                            play_best = False       # => play from end of list
                            same_rank_count = 1     # reset same rank counter
                    else:
                        # no more 'Q's or less than 4 'Q's in total
                        # => play card with worser playability first
                        play_seq.append(ranks.pop(-1))
                        if play_seq[-1] in good_ranks:
                            eff_seq.append(play_seq[-1])
                        play_best = False       # => play from end of list
                        same_rank_count = 1     # reset same rank counter
                else:
                    # 'Q' has been played from end of list
                    # => keep playing from end of list 'Q' or next worse rank
                    play_seq.append(ranks.pop(-1))
                    if play_seq[-1] in good_ranks:
                        eff_seq.append(play_seq[-1])
                    if play_seq[-1] == 'Q':
                        same_rank_count += 1    # 1 more 'Q' played
                    else:
                        same_rank_count = 1     # 1st card of next rank played

            elif play_seq[-1] in ranks:
                # more cards with same rank as previous card in hand
                same_rank_count += 1
                if play_best:
                    # play from begin of list
                    play_seq.append(ranks.pop(0))
                else:
                    # play from end of list
                    play_seq.append(ranks.pop(-1))
                if play_seq[-1] in good_ranks:
                    eff_seq.append(play_seq[-1])
            else:
                # no more cards with same rank
                # => check if we have played 4 or more cards of same rank
                if same_rank_count >= 4:
                    # we killed the discard pile and can play any card
                    play_best = False
                    # play card with bad playability from the end of the list
                    play_seq.append(ranks.pop(-1))
                    if play_seq[-1] in good_ranks:
                        eff_seq.append(play_seq[-1])
                else:
                    # play the next rank with best playability
                    play_seq.append(ranks.pop(0))
                    eff_seq.append(play_seq[-1])
                    play_best = True    # play from begin of list
                    self.n_turns += 1
                # next rank => reset same rank count
                same_rank_count = 1

        # calculate average playability for effective play sequence 
        avg = self.calc_seq_playability(eff_seq, verbose)

        if verbose:
            print(f"### play sequence: {' '.join(play_seq)}")
            print(f"### effective play sequence: {' '.join(eff_seq)}")

        # calculate average playability for effective play sequence 
        avg = self.calc_seq_playability(eff_seq, verbose)

        if verbose:
            print(f"### average playability: {avg:.2f} turns: {self.n_turns}")

        return avg

    def get_number_of_turns(self, verbose=False):
        """
        Get the number of turns to play hand/fup cards.

        Returns the minimum number of turns to play the hand or face up table
        cards as determined when calculating the average playability of these
        cards.

        :param verbose:     True => print play sequence
        :type verbose:      bool
        :return:            number of turns.
        :rtype:             int
        """
        # make sure that average playability has been calculated.
        if self.n_turns == 0:
            self.calc_avg_playability(verbose)

        return self.n_turns

    def get_playability_seq(self):
        """
        Get the playability for each turn of the play sequence.

        Calculates for each rank the probability to randomly appear at the top
        of the discard pile.
        Calculates for each rank the probability that it can be played on a
        random card on top of the discard pile.
        Finds an optimum play sequence for hand or face up table cards.
        Generates a list with the playabilities for each turn of the found play
        sequence.

        :return:    playability for each turn in the play sequence
        :rtype:     list
        """


        # with 3 cards in hand and the talon not gone, just return the
        # playability of each rank.
        # I.e. don't play cards for free after '10' or 'Q'.
#        if len(self.play_seq) == 3 and len(self.state.talon) > 0:
        if len(self.play_seq) <= 3:
            playability_seq = [self.playabs[rank] for rank in self.play_seq]
            return playability_seq
        
        # with more than 3 cards on hand or the talon gone, the playability of
        # the hand improves if bad cards can be played after '10' or 'Q'.
        playability_seq = []
        for i, rank in enumerate(self.play_seq):
            if i == 0:
                # add playability of very 1st rank in play sequence
                playability_seq.append(self.playabs[rank])
                same_rank_count = 1
                turn_count = 1
            elif rank == self.play_seq[i-1]:
                # same rank as previous
                if self.playabs[rank] > 0.6:
                    # add playability of good cards ('3', '2', 'A', 'K', 'Q')
                    # without incrementing the number of turns.
                    # NOTE: '10' is always played single.
                    playability_seq[-1] += self.playabs[rank]
                # but play bad cards ('4', '5', ... 'J') for free
                #  => same turn without incrementing playability
                same_rank_count += 1        # one more of same rank
            elif same_rank_count >= 4:
                # different rank than previous card
                # >4 cards of same rank kill the discard pile
                # => play this card for free (same turn)
                same_rank_count = 1         # start new count
            elif self.play_seq[i-1] == '10':
                # different rank than previous card
                # previous card was '10' which kills the discard pile
                # => play this card for free (same turn)
                same_rank_count = 1         # start new count
            elif self.play_seq[i-1] == 'Q':
                # different rank than previous card
                # previous card was 'Q' which must be covered
                # => play this card for free (same turn)
                same_rank_count = 1         # start new count
            else:
                # different rank than previous card
                # => played at beginning of another turn
                playability_seq.append(self.playabs[rank])
                same_rank_count = 1     # start new count
                turn_count += 1         # one more turn

        if len(playability_seq) == 0:
            # => neither hand nor face up table cards left,
            #    i.e. the 2nd best possible outcome after being OUT
            playability_seq.append(4.0) # make sure this play is selected 

        # return the playability sequence
        return playability_seq


def evaluate_player_cards(state, name):
    """
    Qualify hand and face up table cards of specified player.

    We calculate a value for the cards in the specified player's hand (and if
    the talon is empty also for his face up table cards) in order to decide,
    which of multiple legal plays has the best outcome. We try to find a value
    for the hand/fup cards resulting from a certain play, by calculating the
    probability to play these cards in the following turns (e.g a hand of '2',
    '3', and '10' should usually result in a higher value than '4', '5', and
    '6').
    To find this value we first make a list of all cards still in the game but
    not in this player's hand or face up table cards, an use it to determine
    the probaility that a certain rank ('7', 'A', etc.) randomly appears at top
    of the discard pile in the next turns (independently of the cards already
    in the discard pile).
    From this we can calculate for each rank the probability that it can be
    played (e.g. '2' can always be played => 1.0, while '4' can only be played
    on '2', '4', or '7').
    Because some cards can be played 'for free' after 'Q' or on an empty
    discard pile (after '10' or after 4 or more cards of same rank) we first
    arrange the cards in the best possible sequence and then calculate the
    average probability for this sequence (we call this the playability).

    :param state:       current state of play.
    :type state:        State
    :param name:        name of player for which we evaluate cards.
    :type name:         str
    :return:            playability of found play sequence.
    :rtype:             float
    """
    # get specified player
    for player in state.players:
        if player.name == name:
            break
    else:
        raise ValueError(f"{name} is not in the list of players!")

    # get cards from which the specified player doesn't know where they are
    unknown = [card.rank for card in state.get_unknown_cards(name)]
    # get cards from which the specified player knows the opponents have them
    seen = [card.rank for card in state.get_seen_cards(name)]
    print(Counter(unknown + seen))
    # get probability per rank to appear on top of the discard pile
    rank_probs = calc_rank_probabilities(unknown + seen)
    print(rank_probs)
    # calculate for each rank the probability, that it can be played on a
    # random card on top of the discard pile.
    rank_playabs = calc_rank_playabilities(rank_probs)
    print(rank_playabs)
    # get a list of ranks sorted by their playablility
    rank_order = sort_ranks_by_playability(rank_playabs)
    print(rank_order)
    # get a list of ranks in player's hand cards
    cards = ([card.rank for card in player.hand])
    # find play sequence for hand cards
    play_seq = find_play_sequence(rank_order, cards)
    print(play_seq)
    # if talon is empty add play sequence for face up table cards at the end.
    if len(state.talon) == 0:
        cards = ([card.rank for card in player.face_up])
        play_seq += find_play_sequence(rank_order, cards)

    # Finally calculate the playability for this play sequence and return it.
    playability =  calc_playability(rank_playabs, play_seq)
    print(f"### playability: {playability}")
    return playability


def check_permutations(rank_playabilities, hand):
    """
    Find best play sequence by checking all permutations of hand.

    Calculate the playability for all permutations of the specified hand in
    order to find the best play sequence.
    DON'T USE this for hands > 10 cards, it takes forever.

    :param playable_probs:    playability per rank
    :type playable_probs:    dict
    :param hand:            list of ranks in hand
    :type hand:                list
    """
    playability_max = 0
    turns_max = len(hand) + 1
    seq_max = tuple()
    for play_seq in permutations(hand):
        playability, turns = calc_playability(rank_playabilities, play_seq)
        if (playability > playability_max or playability == playability_max and
                turns < turns_max):
            playability_max = playability
            turns_max = turns
            seq_max = play_seq
    print(f"### check_permutations: {seq_max} playability: {playability_max}"
          f" turns: {turns_max}")


class Combi():
    """
    Class for finding all possible play combinations.

    A Combi instance starts out as a possible play depending on the current
    hand of the player and the discard pile and contains all information
    necessary to decide whether further cards can be played from the remaining
    hand cards (i.e. the number of cards with same rank on top of the discard
    pile and the rank of the card on top of the discard pile).
    If this is the current player's 1st play this turn we can create one combi
    with empty sequence and a hand containing all hand cards after taking the
    discard pile, or 1 combi per unique rank which can be played on the discard
    pile (i.e. the unique rank goes into the sequence and the hand contains the
    ranks of the remaining hand cards).
    If this is not the current player's 1st play, we can create one combi with
    empty sequence to represent ending the turn after the 1st played card, or
    one combi with the same rank as the top discard pile card (which this
    player has previously played) in its sequence.
    For each of the initial combinations we can determine if the player can
    (or must) stop after playing all cards in its sequence and if it is
    expandable, i.e. if it is possible to create new combinations to add a card
    from the hand to the sequence. In this way we can go recoursively through
    a list of combinations and for each combination add its expansions to the
    end of the list before either removing it from the list (not endable) or
    move it to the list of completed combinations (endable) before either
    removing it from the list (not endable) or move it to the list of completed
    combinations (endable).
    The value of a combination (play sequence) is the playability of its
    remaining hand, i.e. the probability to get rid of its cards considered the
    unknown and known cards still in play. If a hand has to (and can be)
    refilled after this play sequence, we randomly create multiple refilled
    hands to calculate an average playability.
    For each (refilled) hand we can also find the possibly best sequence of
    play to get rid of its cards in as few turns as possible.
    """
    def __init__(self, unknown, seen, seq, hand, n_top, top_rank=None):
        """
        Initializer.

        :param unknown:     list with ranks of unknown cards.
        :type unknown:      List
        :param seen:        list with ranks of known cards in the hands of
                            opponents.
        :type seen:         List
        :param seq:         list of ranks in play order.
        :type seq:          list
        :param hand:        list of ranks still in player hand
        :type hand:         list
        :param n_top:       number of cards with same rank at top of discard
                            pile after this sequence of play.
        :type n_top:        int
        :param top_rank:    rank of card on top of discard pile
        :type top_rank:     str
        """
        self.unknown = unknown
        self.seen = seen
        self.seq = seq      # list of ranks representing play order
        # list of remaining ranks still in hand after base rank has been played
        self.hand = hand
        # number of consecutive cards with same rank at the top of the discard
        # pile after this sequence of play.
        self.n_top = n_top
        # the rank of the card at the top of the discard pile is needed, if
        # we already have played the 1st card, in order to decide if we can end
        # the turn without playing another card.
        self.top_rank = top_rank
        self.playability = 0    # (average) playability after refill
        self.turns = 0          # (average) number of turns after refill

    def is_endable(self):
        """
        Check if a turn may be ended after this combination.

        A turn can be ended with a combination, if the discard pile has not
        been killed, and the last rank of the combination is not a 'Q'.
        Since we don't refill the hand for this evaluation, it's also possible
        to end with a killed discard pile or a 'Q', if no more cards are
        available to expand the combination.

        :return:    True => is endable.
        :rtype:     bool
        """
        if self.seq:
            # sequence is not empty => last played card
            rank = self.seq[-1]
        else:
            # rank of card on top of discard pile (empty => None)
            rank = self.top_rank

        if len(self.hand) == 0:
            return True     # max length of combination reached
        elif self.n_top >= 4:
            # >=4 cards with same rank on top => killed the discard pile
            return False
        elif rank is None:
            if len(self.seq) == 0:
                # we have taken the discard pile => end turn
                return True
            else:
                # previous play has killed the discard pile => continue
                return False
        elif rank == '10':
            # last card was '10' => killed the discard pile
            return False
        elif rank == 'Q':
            # last card was 'Q' => has to be covered
            return False
        else:
            # in all other cases we can end our turn
            return True

    def expand(self):
        """
        Create a list of expanded combinations.

        A combination can be expanded if we have a card with same rank as the
        last card of the combination on hand, or after the discard pile has
        been killed ('10' or >= 4 of same rank), or if the last card of the
        combination is a 'Q'. A combination cannot be expanded if we don't have
        any cards left in our hand.

        :return:    list of expansions (Combi)
        :rtype:     list
        """
        expansions = []  # list of expanded combinations based on this combi

        if len(self.hand) == 0:
            # combination has reached its maximum length
            return expansions   # return empty list

        if self.seq:
            # sequence is not empty => last played card
            rank = self.seq[-1]
        else:
            # rank of card on top of discard pile
            # discard pile taken => None
            # end after 1st play => not None (otherwise no ending on 2nd play)
            rank = self.top_rank

        if len(self.seq) == 0 and rank is None:
            # cannot expand after taking the discard pile
            return expansions   # return empty list

        if rank in self.hand:
            # we have more cards with same rank as the last card on hand
            # => create exactly 1 expansion
            seq = self.seq[:]
            hand = self.hand[:]
            seq.append(rank)
            hand.remove(rank)
            expansions.append(Combi(self.unknown, self.seen, seq, hand,
                                    self.n_top + 1))

        if self.n_top >= 4 or rank == '10' or rank == 'Q':
            # killed the discard pile or last card is 'Q'
            ranks = set(self.hand)
            for rk in ranks:
                if rk == rank:
                    continue    # already handled above
                seq = self.seq[:]
                hand = self.hand[:]
                seq.append(rk)
                hand.remove(rk)
                expansions.append(Combi(self.unknown, self.seen, seq, hand, 1))

        return expansions

    def evaluate(self, size, max_draws):
        """
        Calculate the average playability of this combi after refill.

        To get a value for a play combination, we refill the remaining hand
        cards up to the specified size (3 after normal play or 3 + turns
        after taking the discard pile) with cards selected randomly from
        the set of unknown cards, and then calculate the playability of this
        new hand. We repeat this several times (SAMPLE_RATE * 'number of
        unknown cards) to get a representative average value.
        We then assume, that the play which leaves us with the most valuable
        next hand, will be the best play.
        Note: if the talon is empty, max_draws will be 0 and there will be no
              more adding of unknown cards for playability evaluation.

        :param size:        size to which we refill our hand after play.
        :type size:         int
        :param max_draws:   nbr of cards we could draw before talon is empty.
        :type max_draws:    int
        """
        total_playability = 0
        total_turns = 0
        n_samples = 1   # no refill => just calculate playability of hand
        if len(self.hand) < size and max_draws > 0:
            # randomly refill hand n_samples time and calculate average
            # playability over all samples
            n_samples = len(self.unknown) * SAMPLE_RATE

        for _ in range(n_samples):
            # make a copy of the unknown cards and shuffle it
            _unknown = self.unknown[:]
            shuffle(_unknown)
            # make a copy of this combi's remaining hand
            hand = self.hand[:]
            # and refill it to the requested size
            n_draws = 0
            while (len(hand) < size and n_draws < max_draws):
                hand.append(_unknown.pop())
                n_draws += 1
            # calculate the playability per rank
            probs = calc_rank_probabilities(_unknown + self.seen)
            rank_playabilities = calc_rank_playabilities(probs)
            rank_order = sort_ranks_by_playability(rank_playabilities)
            play_seq = find_play_sequence(rank_order, hand)
            playability, turn_count = calc_playability(
                rank_playabilities, play_seq)
            total_playability += playability
            total_turns += turn_count
        self.playability = total_playability / n_samples
        self.turns = total_turns / n_samples


def find_all_play_combis(state):
    """
    Get all combinations of possible plays.

    For each of the ranks in the hand start a new combination with this rank.
    Check if we could end the turn after playing the last card added to this
    combination, if yes add a copy of this combination to the list.
    Next check if more cards can be added to this combination, i.e. if we have
    more cards of the same rank as the last card, or if we have killed the
    discard pile with 4 or more cards of same rank or with a '10', or if the
    last card was a 'Q' we have to cover.
    After killing the discard pile or playing a 'Q' we can expand a combination
    with any of the remaining cards, creating new possible combinations from
    the same base combination.

    :param state:   game state
    :type hand:     State
    :return:        list of possible play combinations
    :rtype:         list
    """
    completed = []          # list of completed play combinations
    in_progress = []        # list of started play combinations
    start_ranks = []        # list of ranks used as start of a play sequence

    # shortcuts
    discard = state.discard                     # discard pile
    if len(state.players[state.player].hand) > 0:
        # playing from hand cards of current player
        hand = state.players[state.player].hand
    elif len(state.players[state.player].face_up) > 0:
        # playing from face up table cards
        hand = state.players[state.player].face_up
    else:
        # playing randomly from face down table cards
        # => no need for anlysis, return empty list
        return []

    first = state.n_played == 0                 # 1st card played this turn
    top_rank = discard.get_top_rank()           # rank at top of discard pile

    # get ranks of cards from which we don't known where they are
    unknown = [card.rank for card in state.get_unknown_cards()]
    # get ranks of cards which are in the hands of opponents
    seen = [card.rank for card in state.get_seen_cards()]

    if len(discard) > 0:
        # there's a discard pile
        if first:
            # at the begin of a turn we can always decide to take the discard
            # pile.
            # => add combi with empty sequence and discard pile added to hand.
            in_progress.append(Combi(unknown, seen, [],
                                     [c.rank for c in hand] +
                                     [c.rank for c in discard], 0, None))
        else:
            # if this is not the 1st card played this turn, it is possible that
            # we can end the turn without playing a further card.
            # => add combi with empty sequence to list
            n_top = discard.get_ntop()  # number of cards with same rank at top
            in_progress.append(Combi(unknown, seen, [],
                                     [c.rank for c in hand], n_top, top_rank))

    for card in hand:
        # loop through all cards in this hand
        if card.rank not in start_ranks and discard.check(first, card):
            # we haven't started a combi with this rank yet
            # and this card can be played
            start_ranks.append(card.rank)    # add it to used start ranks
            if card.rank == top_rank:
                # increment number of cards with same rank at top
                n_top = discard.get_ntop() + 1
            else:
                # 1st card with this rank at top
                n_top = 1
            # create a new combi with this start rank
            # Note: we don't need top_rank because from now on we look at the
            #       last rank in the play sequence
            combi = Combi(unknown, seen, [card.rank],
                          [c.rank for c in hand if c != card], n_top)
            # add it to the list of combinations in progress
            in_progress.append(combi)

    while len(in_progress) > 0:
        # there are still unfinished combinations to be handled
        combi = in_progress[0]  # get 1st combination in list
        if combi.is_endable():
            # valid sequence of play => add it to the completed combis list
            completed.append(combi)
        # create expansions of current combi if possible and add it to the list
        in_progress += combi.expand()
        # remove the handled combi from the list
        in_progress.remove(combi)

    return completed


def evaluate_plays(state):
    """
    Evaluate all possible plays.

    Find all play combis for the current player.
    For each of these combis refill the hand after the corresponding play
    sequence with the specified number of ranks from the list of unknown ranks
    (or less depending on remaining draws). Repeat this multiple times and
    calculate the playability of the resulating hand each time to calculate
    its average playability.

    :param state:   game state.
    :type state:    State
    :return:        list of evaluated play combinations.
    :rtype:         List
    """
    # get size of current player's hand
    n_hand = len(state.players[state.player].hand)
    # estimate the remaining draws for the current player
    # note that we don't need  n_turns and hands returned by function.
    _, n_draws, _ = state.estimate_remaining_draws(n_hand)

    # find all possible play combinations for the current player
    combis = find_all_play_combis(state)

    # evaluate each of these combis
    for combi in combis:
        combi.evaluate(3, n_draws)

    return combis


def find_best_play(state):
    """
    Find the best play for the current player.

    Find all play combis for the current player.
    For each of these combis refill the hand after the corresponding play
    sequence with the specified number of ranks from the list of unknown ranks
    (or less depending on remaining draws). Repeat this multiple times and
    calculate the playability of the resulating hand each time. The best play
    is the one which leaves us with the best average playability after
    refilling.
    In order to decide if we should take the discard pile, we could refill
    according to the number of turns it will take to get rid of the cards in
    the combination of hand and discard pile and compare the playabilities of
    the hand+discard against the best hand playability.

    :param state:   game state.
    :type state:    State
    :return:        play sequence, remaining hand,
                    and maximum average playability of refilled hand.
    :rtype:         Tuple
    """
    best = None
    # create a list of possible play sequences and for each calculate its
    # playability when refilling to 3
    combis = evaluate_plays(state)
    if not combis:
        # list of possible combinations is empty (TODO should not happen)
        return None

    # find the combi with the highest playability
    playabilities = [combi.playability for combi in combis]
    best = combis[playabilities.index(max(playabilities))]
    n_hand = len(state.players[state.player].hand)
    if n_hand == 0:
        # never voluntarily take the discard pile then playing face up table
        # cards, but it may be the only play in the list
        return best

    if state.n_played == 0 and len(combis[0].seq) == 0:
        # 1st play this turn => consider taking the discard pile
        if len(best.seq) > 0:
            # the best play is not taking the discard pile
            # => calculate its playability after refilling to 3 and drawing a
            #    card for each turn we need to get rid of the cards after
            #    taking the discard pile.
            _, n_draws, _ = state.estimate_remaining_draws(n_hand)
            bup = best.playability  # backup the playability value
            best.evaluate(3 + int(combis[0].turns), n_draws)
            if best.playability + 0.2 < combis[0].playability:
                best = combis[0]
            else:
                # restore the original playablility
                best.playability = bup

    # check if the best combination has a play sequence containing
    # a single '2', and  a '3' on hand. Depending on the top card of the
    # discard pile swap the '2' with the '3' (Druck mache!)
    if len(best.seq) == 1 and best.seq[0] == '2' and '3' in best.hand:
        if state.discard.get_top_rank() in ['7', 'K', 'A']:
            best.seq[0] = '3'
            idx = best.hand.index('3')
            best.hand[idx] = '2'

    return best


def find_best_fup_pick(state, get_fup_rank):
    """
    Find best face up table card to pick up after taking the discard pile.

    When taking the discard pile while playing from the face up table cards,
    the player may also take one card or several cards of same rank from his
    face up table cards on hand. I.e. each rank in the face up table cards
    results at least in a play sequence, where we pick up 1 card of this rank.
    If there are multiple cards with the same rank, it's also possible to pick
    up 2 or even 3 cards.

    :param state:           game state.
    :type state:            State
    :param get_fup_rank:    rank of previously picked card,
                            NONE if this is the 1st pick.
    :type get_fup_rank:     str
    :return:                play sequence, remaining hand,
                            and maximum average playability of refilled hand.
    :rtype:                 Tuple
    """
    # get ranks of cards from which we don't known where they are
    unknown = [card.rank for card in state.get_unknown_cards()]
    # get ranks of cards which are in the hands of opponents
    seen = [card.rank for card in state.get_seen_cards()]
    combis = []  # list of possible picks
    # get face up table cards of current player
    fup = [card.rank for card in state.players[state.player].face_up]
    count = Counter(fup)    # count ranks in face up table cards
    seq = []            # play sequence
    hand = fup[:]       # remaining face up cards
    if get_fup_rank is None:    # 1st pick
        # create all possible pick up combinations
        for rank, cnt in count.items():
            for _ in range(cnt):
                seq.append(rank)
                hand.remove(rank)
                # create combination
                combi = Combi(unknown, seen, seq, hand, 0, None)
                # calculate playability of remaining cards (no refill)
                combi.evaluate(0, 0)
                combis.append(combi)
    else:   # 2nd or 3rd pick
        # we can always stop after the 1st pick
        # => empty play sequence
        combi = Combi(unknown, seen, seq, hand, 0, None)
        # calculate playability of remaining cards (no refill)
        combi.evaluate(0, 0)
        combis.append(combi)
        if get_fup_rank in count.keys():
            # more cards with same rank as 1st pick
            for _ in range(count[get_fup_rank]):
                seq.append(get_fup_rank)
                hand.remove(get_fup_rank)
                # create combination
                combi = Combi(unknown, seen, seq, hand, 0, None)
                # calculate playability of remaining cards (no refill)
                combi.evaluate(0, 0)
                combis.append(combi)

    # find the combi with the highest playability
    playabilities = [combi.playability for combi in combis]
    best = combis[playabilities.index(max(playabilities))]
    return best

def restore_game_state(filename, verbose=False):
    """
    Restores a game state from json-file.

    Loads state info from the provided json-file.
    Creates a list of players (all of type 'CheapShit') and uses it to create
    the initial game state.
    Uses the loaded game state info to transform this state into the loaded
    game state.
    NOTE: in the json-file change the log-level in "log_info" to "No Secrets",
          "One Line" will crash!!!

    :param filename:    name of json-file containing end game state.
    :type filename:     str
    :param verbose:     True => print loaded json-string
    :type verbose:      bool
    :return:            game state.
    :rtype:             State
    """
    state_file = filename

    try:
        # load game state from json-file
        with open(state_file, 'r', encoding='utf-8') as json_file:
            state_info = json.load(json_file)
    except OSError as err:
        print(err)
        print(f"### Error: couldn't load file {state_file}")
        return

    # print the loaded game state
    if verbose:
        print(f'\n### Game state info loaded from {filename}')
        state_info_str = json.dumps(state_info, indent=4)
        print(state_info_str)

    # create face up table (needed in player createion)
    fup_table = FupTable()

    # load face up table from file (in package)
    fup_table.load(FUP_TABLE_FILE, True)

    # create list of remaining player
    # Note, that the AI type is not in the status (but in the config).
    # We use 'CheapShit' because we just need a game state to count cards.
    players = []
    players.append(plr.HumanPlayer('', False, False))
    players.append(plr.CheapShit('', fup_table, True))
    players.append(plr.CheapShit('', fup_table, True))

    # get the number of necessary card decks from state info
    n_decks = state_info['n_decks']

    # create the logging info from the state info
    # => we can change it by editing the JSON string
    log_info = state_info['log_info']

    # Now we have everything to create an initial state.
    # Note, that this is not the original initial state (for 3 players), but it
    # doesn't matter, since we will overwrite it with the loaded state info
    # anyhow (we don't specify the dealer, since he may be already out).
    state = State(players, -1, n_decks, log_info)

    # load the burnt cards pile with burnt cards in state_info
    state.burnt.load_from_state(state_info['burnt'])
    state.n_burnt = state_info['n_burnt']

    # load the removed cards pile with killed cards in state_info
    state.killed.load_from_state(state_info['killed'])

    # load the talon with talon cards in state_info
    state.talon.load_from_state(state_info['talon'])

    # load the discard pile with cards specified in state_info
    state.discard.load_from_state(state_info['discard'])

    # load player states
    for j, player in enumerate(state.players):
        player.load_from_state(state_info['players'][j])

    # load remaining game state attributes
    state.turn_count = state_info['turn_count']
    state.player = state_info['player']
    state.direction = state_info['direction']
    state.next_direction = state_info['next_direction']
    state.next_player = state_info['next_player']
    state.n_played = state_info['n_played']
    state.eights = state_info['eights']
    state.kings = state_info['kings']
    state.game_phase = state_info['game_phase']
    state.starting_card = state_info['starting_card']
    state.auction_members = state_info['auction_members']
    state.shown_starting_card = state_info['shown_starting_card']
    state.result = state_info['result']
    state.dealing = False

    return state


def main_old():
    """
    Test for functions in this module.
    """

    # testing find_all_play_combis
    print('\n### Test: find_all_play_combis() ###')

    # create 3 players with generic names
    _players = []
    _players.append(plr.CheapShit('Player1', None, False))
    _players.append(plr.CheapShit('Player2', None, False))
    _players.append(plr.CheapShit('Player3', None, False))

    # create a game state  (players, dealer=-1, n_decks=1, log_info)
    state = State(_players, -1, 1, ('Debugging', False, ''))

    # make Player1 the current player
    state.player = 0

    # create empty hand and reference it from state
    hand = Deck(empty=True)
    state.players[0].hand = hand

    # create an empty discard pile and reference it from state
    discard = Discard()
    state.discard = discard

    hand.add_card(Card(0, 'Clubs', '5'))
    hand.add_card(Card(0, 'Spades', '4'))
    hand.add_card(Card(0, 'Diamonds', '4'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")

    discard.add_card(Card(0, 'Clubs', '4'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")

    hand.add_card(Card(0, 'Hearts', '4'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")

    discard.add_card(hand.pop_card(1))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")

    hand.add_card(Card(1, 'Clubs', '4'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")

    hand.add_card(Card(0, 'Clubs', 'Q'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")

    hand.add_card(Card(0, 'Hearts', 'Q'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print(f"hands: {[c.hand for c in combis]}")

    discard.add_card(hand.pop_card(5))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")

    discard.add_card(hand.pop_card(4))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")

    discard.pop_card(2)
    hand.add_card(Card(0, 'Clubs', '10'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")

    hand.add_card(Card(0, 'Diamonds', '10'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")

    discard.add_card(Card(0, 'Clubs', '7'))
    print("\n--- First play ---")
    state.n_played = 0
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")
    print("\n--- Second play ---")
    state.n_played = 1
    print(f"discard: {discard}   hand: {hand}")
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")

    # testing card statistics
    print('\n### Test: card statistics ###')

    # create 3 players with generic names
    _players = []
    _players.append(plr.CheapShit('Player1', None, False))
    _players.append(plr.CheapShit('Player2', None, False))
    _players.append(plr.CheapShit('Player3', None, False))

    # create a game state  (players, dealer=-1, n_decks=1, log_info)
    state = State(_players, -1, 1, ('Debugging', False, ''))

    # shortcuts
    talon = state.talon
    players = state.players
    discard = state.discard

    # shuffle the talon
    talon.shuffle()

    # deal cards to players
    Game.deal(players, 0, talon)

    # add some random cards to the discard pile and mark them as seen
    for i in range(10):
        card = talon.pop_card()
        card.seen = True
        discard.add_card(card)

    # player1 and player2 pick up some discard pile cards
    # => marked as seen
    for i in range(2):
        players[1].hand.add_card(discard.pop_card())
    for i in range(3):
        players[2].hand.add_card(discard.pop_card())

    # make Player1 the current player
    state.player = 0

    print(f"talon: {talon}")
    print(f"discard: {discard}")
    players[0].print(visibility=3)
    players[1].print(visibility=3)
    players[2].print(visibility=3)

    unknown = [card.rank for card in state.get_unknown_cards()]
    print(f"unknown: {unknown}   nof: {len(unknown)}")
    seen = [card.rank for card in state.get_seen_cards()]
    print(f"seen: {seen}   nof: {len(seen)}")
    print(f"total number of cards: {len(unknown) + len(seen)}")
    count = Counter(unknown + seen)
    print(f"rank counter: {count}")
    probs = calc_rank_probabilities(unknown + seen)
    print(f"rank probabilities: {probs}")
    rank_playabilities = calc_rank_playabilities(probs)
    print(f"rank playabilities: {rank_playabilities}")
    rank_order = sort_ranks_by_playability(rank_playabilities)
    print(f"rank order: {rank_order}")

    # testing find best play order
    print('\n### Test: find best play order ###')

    # with the previously calculated statistics, find the best play order after
    # taking the discard pile
    hand = ([card.rank for card in players[0].hand]
            + [card.rank for card in discard])
    print(f"player's hand after taking the discard pile: {hand}")
    play_seq = find_play_sequence(rank_order, hand)
    playability, turn_count = calc_playability(rank_playabilities, play_seq)
    print(f"play sequence: {play_seq}   playability: {playability}"
          f"   turns: {turn_count}")

    # testing find all play combinations
    print('\n### Test: find all play combinations ###')
    print(f"discard: {discard}")
    print(f'hand:    {players[0].hand}')
    combis = find_all_play_combis(state)
    print(f"plays: {[c.seq for c in combis]}")

    # testing evaluate all play combinations
    print('\n### Test: evaluate all play combinations ###')
    for i in range(len(state.players)):
        print(f'\n### Player{i+1}')
        state.player = i
        combis = evaluate_plays(state)
        for combi in combis:
            print(f"seq: {combi.seq}, hand: {combi.hand}: playability:"
                  " {combi.playability}")
        best = find_best_play(state)
        print(f"best combi: seq: {best.seq} hand: {best.hand} playability:"
              f" {best.playability}")


def main():
    """
    Test analyzer with a game state loaded from file.
    """
    # testing card statistics
    print('\n### Test: card statistics ###')

    # NOTE: in the json-file change the log-level in "log_info" to
    #       "No Secrets", since "One Line" will crash!!!
#    filename = 'shithead/analyzer_games/wolbert_turn22.json'
#    filename = 'shithead/analyzer_games/wolbert_turn40.json'
#    filename = 'shithead/analyzer_games/player2_turn11.json'

    # restore the end game state from json-file
    filename = 'shithead/analyzer_games/wolbert_turn16.json'
    state = restore_game_state(filename, True)

    # print state overview
    print(f'\n### Game state loaded from {filename}')
    state.print()

    # estimate number of turns for current player to get rid of his hand cards
#    est_turns_to_fup = state.estimate_turns_to_fup()
#    print(f"### {state.players[state.player].name} estimated turns to FUP: {est_turns_to_fup}")

    # create an analyzer for the loaded game state
    analyzer = Analyzer(state, 'Wolbert')
    # calculate playability per rank
    analyzer.calc_rank_playabilities(True)
    # calculate the average playability over all unknown cards
    analyzer.calc_refill_playability(True)

    # calculate the playabilities for Wolbert's hand cards
    print("\n### calculate hand playabilities without dummies ### ")
    analyzer.calc_avg_playability(True)

    # replace Wolbert's hand card '8-Diamonds' with dummy card '0-Clubs'
    filename = 'shithead/analyzer_games/wolbert_turn16_1_dummy.json'
    state = restore_game_state(filename, False)
    print(f'\n### Game state loaded from {filename}')
    state.print()
    analyzer = Analyzer(state, 'Wolbert')
    print("\n### calculate hand playabilities with  1 dummy ### ")
    analyzer.calc_avg_playability(True)

    # replace Wolbert's hand card '8-Diamonds' with dummy card '0-Clubs'
    # replace Wolbert's hand card '6-Spades' with dummy card '0-Clubs'
    filename = 'shithead/analyzer_games/wolbert_turn16_2_dummy.json'
    state = restore_game_state(filename, False)
    print(f'\n### Game state loaded from {filename}')
    state.print()
    analyzer = Analyzer(state, 'Wolbert')
    print("\n### calculate hand playabilities with  2 dummies ### ")
    analyzer.calc_avg_playability(True)

    # replace Wolbert's hand card '8-Diamonds' with dummy card '0-Clubs'
    # replace Wolbert's hand card '6-Spades' with dummy card '0-Clubs'
    # replace Wolbert's hand card '2-Diamonds' with dummy card '0-Clubs'
    filename = 'shithead/analyzer_games/wolbert_turn16_3_dummy.json'
    state = restore_game_state(filename, False)
    print(f'\n### Game state loaded from {filename}')
    state.print()
    analyzer = Analyzer(state, 'Wolbert')
    print("\n### calculate hand playabilities with  3 dummies ### ")
    analyzer.calc_avg_playability(True)

    # replace Player1's hand card '10-Hearts' with dummy card '0-Clubs'
    filename = 'shithead/analyzer_games/player1_turn38_1_dummy.json'
    state = restore_game_state(filename, False)
    print(f'\n### Game state loaded from {filename}')
    state.print()
    analyzer = Analyzer(state, 'Player1')
    print("\n### calculate hand playabilities with  1 dummy ### ")
    analyzer.calc_avg_playability(True)


    # Wolbert large hand 
    filename = 'shithead/analyzer_games/wolbert_turn22.json'
    state = restore_game_state(filename, False)
    print(f'\n### Game state loaded from {filename}')
    state.print()
    analyzer = Analyzer(state, 'Wolbert')
    print("\n### calculate hand playabilities ### ")
    analyzer.calc_avg_playability(True)

    # Wolbert large hand 
    filename = 'shithead/analyzer_games/wolbert_turn40.json'
    state = restore_game_state(filename, False)
    print(f'\n### Game state loaded from {filename}')
    state.print()
    analyzer = Analyzer(state, 'Wolbert')
    print("\n### calculate hand playabilities ### ")
    analyzer.calc_avg_playability(True)



#    analyzer.print_cards()
#    analyzer.print_ranks()
#    analyzer.calc_rank_probabilities()
#    analyzer.print_probs()
#    analyzer.calc_rank_playabilities()
#    analyzer.print_playabs()
#    analyzer.sort_ranks()
#    analyzer.print_rank_order()
#    analyzer.find_play_sequence()
#    analyzer.print_play_sequence()

#    analyzer = Analyzer(state, 'Wolbert')
#    playability_seq = analyzer.get_playability_seq()
#    playab_seq_strings = [f"{p:.2f}" for p in playability_seq]
#    print(f"### playability_seq: {' '.join(playab_seq_strings)}")



if __name__ == '__main__':
    main()
