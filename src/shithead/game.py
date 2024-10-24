'''
Game class for the Shithead game.

This is where the rules of the Shithead game are implemented.
Since the actual game state is kept in the State objects, all methods of the
Game class are class methods, i.e. we don't have to instantiate a Game object.
Depending on the current game state (current player, discard pile, etc.) the
current player has to select one of the legal plays available for this statet,
which is then applied to the state in order to get to the next game state.

23.08.2022  Wolfgang Trachsler
'''

from math import ceil
from random import randint

# local imports (modules in same package)
from .cards import Card
from .state import State, SWAPPING_CARDS, FIND_STARTER, PLAY_GAME
from .state import SHITHEAD_FOUND, ABORTED
from .discard import Discard

# uncomment this import if you want to run initial_tests()
# but you'll get a cirular init error when running other stuff !!!

CARDS_PER_PLAYER = 17       # to calculate the number of decks needed
CARDS_PER_DECK = 52         # number of cards in a deck


# -----------------------------------------------------------------------------
class Game:
    '''
    Class representing a Shithead game.

    Implements the game state machine, i.e. the game state reached from a given
    game state when applying a given game play.
    Note, that Game itself has no attributes and only class methods, since the
    actual state of the shithead game is stored in objects of the State class.
    '''
    @classmethod
    def calc_nof_decks(cls, n_players):
        '''
        Calculate number of decks necessary for this number of players.
        The minimum number of cards necessary per player is 17 (6 face up/down
        table cards, 3 hand cards, and about 8 cards per player to draw from
        the talon).

        :param n_players:   number of players.
        :type n_players:    int
        :return:            number of decks
        :rtype:             int
        '''
        # calculate the minimum number of cards necessary
        cmin = n_players * CARDS_PER_PLAYER
        # calculate then necessary number of decks
        return ceil(cmin/CARDS_PER_DECK)

    @classmethod
    def calc_burnt_cards(cls, n_players):
        '''
        Calculate number of burnt cards, i.e. cards removed from talon before
        the game starts. The minimum number of cards necessary per player is 17
        (6 face up/down table cards, 3 hand cards, and about 8 cards per player
        to draw from the talon). The additional cards reduced by a random
        number between 1 and twice the number of players are removed from the
        talon.

            | players | min | decks | max | burned |
            +---------+-----+-------+-----+--------+
            |    2    |  34 |   1   |  52 | 14..18 |
            |    3    |  51 |   1   |  52 |  0     |
            |    4    |  68 |   2   | 104 | 28..36 |
            |    5    |  85 |   2   | 104 |  9..19 |
            |    6    | 102 |   2   | 104 |  0     |
            +---------+-----+-------+-----+--------+

        :param n_players:   number of players.
        :type n_players:    int
        :return:            number of burnt cards
        :rtype:             int
        '''
        # calculate the minimum number of cards necessary
        cmin = n_players * CARDS_PER_PLAYER
        n_decks = ceil(cmin/CARDS_PER_DECK)
        # calculate number of additional cards per player
        additional_cards = n_decks * CARDS_PER_DECK - cmin
        if additional_cards < 2 * n_players:
            # less than 2 additonal cards per player => use all cards
            return 0
        else:
            # more than 2 additional cards per player
            # => remove some of the additional cards
            #    but randomly keep up to 2 cards per player.
            n_burnt = additional_cards - randint(1, 2 * n_players)
            return int(n_burnt)

    @classmethod
    def deal(cls, players, dealer, talon):
        '''
        Deal cards to players.

        Deal one card at a time in clockwise direction to each player starting
        with the player following the dealer in clockwise direction.
        1. deal 3 face down table cards to each player.
        2. deal 3 face up table cards to each player.
        3. deal 3 face down hand cards to each player.

        Note, that the players know where to put each of the cards in
        accordance with the sequence in which they are dealt, we don't have to
        tell them where to put them.

        :param players: list of players
        :type players:  list
        :param dealer:  player dealing cards (index)
        :type dealer:   int
        :param talon:   talon of shuffled cards.
        :type talon:    Deck
        '''
        n_players = len(players)
        # deal each player 3 face down table cards.
        for _ in range(3):
            for j in range(n_players):
                players[(dealer + 1 + j) % n_players].deal(talon.pop_card())

        # deal each player 3 face up table cards.
        for _ in range(3):
            for j in range(n_players):
                card = talon.pop_card()
                card.seen = True    # we always know where this card is
                players[(dealer + 1 + j) % n_players].deal(card)

        # deal each player 3 face down hand cards.
        for _ in range(3):
            for j in range(n_players):
                players[(dealer + 1 + j) % n_players].deal(talon.pop_card())

    @classmethod
    def get_current_player(cls, state):
        '''
        Get current player.

        :param state:   current game state.
        :type state:    State
        :return:    current player
        :rtype:     Player
        '''
        return state.players[state.player]

    @classmethod
    def find_next_player(cls, state, out=False):
        '''
        Evaluate next player according to current state.

        Uses current direction and number of 'K's to find new direction.
        Uses current player, new direction, and number of '8's to find next
        player.

        :param state:   current game state.
        :type state:    State
        :param out:     True => current player is out.
        :type out:      bool
        :return:        direction and next_player
        :rtype:         tuple
        '''
        # if an odd number of 'K's has been added during this turn, change the
        # current direction.
        if state.kings % 2:
            direction = not state.direction
        else:
            direction = state.direction

        # find next player in game direction.
        player = state.player
        n_players = len(state.players)
        if direction:   # clockwise
            next_player = (player + 1) % n_players
        else:           # counterclockwise
            next_player = (player + n_players - 1) % n_players

        # skip over players according to the number of '8's played this turn
        for _ in range(state.eights):
            if direction:   # clockwise
                next_player = (next_player + 1) % n_players
                # don't count current player if he's already out
                if next_player == player and out:
                    next_player = (next_player + 1) % n_players
            else:   # counterclockwise
                next_player = (next_player + n_players - 1) % n_players
                # don't count current player if he's already out
                if next_player == player and out:
                    next_player = (next_player + n_players - 1) % n_players
        return (direction, next_player)

    @classmethod
    def discard_card(cls, state, source, card):
        '''
        Play card on discard pile.

        Add card on top of discard pile.
        Increment the number of cards played this turn.
        Resolve card effects:
            - '10'  => kill discard pile.
            - '8'   => skip player.
            - 'K'   => change direction.

        :param state:   game state in which this card was played.
        :type state:    State
        :source:        card source ('HAND', 'FUP', 'FDOWN')
        :param card:    card played on discard pile.
        :type card:     Card
        '''
        # get current player
        player = cls.get_current_player(state)

        # from now on we always know where this card is
        card.seen = True  # no longer unknown => mark it as face up

        # cards played from hand or face up table cards always fit the discard
        # pile, but cards played from face down table cards may not fit the
        # discard pile => take the discard pile
        first = state.n_played == 0     # 1st card played this turn
        if not state.discard.check(first, card):
            # Doesn't fit => make sure it's not a hand or face up table card
            if (source == 'HAND') or (source == 'FUP'):
                raise ValueError(f"Legal play of {card} from {source}"
                                 " which doesn't fit the discard pile!")
            # add this face down table card to the players hand
            player.hand.add_card(card)
            # take the discard pile
            for _ in range(len(state.discard)):
                # get card at top of discard pile
                card = state.discard.pop_card()
                # and add it to hand cards of this player
                player.hand.add_card(card)
            player.hand.sort()  # always keep hand sorted
            # and end turn
            cls.end_turn(state)
        else:
            # put card on top of the discard pile.
            state.discard.add_card(card)
            # resolve special card effects
            if card.rank == '10':
                # kill the discard pile
                # move all cards from the discard pile to the removed cards
                # pile.
                for _ in range(len(state.discard)):
                    card = state.discard.pop_card()
                    state.killed.add_card(card)
            elif card.rank == '8':
                # increment the number of skipped players
                state.eights += 1
                # immediately reflect in state
                direction, player = cls.find_next_player(state)
                state.next_direction = direction
                state.next_player = player
            elif card.rank == 'K':
                # reverse the direction of play
                state.kings += 1
                # immediately reflect in state
                direction, player = cls.find_next_player(state)
                state.next_direction = direction
                state.next_player = player

        # increment number of cards played this turn
        state.n_played += 1

    @classmethod
    def resolve_auction(cls, state):
        '''
        Check if a starting player has been found.

        If a single player showed the starting card, he becomes the starting
        player.
        If no player showed the starting card, or multiple players have shown
        the starting cards and all available starting cards (number of decks)
        have been shown, the auction has to be repeated with the next higher
        starting cards. If no more starting cards are left (i.e. we tried every
        52 possible cards without a player showing one of his hand cards) we
        continue with the normal game and the player following the dealer as
        starting player. If multiple players have shown the starting card, they
        are the only players allowed to bid in the next auction round.

        :param state:   game state in which this card was played.
        :type state:    State

        TODO do a test simulating some extreme cases
        '''
        n_shown = len(state.shown_starting_card)
        # check if we have found a starting player
        if n_shown == 1:
            # a single player showed the starting card
            state.player = state.shown_starting_card[0]
            state.next_player = (state.player + 1) % len(state.players)
            state.game_phase = PLAY_GAME
            state.turn_count = 1

        elif n_shown == 0 or (n_shown > 1 and n_shown == state.n_decks):
            # nobody showed the starting card
            # or multiple players have shown all available starting cards
            # => try next higher starting card.
            state.starting_card += 1
            if state.starting_card >= CARDS_PER_DECK:
                # no more starting cards left
                # starting player is the player following the dealer.
                state.player = state.starter
                state.next_player = (state.player + 1) % len(state.players)
                state.game_phase = PLAY_GAME
                state.turn_count = 1

        if state.game_phase == FIND_STARTER:
            # we haven't found the starting player yet
            # => prepare for the next bidding round
            if n_shown > 0:
                # only the players who showed a card are still in the auction
                state.auction_members = state.shown_starting_card[:]
            state.shown_starting_card = []
            state.player = state.auction_members[0]
            state.next_player = state.auction_members[1]
            state.turn_count = 0

    @classmethod
    def end_turn(cls, state, fup_table=None, stats=None, out=False):
        '''
        End current players turn.

        Use current direction and number of 'K's to find new direction.
        Use current player, new direction, and number of '8's to find next
        player.
        Reset number of played cards in current turn.
        Reset number of played 'K's in current turn.
        Reset number of played '8's in current turn.

        :param state:       current game state.
        :type state:        State
        :param fup_table:   face up table (out and SWAPPING_CARDS only).
        :type fup_table:    FupTable
        :param stats:       statistic (out only).
        :type stats:        Statistic
        :param out:         True => current player is out.
        :type out:          bool
        '''
        # increment the turn counter of this game
        state.turn_count += 1

        player = state.player
        # increment the turn counter of the current player
        if state.game_phase == PLAY_GAME:
            state.players[player].turn_count += 1
        elif state.game_phase == SWAPPING_CARDS:
            state.players[player].turn_count = 0

        # reset get_fup and get_fup_rank of current player
        # this is used turing a player's turn to indicate that he has to pick
        # up a face up table card after taking the discard pile playing from
        # face up table cards. 'get_fup_rank' is the rank of the card if he
        # already has picked up 1 card (maybe there's another one)
        state.players[player].get_fup = False
        state.players[player].get_fup_rank = None
        # get direction of play and next player
        direction, next_player = cls.find_next_player(state, out)

        if out:
            # get name and turn count of player before removing him
            name = state.players[player].name
            turn_count = state.players[player].turn_count
            # remove the current player from the list
            if state.player < next_player:
                # index of next player decrements,
                # since the current player is removed from the list
                next_player -= 1
            # current player is out => remove from the list
            state.players.pop(state.player)
            # update statistics
            score = len(state.players)  # score = number of remaining players
            # enter score for this player in state
            state.result[name] = [score, turn_count]
            # check if game is over => only shithead left
            if score == 1:
                shithead = state.players[next_player]
                state.result[shithead.name] = [0, turn_count]
                state.game_phase = SHITHEAD_FOUND
            if stats:
                # if a statistic has been specified update it
                stats.update(name, score, turn_count)
            if fup_table:
                # if a face up table has been specified
                # (=> fup_table_generator), update the score fup table score
                # (= number of remaining players)
                score = len(state.players)
                # update face up table
                fup_table.score(name, score)

        # reset counters
        state.n_played = 0
        state.kings = 0
        state.eights = 0
        # set new direction
        state.direction = direction
        # set new current player
        state.player = next_player
        # also update the supposed next direction/player
        direction, player = cls.find_next_player(state)
        state.next_direction = direction
        state.next_player = player

        if state.game_phase == SWAPPING_CARDS:
            if fup_table:
                # if a face up table has been specified store the initial face
                # up table cards => fup table generator
                # get list of face up table cards.
                fup = [card for card in state.players[player].face_up]
                name = state.players[player].name
                # store face up table cards in face up table
                fup_table.store(name, fup)

            # check if every player had chance to swap cards.
            # player, next_player was already set above
            if state.turn_count == len(state.players):
                # change to finding starting player phase
                state.game_phase = FIND_STARTER
                state.turn_count = 0

        elif state.game_phase == FIND_STARTER:
            # check if every player has made a bid or passed.
            if state.turn_count == len(state.auction_members):
                # each player still in the auction has shown a card or passed
                # => check if a starting player has been found
                #    overwrites player, next_player, and resets turn count
                cls.resolve_auction(state)
            else:
                # find next player to bid in the auction
                # note, may be different from player/next_player set above
                state.player = state.auction_members[state.turn_count]
                state.next_player = (state.auction_members[
                    (state.turn_count + 1) % len(state.auction_members)])

    @classmethod
    def next_state(cls, state, play, fup_table=None, stats=None):
        '''
        Apply the specified play to the current state to get the next state.
            - SHUFFLE       => shuffle the talon.
            - BURN          => move some cards from the talon to the burnt
                               cards pile.
            - DEAL          => deal 3 face up, 3 face down, and 3 hand cards
                               to each player.
            - GET, index    => take face up table card at index on hand.
            - PUT, index    => put hand card at index to face up table cards.
            - SHOW, index   => show hand card at index in starter auction.
            - HAND, index   => play hand card at index to discard pile.
                            => resolve effects:
                                - '10'  => kill discard pile.
                                - '8'   => skip player.
                                - 'K'   => change direction.
            - FUP, index    => play face up table card at idx to discard pile.
                            => resolve card effects ('10', '8', 'K').
            - FOOWN, index  => play face dwn table card at idx to discard pile.
                            => resolve card effects ('10, '8', 'K').
            - OUT           => remove player from list of active players.
                            => check if only one player left (end of game).
                            => end turn:
                                - current player = next player.
                                - number of cards played = 0.
            - TAKE          => add discard pile cards to hand cards.
                            => end turn:
                                - current player = next player.
                                - number of cards played = 0.
            - KILL          => remove all cards from the discard pile, because
                               4 or more cards of same rank are at the top.
            - REFILL        => add cards from talon to (unknown) hand cards,
                               to fill the player's hand up to 3 cards.
            - END           => end turn:
                                - current player = next player.
                                - number of cards played = 0.
            - DEALER, index => make players[index] the dealer.

        :param state:       current shithead state
        :type state:        State
        :param play:        current player's play
        :type play:         Play
        :param fup_table:   face up table (only for creating new fup table).
        :type fup_table:    FupTable
        :param stats:       statistic => score, nbr of turns, nbr of games.
        :type stats:        Statistic
        :return:            game state after specified play has been applied.
        :rtype:             State
        '''
        # start with the current state
        next_state = state

        # shortcuts
        players = next_state.players
        dealer = next_state.dealer
        player = cls.get_current_player(next_state)
        talon = next_state.talon
        burnt = next_state.burnt
        action = play.action
        index = play.index
        card = None

        # store the log info
        next_state.log_player = player.name
        next_state.log_action = action

        # apply specified play
        if action == 'SHUFFLE':
            # shuffle the talon
            talon.shuffle()
            next_state.log_player = next_state.players[next_state.dealer].name
        elif action == 'BURN':
            # calculate the number of burnt cards for this number of players
            n_burnt = Game.calc_burnt_cards(len(players))
            for _ in range(n_burnt):
                # move cards from talon to burnt card pile.
                burnt.add_card(talon.pop_card())
            next_state.log_player = next_state.players[next_state.dealer].name
        elif action == 'DEAL':
            # deal 3 face up, 3 face down, and 3 hand cards to each player
            Game.deal(players, dealer, talon)
            next_state.log_player = next_state.players[next_state.dealer].name
        elif action == 'GET':
            # remove the card at index from the face up table cards
            card = player.face_up.pop_card(index)
            # and add it to the hand cards
            player.hand.add_card(card)
            player.hand.sort()
            # GET after TAKE with only face up table cards left
            # => remember its rank for possible 3rd or 4th play
            player.get_fup_rank = card.rank
        elif action == 'PUT':
            # remove the card at index from the hand cards
            card = player.hand.pop_card(index)
            # and add it to the face up table cards
            player.face_up.add_card(card)
        elif action == 'SHOW':
            # get shown card and mark it as shown and face up
            card = player.hand.pop_card(index)
            card.seen = True
            card.shown = True
            # put the shown card back into the hand
            player.hand.add_card(card)
            player.hand.sort()
            # add this player to the list of players who have shown the
            # starting card.
            next_state.shown_starting_card.append(state.player)
            cls.end_turn(next_state)

        elif action == 'HAND' or action == 'FUP' or action == 'FDOWN':
            # remove the card at the index from the source
            card = player.play_card(action, index)
            # play it on the discard pile and resolve the card effects.
            cls.discard_card(next_state, action, card)

        elif action == 'OUT':
            # current player is out
            # => end turn and remove him from players list
            cls.end_turn(next_state, fup_table, stats, True)

        elif action == 'TAKE':
            # if the player has no hand cards but still face up table cards,
            # he must get one of his face up table cards on hand as 2nd play.
            if len(player.hand) == 0 and len(player.face_up) > 0:
                player.get_fup = True
                player.get_fup_rank = None
                # Turn is not over yet, player has to pick 1, 2, or 3 face up
                # table cards on the same turn
                next_state.n_played += 1

            # current player takes discard pile
            for _ in range(len(next_state.discard)):
                # get card at top of discard pile
                card = next_state.discard.pop_card()
                # and add it to hand cards of this player
                player.hand.add_card(card)
            player.hand.sort()  # always keep hand sorted
            # if player doesn't have to also take a face up table card,
            # end this player's turn
            if not player.get_fup:
                cls.end_turn(next_state)

        elif action == 'KILL':
            # kill discard pile because of 4 or more cards of same rank at top.
            # move all cards from the discard pile to the removed cards pile.
            for _ in range(len(next_state.discard)):
                card = next_state.discard.pop_card()
                next_state.killed.add_card(card)
            # reset the '8's and 'K's counter
            # because all '8's and 'K' at the top have been removed.
            next_state.eights = 0
            next_state.kings = 0

        elif action == 'REFILL':
            while (len(player.hand) < 3 and len(talon) > 0):
                # get card at top of talon
                card = talon.pop_card()
                # and add it to the hand cards of this player
                player.hand.add_card(card)
            player.hand.sort()  # always keep hand sorted

        elif action == 'END':
            # player ends his turn
            cls.end_turn(next_state, fup_table)

        elif action == 'DEALER':
            # make player at index in player list the dealer
            next_state.dealer = index

        elif action == 'ABORT':
            # too many turns (AI deadlock) => abort game
            next_state.game_phase = ABORTED

        else:
            raise ValueError(f'Unknown action {action}!')

        # if a card has been played log its name
        if card and action in ['GET', 'PUT', 'SHOW', 'HAND', 'FUP', 'FDOWN']:
            next_state.log_card = str(card)
        else:
            next_state.log_card = ''

        # add this play to the play history of the next state
        next_state.history.append(str(play))

        return next_state

    @classmethod
    def reset_result(cls, state):
        '''
        Reset the scores and turn counts of all players to 0.

        If we quit or have to abort the game (AI deadlock), there are no
        winners.

        :param state:       current shithead state
        :type state:        State
        '''
        for player in state.players:
            state.result[player.name] = [0, 0]

    @classmethod
    def get_result(cls, state):
        '''
        Get scores and turn counts for this round of the game.

        The game is over if only one player is left or if the game is aborted
        due to an AI deadlock (too many turns played).
        In the 1st case the score 0 for the shithead has been entered in the
        result. In the 2nd case all scores and turn counts have to be reset to
        0, i.e. we use the result to correct the scores and turn counts in the
        statistics for the players which are already out.

        :param state:       current shithead state
        :type state:        State
        :return:            current scores of players.
        :rtype:             dict
        '''
        return state.result

    @classmethod
    def loser(cls, state):
        '''
        Return loser (Shithead) of the game.

        This is used for end game evaluation using MCTS.
        Checks if only one player is left and returns his name.

        :param state:       current shithead state
        :type state:        State
        :return:            Name of Shithead or None (game not finished yet)
        :rtype:             str
        '''
        if len(state.players) == 1:
            return state.players[0].name
        else:
            return None


def initial_tests():
    """
    Initial tests for module game.py.
    """
    # I'm doing this here to avoid the circular import error
    # these imports are only used for testing in '__main__'.
    from .player import CheapShit
    from .cards import Deck
    print('\nTest creating a new game:')
    players = []
    players.append(CheapShit('Player1', None, False))
    players.append(CheapShit('Player2', None, False))
    dealer = 0
    log_level = 'No Secrets'
    log_to_file = False
    log_file = ''
    log_info = (log_level, log_to_file, log_file)
    state = State(players, dealer, 1, log_info)
    state.print()

    print('\nTest check if 1st card can be played on empty discard pile:')
    discard = Discard()  # empty discard pile
    print(discard.check(True, Card(0, 'Clubs', '4')))
    print(discard.check(True, Card(0, 'Spades', 'A')))

    print("\nTest check if 1st card can be played on '2':")
    discard.add_card(Card(0, 'Clubs', '2'))
    print(discard.check(True, Card(0, 'Clubs', '5')))
    print(discard.check(True, Card(0, 'Hearts', 'K')))

    print("\nTest check if 1st card can be played on '4':")
    discard.add_card(Card(0, 'Clubs', '4'))
    print(discard.check(True, Card(0, 'Diamonds', '4')))
    print(discard.check(True, Card(0, 'Diamonds', '5')))
    print(discard.check(True, Card(0, 'Spades', '9')))

    print("\nTest check if 1st card can be played on '5':")
    discard.add_card(Card(0, 'Clubs', '5'))
    print(discard.check(True, Card(0, 'Diamonds', '4')))
    print(discard.check(True, Card(0, 'Diamonds', '5')))
    print(discard.check(True, Card(0, 'Spades', '7')))

    print("\nTest check if 1st card can be played on '6':")
    discard.add_card(Card(0, 'Clubs', '6'))
    print(discard.check(True, Card(0, 'Diamonds', '5')))
    print(discard.check(True, Card(0, 'Diamonds', '7')))
    print(discard.check(True, Card(0, 'Spades', 'A')))

    print("\nTest check if 1st card can be played on '7':")
    discard.add_card(Card(0, 'Clubs', '7'))
    print(discard.check(True, Card(0, 'Diamonds', '5')))
    print(discard.check(True, Card(0, 'Diamonds', '8')))
    print(discard.check(True, Card(0, 'Spades', '10')))

    print("\nTest check if 1st card can be played on '8':")
    discard.add_card(Card(0, 'Clubs', '8'))
    print(discard.check(True, Card(0, 'Diamonds', '7')))
    print(discard.check(True, Card(0, 'Diamonds', '9')))
    print(discard.check(True, Card(0, 'Spades', 'Q')))

    print("\nTest check if 1st card can be played on '9':")
    discard.add_card(Card(0, 'Clubs', '8'))
    print(discard.check(True, Card(0, 'Diamonds', '7')))
    print(discard.check(True, Card(0, 'Diamonds', '9')))
    print(discard.check(True, Card(0, 'Spades', 'Q')))

    print("\nTest check if 1st card can be played on 'J':")
    discard.add_card(Card(0, 'Clubs', 'J'))
    print(discard.check(True, Card(0, 'Diamonds', '9')))
    print(discard.check(True, Card(0, 'Hearts', 'Q')))
    print(discard.check(True, Card(0, 'Spades', 'A')))

    print("\nTest check if 1st card can be played on 'Q':")
    discard.add_card(Card(0, 'Clubs', 'Q'))
    print(discard.check(True, Card(0, 'Diamonds', 'J')))
    print(discard.check(True, Card(0, 'Hearts', 'Q')))
    print(discard.check(True, Card(0, 'Spades', 'K')))

    print("\nTest check if 1st card can be played on 'K':")
    discard.add_card(Card(0, 'Clubs', 'K'))
    print(discard.check(True, Card(0, 'Diamonds', 'Q')))
    print(discard.check(True, Card(0, 'Hearts', 'K')))
    print(discard.check(True, Card(0, 'Spades', 'A')))

    print("\nTest check if 1st card can be played on 'A':")
    discard.add_card(Card(0, 'Clubs', 'A'))
    print(discard.check(True, Card(0, 'Diamonds', 'K')))
    print(discard.check(True, Card(0, 'Hearts', '2')))
    print(discard.check(True, Card(0, 'Spades', '3')))
    print(discard.check(True, Card(0, 'Clubs', '10')))
    print(discard.check(True, Card(0, 'Diamonds', 'A')))

    print("\nTest check if 1st card can be played on 'J' below '3':")
    discard.add_card(Card(0, 'Clubs', 'J'))
    discard.add_card(Card(0, 'Diamonds', '3'))
    discard.add_card(Card(0, 'Hearts', '3'))
    print(discard.check(True, Card(0, 'Diamonds', '7')))
    print(discard.check(True, Card(0, 'Hearts', 'J')))
    print(discard.check(True, Card(0, 'Spades', '2')))
    print(discard.check(True, Card(0, 'Clubs', 'K')))
    print(discard.check(True, Card(0, 'Diamonds', 'A')))

    print("\nTest check if 2nd card can be played on 'Q':")
    discard.add_card(Card(0, 'Clubs', 'Q'))
    print(discard.check(False, Card(0, 'Diamonds', '7')))
    print(discard.check(False, Card(0, 'Clubs', '4')))
    print(discard.check(False, Card(0, 'Hearts', 'A')))

    print("\nTest check if 2nd card can be played on 4 'Q's:")
    discard.add_card(Card(0, 'Clubs', 'Q'))
    discard.add_card(Card(0, 'Diamonds', 'Q'))
    discard.add_card(Card(0, 'Hearts', 'Q'))
    discard.add_card(Card(0, 'Spades', 'Q'))
    print(discard.check(False, Card(0, 'Diamonds', '7')))
    print(discard.check(False, Card(0, 'Hearts', 'A')))
    print(discard.check(False, Card(1, 'Spades', 'Q')))

    print("\nTest check if 2nd card can be played on '4':")
    discard.add_card(Card(0, 'Clubs', '4'))
    print(discard.check(False, Card(0, 'Diamonds', '7')))
    print(discard.check(False, Card(0, 'Hearts', 'A')))
    print(discard.check(False, Card(0, 'Diamonds', '4')))

    print("\nTest check if 2nd card can be played on 'K':")
    discard.add_card(Card(0, 'Clubs', 'K'))
    print(discard.check(False, Card(0, 'Hearts', 'A')))
    print(discard.check(False, Card(0, 'Diamonds', 'K')))

    players = []
    players.append(CheapShit('Player1', None, False))
    players.append(CheapShit('Player2', None, False))
    dealer = 0
    log_level = 'No Secrets'
    log_to_file = False
    log_file = ''
    log_info = (log_level, log_to_file, log_file)
    state = State(players, dealer, 1, log_info)
    state.game_phase = PLAY_GAME
    print("\nTest get legal plays (1st card, empty discard pile):")
    players[0].take_card('HAND', Card(0, 'Diamonds', '5'))
    players[0].take_card('HAND', Card(0, 'Hearts', '10'))
    players[0].take_card('HAND', Card(0, 'Hearts', '8'))
    print('Discard: ', end='')
    state.discard.print_top()
    players[0].print(visibility=3)
    plays = players[0].get_legal_plays(state)
    print(' '.join([str(play) for play in plays]))

    print("\nTest get legal plays (1st card, discard pile not empty):")
    state.discard.add_card(Card(0, 'Diamonds', '5'))
    players[0].hand = Deck(empty=True)
    players[0].take_card('HAND', Card(0, 'Clubs', '5'))
    players[0].take_card('HAND', Card(0, 'Hearts', '10'))
    players[0].take_card('HAND', Card(0, 'Spades', '2'))
    print('Discard: ', end='')
    state.discard.print_top()
    players[0].print(visibility=3)
    plays = players[0].get_legal_plays(state)
    print(' '.join([str(play) for play in plays]))

    state.discard.add_card(Card(0, 'Clubs', '7'))
    print('Discard: ', end='')
    state.discard.print_top()
    players[0].print(visibility=3)
    plays = players[0].get_legal_plays(state)
    print(' '.join([str(play) for play in plays]))

    state.discard.add_card(Card(0, 'Clubs', 'K'))
    print('Discard: ', end='')
    state.discard.print_top()
    players[0].print(visibility=3)
    plays = players[0].get_legal_plays(state)
    print(' '.join([str(play) for play in plays]))

    print("\nTest get legal plays (2nd card, refill):")
    state.n_played = 1
    state.discard.add_card(Card(0, 'Diamonds', '5'))
    players[0].hand = Deck(empty=True)
    players[0].take_card('HAND', Card(0, 'Clubs', '5'))
    players[0].take_card('HAND', Card(0, 'Hearts', '10'))
    print('Discard: ', end='')
    state.discard.print_top()
    players[0].print(visibility=3)
    plays = players[0].get_legal_plays(state)
    print(' '.join([str(play) for play in plays]))

    print("\nTest get legal plays (2nd card, kill or play another '5'):")
    state.n_played = 1
    state.discard.add_card(Card(1, 'Clubs', '5'))
    state.discard.add_card(Card(0, 'Hearts', '5'))
    state.discard.add_card(Card(0, 'Spades', '5'))
    print('Discard: ', end='')
    state.discard.print_top()
    players[0].print(visibility=3)
    plays = players[0].get_legal_plays(state)
    print(' '.join([str(play) for play in plays]))

    print("\nTest get legal plays (2nd card, play on 'Q'):")
    state.n_played = 1
    state.discard.add_card(Card(1, 'Clubs', 'Q'))
    players[0].take_card('HAND', Card(0, 'Hearts', '8'))
    print('Discard: ', end='')
    state.discard.print_top()
    players[0].print(visibility=3)
    plays = players[0].get_legal_plays(state)
    print(' '.join([str(play) for play in plays]))

    print("\nTest get legal plays (2nd card, end turn):")
    state.n_played = 1
    state.discard.add_card(Card(1, 'Hearts', '5'))
    print('Discard: ', end='')
    state.discard.print_top()
    players[0].print(visibility=3)
    plays = players[0].get_legal_plays(state)
    print(' '.join([str(play) for play in plays]))


if __name__ == '__main__':
    # !!!NOTE!!!
    # Trying to call this with
    #     $ python game.py
    # results in an ImportError because I used relative imports for the local
    # modules (pyinstaller is to blame for that).
    # Therefore we have to go one directory up and call it with
    #     $ python -m shithead.game
    initial_tests()
