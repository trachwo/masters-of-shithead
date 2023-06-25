"""
Functions for statistical hand analysis during a shithead game.

This was originally implemented to have a tool to decide whether to voluntarily
take the discard pile or not. The idea is to use the knowledge about the unknown
cards still in the game (burnt cards, talon, and player hand and face down table
cards) and the known cards still in the game (own hand cards, opponent hand
cards taken from discard, face up table cards) to calculate the probability
that a player is able to play a card. And from this we should be able to
calculate the probability to get rid of a specific hand of cards.
If do this calculation for a hand after voluntarily taking the discard pile, or
after randomly refilling our hand from the talon, we should be able to decide
if taking the discard pile is a good play.
With the same method it should be possible to chose the best card to play in a
certain situation. The AI using this method is called 'BullShit' since it lost
most of the time against the other AIs.

06.05.2023 Wolfgang Trachsler
"""

from random import randint, shuffle
from itertools import permutations
from collections import Counter

# local imports (modules in same package)
from .cards import Card, Deck, CARD_RANKS
from . import player as plr # to avoid confusion with 'player' used as variable name
from .game import Game
from .discard import Discard
from .state import State

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
    '9': ['2', '4', '5', '6', '8', '9'],
    '10': ['2', '3', '4', '5', '6', '8', '9', '10', 'J', 'Q', 'K', 'A'],
    'J': ['2', '4', '5', '6', '8', '9', 'J'],
    'Q': ['2', '4', '5', '6', '8', '9', 'J', 'Q'],
    'K': ['2', '4', '5', '6', '8', '9', 'J', 'Q', 'K'],
    'A': ['2', '4', '5', '6', '8', '9', 'J', 'Q', 'K', 'A'],
}

# to get a good average we take 'SAMPLE_RATE * len(unknown_cards)' samples
SAMPLE_RATE = 2

def calc_rank_probabilities(cards):
    """
    Calculates the probability per rank to be on top of the discard pile.

    We asume that one of the cards in play but not in our hand, will be on top of
    the discard pile then it's our next turn. By counting the number of cards of
    each rank we can calculate the probability for each rank to be on top.

    :param cards:   list of unknown cards and
                    seen opponent hand cards (ranks only).
    :type cards:    list of str
    :return:        probaility per rank
    :rtype:         dict
    """
    # count cards per rank
    count = Counter(cards)
    probs = {}
    for rank in CARD_RANKS:
        if rank in count.keys():
            probs[rank] = count[rank] / len(cards)
        else:
            probs[rank] = 0
    return probs

def calc_rank_playabilities(probs):
    """
    Calculate the probability that a card can be played as 1st play.

    We assume that from all the cards still in the game and not in our hand, one
    will randomly appear on the top of the discard pile. Now we can calculate for
    each of the card ranks the probability to be played on this top card.
    At the start of a players turn a card can only be played if her rank satisfies
    the rank of the top discard pile card (e.g. a '4' can only be played on '2',
     '4', or '7'). I.e. we can now calculate for each of our hand cards the
     probability, that a card will be at the top of the discard pile, which
     lets us play this hand card.

    :param probs:    probabilities per rank to be on top of the discard pile.
    :type _probs:    dict
    :return:         probability to be playable at begin of turn per rank.
    :rtype:          dict
    """
    playabilities = {}
    for rank in CARD_RANKS:
        prob = 0
        for r in CAN_BE_PLAYED_ON[rank]:
            prob += probs[r]
        playabilities[rank] = prob
    return playabilities

def sort_ranks_by_playability(playabilities):
    """
    Get a list of ranks sorted by playability.

    Since some of the ranks in a hand may have the same playability, we have to
    generate a unique order of ranks to make sure that after sorting a hand by
    playability, all cards of same rank are played after each other.

    :param playabilities:   playability per rank
    :type playabilities:    dict
    :return:                list of all ranks sorted by playability
    :rtype:                 list
    """
    # sorting key function => gets playability per rank
    def get_rank_playability(rank):
        return playabilities[rank]

    # get a rank order sorted by playability
    rank_order = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    rank_order.sort(key=get_rank_playability, reverse=True)
    return rank_order

def find_play_sequence(rank_order, hand):
    """
    Find the best play sequence to play a hand of cards.

    We sort a hand of cards in a way, that playing it in sequence from 1st to last
    card yields the best probability to get rid of all cards.
    We first sort all cards according to the playability of their rank, with the
    highest playability first and the rank with the worst playability last.
    Starting with the highest playability we play as many cards of the same rank
    as possible. If we can play 4 or more cards of the same rank, this will kill
    the discard pile, i.e. in this case we now play the cards with the worst
    playability. Otherwise we play the cards which now have the best playability,
    from the beginning of the list.
    The '10' is treated specially, since each played '10' kills the discard pile,
    we always play the rank with worst playability before playing anonter '10'.
    The 'Q' is also treated specially, since we can play immediately another card.
    Usually this will be the card with the worst playability, but with the
    possibility to play 4 'Q's in a row and only 1 other rank left, it is
    preferable to play the 'Q's first.

    :param rank_order:  list of all ranks sorted by playability
    :type rank_order:   dict
    :param hand:        list of ranks in hand
    :type hand:         list
    :return:            ranks in sequence of optimum play
    :rtype:             list
    """
    # sorting key function => gets index of rank in rank order
    def get_rank_order(rank):
        return rank_order.index(rank)

    # cannot rearrange empty hand
    if len(hand) == 0:
        return []

    # sort the hand according to the rank_order
    hand.sort(key=get_rank_order)

    # play rank with highest playability first
    play_seq = []    # list for ranks in play order
    play_seq.append(hand.pop(0))
    same_rank_count = 1
    play_best = True

    while(len(hand) > 0):
        if play_seq[-1] == '10':
            # we played a '10' and killed the discard pile
            # => we can play the any card, i.e. the one with the worst playability
            play_seq.append(hand.pop(-1))
            play_best = False    # => play from end of list
            same_rank_count = 1    # reset same rank counter

        elif play_seq[-1] == 'Q':
            if play_best:
                # played 'Q' from start of list, i.e. we could now play any card with worse
                # playability on the 'Q' or maybe play 4 'Q's to kill the discard pile
                # count number of 'Q's still in the Hand
                count = Counter(hand)
                if count['Q'] > 0 and count['Q'] + same_rank_count >= 4:
                    # we could play all 'Q's to kill the discard pile
                    # do it if there's only one other rank left
                    if len(count.keys()) <= 2:
                        # play another 'Q'
                        play_seq.append(hand.pop(0))
                        same_rank_count += 1
                    else:
                        # better play cards with worse playability first
                        play_seq.append(hand.pop(-1))
                        play_best = False    # => play from end of list
                        same_rank_count = 1    # reset same rank counter
                else:
                    # no more 'Q's or less than 4 'Q's in total
                    # => play card with worser playability first
                        play_seq.append(hand.pop(-1))
                        play_best = False    # => play from end of list
                        same_rank_count = 1    # reset same rank counter
            else:
                # 'Q' has been played from end of list
                # => keep playing from end of list 'Q' or next worse rank
                play_seq.append(hand.pop(-1))
                if play_seq[-1] == 'Q':
                    same_rank_count += 1
                else:
                    same_rank_count = 1

        elif play_seq[-1] in hand:
            # more cards with same rank as previous card in hand
            same_rank_count +=1
            if play_best:
                # play from begin of list
                play_seq.append(hand.pop(0))
            else:
                # play from end of list
                play_seq.append(hand.pop(-1))
        else:
            # no more cards with same rank
            # => check if we have played 4 or more
            if same_rank_count >= 4:
                # we killed the discard pile and can play any card
                play_best = False
                # play card with bad playability from the end of the list
                play_seq.append(hand.pop(-1))
            else:
                # play the next rank with best playability
                play_seq.append(hand.pop(0))
                play_best = True    # play from begin of list
            # next rank => reset same rank count
            same_rank_count = 1

    return play_seq

def calc_playability(rank_playabilities, play_seq):
    """
    Calculate the playability of a play sequence.

    Calculates the probability to get rid of a hand of cards then played in the
    specified sequence.

    :param rank_playabilities:  playability per rank
    :type rank_playabilities:   dict
    :param play_seq:            hand of cards sorted in sequence of play.
    :type play_seq:             list
    :return:                    playability, number of turns
    :rtype:                     tuple
    """
    if len(play_seq) == 0:
        # no cards to play
        return (1, 0)
    playability = rank_playabilities[play_seq[0]]
    same_rank_count = 1
    turn_count = 1
    for i in range(1, len(play_seq)):
        if play_seq[i] == play_seq[i-1]:
            # same rank as previous
            # => play this card for free (same turn)
            same_rank_count += 1    # increment count
        elif same_rank_count >= 4:
            # different rank than previous card
            # >4 cards of same rank kill the discard pile
            # => play this card for free (same turn)
            same_rank_count = 1        # reset the count
        elif play_seq[i-1] == '10':
            # different rank than previous card
            # '10' kills the discard pile
            # => play this card for free (same turn)
            same_rank_count = 1        # reset the count
        elif play_seq[i-1] == 'Q':
            # different rank than previous card
            # 'Q' must be covered
            # => play this card for free (same turn)
            same_rank_count = 1        # reset the count
        else:
            # different rank than previous card
            # => played at beginning of another turn
            # probability that this card and all previous cards can be played
            playability *= rank_playabilities[play_seq[i]]
            same_rank_count = 1    # reset the count
            turn_count += 1        # increment the turn count

    return (playability, turn_count)

def check_permutations(rank_playabilities, hand):
    """
    Find best play sequence by checking all permutations of hand.

    Calculate the playability for all permutations of the specified hand in order
    to find the best play sequence.
    DON'T USE this for hands > 10 cards, it takes forever.

    :param playable_probs:    playability per rank
    :type playable_probs:    dict
    :param hand:            list of ranks in hand
    :type hand:                list
    """
    playability_max = 0
    turns_max = len(hand) + 1
    for play_seq in permutations(hand):
        playability, turns = calc_playability(rank_playabilities, play_seq)
        if (playability > playability_max or playability == playability_max and
                turns < turns_max):
            playability_max = playability
            turns_max = turns
            seq_max = play_seq
    print(f"### check_permutations: {seq_max} playability: {playability_max} turns: {turns_max}")

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
        expansions = [] # list of expanded combinations based on this combi

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
        :param max_draws:   number of cards we could draw before talon is empty.
        :type max_draws:    int
        """
#        print(f"### seq: {self.seq}   hand: {self.hand}")
        total_playability = 0
        total_turns = 0
        n_samples = 1   # no refill => just calculate playability of hand
        if len(self.hand) < size and max_draws > 0:
            # randomly refill hand n_samples time and calculate average
            # playability over all samples
            n_samples = len(self.unknown) * SAMPLE_RATE

        for i in range(n_samples):
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
            playability, turn_count = calc_playability(rank_playabilities, play_seq)
#            if size > 3:
#                print(f"play_seq: {play_seq}   playability: {playability}   turns: {turn_count}")
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

    first = (state.n_played == 0)               # 1st card played this turn
    top_rank = discard.get_top_rank()           # rank at top of discard pile

    # get ranks of cards from which we don't known where they are
    unknown = [card.rank for card in state.get_unknown_cards()]
    # get ranks of cards which are in the hands of opponents
    seen = [card.rank for card in state.get_seen_cards()]

    if len(discard) > 0:
        # there's a discard pile
        if first:
            # at the begin of a turn we can always decide to take the discard pile.
            # => add combi with empty sequence and discard pile added to hand.
            in_progress.append(Combi(unknown, seen, [],
                    [c.rank for c in hand] + [c.rank for c in discard], 0, None))
        else:
            # if this is not the 1st card played this turn, it is possible that
            # we can end the turn without playing a further card.
            # => add combi with empty sequence to list
            n_top = discard.get_ntop()  # number of cards with same rank at top
            in_progress.append(Combi(unknown, seen, [], [c.rank for c in hand],
                    n_top, top_rank))

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

    while(len(in_progress) > 0):
        # there are still unfinished combinations to be handled
#        print(f"seq: {[combi.seq for combi in in_progress]}")
#        print(f"hand: {[combi.hand for combi in in_progress]}")
#        print(f"n_top: {[combi.n_top for combi in in_progress]}")
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
    n_turns, n_draws, n_hand_after = state.estimate_remaining_draws(n_hand)

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
            n_turns, n_draws, n_hand_after = state.estimate_remaining_draws(n_hand)
            bup = best.playability  # backup the playability value
            best.evaluate(3 + int(combis[0].turns), n_draws)
            if best.playability + 0.2 < combis[0].playability:
#                print('### take the discard pile ###')
#                print(f"take discard pile: hand: {combis[0].hand} playability: {combis[0].playability} turn count: {combis[0].turns}/{int(combis[0].turns)}")
#                print(f"not taking discard pile: seq: {best.seq} hand: {best.hand} playability: {best.playability}")
                best = combis[0]
            else:
                # restore the original playablility
                best.playability = bup

    # check if the best combination has a play sequence containing a single '2',
    # and  a '3' on hand. Depending on the top card of the discard
    # pile swap the '2' with the '3' (Druck mache!)
    if len(best.seq) == 1 and best.seq[0] == '2' and '3' in best.hand:
        if state.discard.get_top_rank() in ['7', 'K', 'A']:
            best.seq[0] == '3'
            idx = best.hand.index('3')
            best.hand[idx] = '2'

    return best

def find_best_fup_pick(state, get_fup_rank):
    """
    Find best face up table card to pick up after taking the discard pile.

    When taking the discard pile while playing from the face up table cards,
    the play may also take one card or several cards of same rank from his face
    up table cards on hand. I.e. each rank in the face up table cards results
    at least in a play sequence, where we pick up 1 card of this rank. If there
    are multiple cards with the same rank, it's also possible to pick up 2 or
    even 3 cards.

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
        for rank in count.keys():
            for i in range(count[rank]):
                seq.append(rank)
                hand.remove(rank)
                # create combination
                combi = Combi(unknown, seen, seq, hand, 0, None)
                # calculate playability of remaining cards (no refill)
                combi.evaluate(0,0)
                combis.append(combi)
    else:   # 2nd or 3rd pick
        # we can always stop after the 1st pick
        # => empty play sequence
        combi = Combi(unknown, seen, seq, hand, 0, None)
        # calculate playability of remaining cards (no refill)
        combi.evaluate(0,0)
        combis.append(combi)
        if get_fup_rank in count.keys():
            # more cards with same rank as 1st pick
            for i in range(count[get_fup_rank]):
                seq.append(get_fup_rank)
                hand.remove(get_fup_rank)
                # create combination
                combi = Combi(unknown, seen, seq, hand, 0, None)
                # calculate playability of remaining cards (no refill)
                combi.evaluate(0,0)
                combis.append(combi)

    # find the combi with the highest playability
    playabilities = [combi.playability for combi in combis]
    best = combis[playabilities.index(max(playabilities))]
    return best

def main():

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
    hand = [card.rank for card in players[0].hand] + [card.rank for card in discard]
    print(f"player's hand after taking the discard pile: {hand}")
    play_seq = find_play_sequence(rank_order, hand)
    playability, turn_count = calc_playability(rank_playabilities, play_seq)
    print(f"play sequence: {play_seq}   playability: {playability}   turns: {turn_count}")

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
            print(f"seq: {combi.seq}, hand: {combi.hand}: playability: {combi.playability}")
        best = find_best_play(state)
        print(f"best combi: seq: {best.seq} hand: {best.hand} playability: {best.playability}")

if __name__ == '__main__':
    main()








