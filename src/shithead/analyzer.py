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

from collections import Counter
import json

# local imports (modules in same package)
from .cards import CARD_RANKS
from . import player as plr  # to avoid confusion with variable 'player'
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

        self.unknown = []           # ranks of unknown cards
        self.seen = []              # ranks of known opponent cards
        self.playabs = {}           # playabilities per rank
        self.play_seq = []          # list of ranks in play order
        self.n_turns = 0            # number of turns
        self.play_from_hand = True  # True => hand cards played

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
        probs_str = []
        playabs_str = []

        # count cards per rank
        count = Counter(ranks)  # count per rank
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
            avg = sum(playabs) / len(playabs)

        if verbose:
            playabs_str = [f"{playab:.2f}" for playab in playabs]
            print(f"### sequence playabilities: {' '.join(playabs_str)}")

        return avg

    def get_play_sequence(self, verbose=False):
        """
        Get the play sequence for the hand or face up table cards.

        For 3 or less cards we just return the ranks in the hand or face up
        table cards as they are.
        Hands with more than 3 cards are sorted in a way, that playing it in
        sequence from 1st to last card yields the best probability to get rid
        of all cards. We first sort all cards according to the playability of
        their rank, with the highest playability first and the rank with the
        worst playability last. Starting with the highest playability we play
        as many cards of the same rank as possible. If we can play 4 or more
        cards of the same rank, this will kill the discard pile, i.e. in this
        case we now play the cards with the worst playability. Otherwise we
        play the cards which now have the best playability, from the beginning
        of the list. The '10' is treated specially, since each played '10'
        kills the discard pile, we always play the rank with worst playability
        before playing another '10'. The 'Q' is also treated specially, since
        we can immediately play another card. Usually this will be the card
        with the worst playability, but with the possibility to play 4 'Q's in
        a row and only 1 other rank left, it is preferable to play the 'Q's
        first.

        :param verbose:     True => print play sequence
        :type verbose:      bool
        """
        self.play_seq = []  # found play sequence

        # make sure the rank playabilities have been calculated
        if len(self.playabs) == 0:
            self.calc_rank_playabilities(verbose)
        # make sure the average refill playability has been calculated
        if len(self.playabs) == len(CARD_RANKS):
            self.calc_refill_playability(verbose)

        if len(self.player.hand) > 0:
            # get a list of ranks in player's hand cards
            ranks = ([card.rank for card in self.player.hand])
            self.play_from_hand = True
        elif len(self.player.face_up) > 0:
            # get a list of ranks in player's face up table cards
            ranks = ([card.rank for card in self.player.face_up])
            self.play_from_hand = False     # add bonus
        else:
            # only face down table cards left => nothing to do
            ranks = []      # add bonus

        # 3 or less cards
        if len(ranks) <= 3:
            self.play_seq = ranks[:]
            return      # nothing more to do

        # >3 cards on hand => find best play sequence
        # default rank order
        rank_order = ['3', '2', '10', 'A', 'K', 'Q', 'J', '9', '8', '7',
                           '6', '5', '4', '0']

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
        self.play_seq.append(ranks.pop(0))
        same_rank_count = 1     # played 1 card of this rank
        play_best = True        # => play best ranks first

        # loop through remaining cards in the original sequence
        while len(ranks) > 0:
            if self.play_seq[-1] == '10':
                # we played a '10' and killed the discard pile
                # => we can play any card,
                # i.e. play the one with the worst playability next
                self.play_seq.append(ranks.pop(-1))
                play_best = False       # => play from end of list
                same_rank_count = 1     # reset same rank counter

            elif self.play_seq[-1] == 'Q':
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
                            self.play_seq.append(ranks.pop(0))
                            same_rank_count += 1
                        else:
                            # better play cards with worse playability first
                            self.play_seq.append(ranks.pop(-1))
                            play_best = False       # => play from end of list
                            same_rank_count = 1     # reset same rank counter
                    else:
                        # no more 'Q's or less than 4 'Q's in total
                        # => play card with worser playability first
                        self.play_seq.append(ranks.pop(-1))
                        play_best = False       # => play from end of list
                        same_rank_count = 1     # reset same rank counter
                else:
                    # 'Q' has been played from end of list
                    # => keep playing from end of list 'Q' or next worse rank
                    self.play_seq.append(ranks.pop(-1))
                    if self.play_seq[-1] == 'Q':
                        same_rank_count += 1    # 1 more 'Q' played
                    else:
                        same_rank_count = 1     # 1st card of next rank played

            elif self.play_seq[-1] in ranks:
                # more cards with same rank as previous card in hand
                same_rank_count += 1
                if play_best:
                    # play from begin of list
                    self.play_seq.append(ranks.pop(0))
                else:
                    # play from end of list
                    self.play_seq.append(ranks.pop(-1))
            else:
                # no more cards with same rank
                # => check if we have played 4 or more cards of same rank
                if same_rank_count >= 4:
                    # we killed the discard pile and can play any card
                    play_best = False
                    # play card with bad playability from the end of the list
                    self.play_seq.append(ranks.pop(-1))
                else:
                    # play the next rank with best playability
                    self.play_seq.append(ranks.pop(0))
                    play_best = True    # play from begin of list
                # next rank => reset same rank count
                same_rank_count = 1

        if verbose:
            print(f"### play sequence: {' '.join(self.play_seq)}")

    def get_number_of_turns(self, verbose=False):
        """
        Determine the number of turns to play from the play sequence.

        Determines the minimum number of turns to play the hand or face up
        table cards from the play sequence found during get_play_sequence().

        :param verbose:     True => print play sequence
        :type verbose:      bool
        :return:            number of turns.
        :rtype:             int
        """
        # make sure the play sequence has been determined.
        if len(self.play_seq) == 0:
            self.get_play_sequence(verbose)

        # make sure play sequence is not empty.
        if len(self.play_seq) == 0:
            return 0

        # 1st rank
        n_turns = 0
        same_rank_count = 0

        for idx, rank in enumerate(self.play_seq):
            if idx == 0:
                # 1st card => initialize counters
                n_turns = 1
                same_rank_count = 1
            else:
                if rank == self.play_seq[idx - 1]:
                    # same rank as previous card
                    same_rank_count += 1
                else:
                    # change of rank
                    if (same_rank_count < 4
                            and self.play_seq[idx - 1] != '10'
                            and self.play_seq[idx - 1] != 'Q'):
                        # discard not killed and not played on 'Q'
                        # => increment turn counter
                        n_turns += 1
                    # reset same rank counter
                    same_rank_count = 1
        if verbose:
            print(f"### number of turns: {n_turns}")

        return n_turns

    def get_effective_seq(self, verbose=False):
        """
        Determine the effective play sequence.

        The play sequence found with get_play_sequence() can be reduced by 1st
        removing all continues sequences of low ranks ('4', '5', '6', '8', '9',
        'J') following 'Q', '10', or another sequence of >=4 cards with same
        rank (=> low cards which can be played for free do not reduce the
        average playability of the hand). The remaining sequences of low ranks
        are each replaced with a single occurance of this rank (=> all cards of
        same low rank can be played in 1 turn and have therefore less impact
        on the average playability). Note that sequences of '2', '3', 'Q', 'K',
        and 'A' are left intact to maximize their impact on the average
        playability.

        :param verbose:     True => print play sequence
        :type verbose:      bool
        :return:            number of turns.
        :rtype:             int
        """
        # make sure the play sequence has been determined.
        if len(self.play_seq) == 0:
            self.get_play_sequence(verbose)

        # make sure play sequence is not empty.
        if len(self.play_seq) == 0:
            return []

        eff_seq = []
        good_ranks = ('3', '2', '10', 'A', 'K', 'Q')

        # 1st rank
        same_rank_count = 0

        for idx, rank in enumerate(self.play_seq):
            if idx == 0:
                # 1st card => initialize counters
                eff_seq.append(rank)
                same_rank_count = 1
            else:
                if rank == self.play_seq[idx - 1]:
                    # same rank as previous card
                    same_rank_count += 1
                    if rank in good_ranks:
                        eff_seq.append(rank)
                else:
                    # change of rank
                    if (same_rank_count < 4
                            and self.play_seq[idx - 1] != '10'
                            and self.play_seq[idx - 1] != 'Q'):
                        # discard not killed and not played on 'Q'
                        # => add rank to effective sequence
                        eff_seq.append(rank)
                    else:
                        # could be played for free
                        if rank in good_ranks:
                            # only add good rank to effective sequence
                            eff_seq.append(rank)
                    # reset same rank counter
                    same_rank_count = 1
        if verbose:
            print(f"### eff_seq: {' '.join(eff_seq)}")

        return eff_seq

    def calc_avg_playability(self, verbose=False):
        """
        Calculate the average playability for hand or face up table cards.

        If this player is out of the game (no cards left), we return 10.0 to
        indicate that the best possible outcome has been reached.
        If only face down table cards are left, we return 5.0 to indicate, that
        the 2nd best outcome has been reached.
        If only face up and face down table cards are left, we calculate the
        average playability of the face up table cards and add 1.0 to make this
        a better outcome than any hand cards playability.
        For 3 or less hand cards we just return their average playability.
        For hand with more than 3 cards we calculate the average playability of
        the corresponding effective play sequence.

        :param verbose:     True => print play sequence
        :type verbose:      bool
        :return:            average playability
        :rtype:             float
        """
        avg = 0             # average playability for hand/fup cards

        # player is already out
        if self.player is None:
            return 10.0     # best possible outcome

        # make sure the rank playabilities have been calculated
        if len(self.playabs) == 0:
            self.calc_rank_playabilities(verbose)
        # make sure the average refill playability has been calculated
        if len(self.playabs) == len(CARD_RANKS):
            self.calc_refill_playability(verbose)
        # make sure the play sequence has been determined
        if len(self.play_seq) == 0:
            self.get_play_sequence(verbose)

        if len(self.play_seq) == 0:
            # no hand or face up table cards left
            return 5.0      # 2nd best possible outcome

        if len(self.play_seq) <= 3:
            avg = self.calc_seq_playability(self.play_seq, verbose)
            if not self.play_from_hand:
                # playing face up table cards
                avg += 1.0  # add bonus
        else:
            # >3 cards in play sequence => get effective play sequence
            eff_seq = self.get_effective_seq(verbose)
            # calculate average playability for effective play sequence
            avg = self.calc_seq_playability(eff_seq, verbose)

        if verbose:
            print(f"### average playability: {avg:.2f}")

        return avg


def restore_game_state(filename, verbose=False):
    """
    Restores a game state from json-file.

    Loads state info from the provided json-file.
    Creates a list of players (2 x 'CheapShit' and 1 x BullShit) and uses it
    to create the initial game state.
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


def main():
    """
    Test analyzer with a game state loaded from file.
    """
    # testing card statistics
    print('\n### Test: card statistics ###')

    # NOTE: in the json-file change the log-level in "log_info" to
    #       "No Secrets", since "One Line" will crash!!!

    # restore the end game state from json-file
    filename = 'shithead/analyzer_games/wolbert_turn16.json'
    state = restore_game_state(filename, True)

    # print state overview
    print(f'\n### Game state loaded from {filename}')
    state.print()

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


if __name__ == '__main__':
    main()
