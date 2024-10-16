"""
Monte Carlo Tree Search (MCTS).

Used by AI players for the the end game, i.e. when the stack is empty and
only 2 players are left in the game.

31.05.2024 Wolfgang Trachsler
"""

import time
import json
from random import randrange
from collections import defaultdict
from time import sleep

from .game import Game
from .state import State
from .play import Play
from .monte_carlo_node import MonteCarloNode
from .fup_table import FupTable, FUP_TABLE_FILE
from . import player as plr     # to avoid confusion with variable 'player'

MAX_SIMULATION_TURNS = 1000


class MonteCarlo:
    """
    Class representing the Monte Carlo search tree.
    """
    def __init__(self, game, ucb1_explore_param=2):
        '''
        Constructor.

        :param game: Shithead game (=> game rules).
        :type game: Game
        :param ucb1_explore_param: Explore parameter used for Upper Confidence
                                 Bound 1.
        :type ucb1_explore_param: float
        '''
        self.game = game
        self.ucb1_explore_param = ucb1_explore_param
        # dictionary mapping State.hash() to MonteCarloNode
        # => a node is unambiguously identified by the play history leading up
        #    to its state.
        self.nodes = {}

        self.simulation_turns = 0       # total number of simulated turns
        self.simulations = 0            # total number of simulations
        self.aborts = 0                 # total number of aborted simulations
        # maximum number of consecutive search loops without expansion
        self.max_no_exp_loops = 0
        self.single_children = 0        # single child nodes

    def make_node(self, state):
        '''
        Create dangling node.

        If the specified state does not exist (i.e. there's no key
        corresponding to its play history in the nodes dictionary yet),
        We create a new root node (no parent) and add it to nodes.
        !!!Note!!!
        Each state uses its whole play history as hash key, i.e. that usually
        only the very 1st node is a dangling node. If run_search() is called
        again at a later time, there should already be a node with this hash
        in the existing tree and run_search() just adds more nodes to this tree
        below the specified node.

        :param state:   Shithead game state.
        :type state:    State
        '''
        if state.hash() not in self.nodes:
            # get the current player in this state
            player = state.players[state.player]
            # get list of legal plays for this player in this state
            unexpanded_plays = player.get_legal_plays(state)
            # create a new node for this state (no parent, no play)
            # and add it to the nodes list
            self.nodes[state.hash()] = MonteCarloNode(None, None, state,
                                                      unexpanded_plays)
            # all nodes created after the root node immediatly get n_plays = 1.
            # to avoid inconsistencies in the node statistics we set the root
            # node to n_plays=1.
            self.nodes[state.hash()].n_plays = 1

    def select(self, state, verbose=False):
        '''
        Phase 1: Selection.

        Find not fully expanded node or leaf (no more legal plays).
        In Shithead there are no leafs, i.e. there's always a legal play until
        one of the players has lost the game (Shithead = last player with
        cards).

        :param state: Shithead game state.
        :type state: State.
        :param verbose:     True => print details of found node.
        :type verbose:      bool
        '''
        # get the node belonging to this state (play history)
        node = self.nodes[state.hash()]
        # search through tree to find a not fully expanded or leaf node.
        while node.is_fully_expanded() and not node.is_leaf():
            # go to child node which yields the best UCB1
            best_play = None             # initialize best play
            best_ucb1 = float('-inf')    # init best upper confidence bound 1
            plays = node.all_plays()     # all legal plays from this node
            for play in plays:
                # calculate UCB1 for all children of current node
                child_ucb1 = node.child_node(play).get_ucb1(
                    self.ucb1_explore_param)
                if child_ucb1 > best_ucb1:
                    best_play = play
                    best_ucb1 = child_ucb1
            # select the child with the best UCB1 as next node
            node = node.child_node(best_play)
            if verbose:
                node.print()
        return node

    def expand(self, node, verbose=False):
        '''
        Phase 2: Expansion.

        Expand a random unexpanded child node.
        Select randomly an unexpanded play of this node.
        Use this play to generate the game state of the child.
        Get a list of legal plays from the child's game state.
        Create the child node from this node (parent), play (leads from parent
        to child), child state, and legal plays for child state.
        Add the child node to the children list of this node (=> add child to
        tree).
        :param node:        node with unexpanded plays
        :type node:         MonteCarloNode
        :param verbose:     True => print hash of parent node + expanded play
        :type verbose:      bool
        :return:            new child of this node.
        :rtype:             MonteCarloNode
        '''
        # get a list of unexpanded plays for this node
        plays = node.unexpanded_plays()
        # select one play randomly from this list
        play = plays[randrange(len(plays))]
        if verbose:
            print(f'\n### expand: {node.state.hash()}+{str(play)}')
        # make a copy of this nodes state
        child_state = node.state.copy()
        # apply selected play to change into the state of the child node
        child_state = self.game.next_state(child_state, play)
        # get the current player in child's state
        player = child_state.players[child_state.player]
        # get list of legal plays for this player in child's state
        child_unexpanded_plays = player.get_legal_plays(child_state)
        # create the child node
        child_node = node.expand(play, child_state, child_unexpanded_plays)
        if verbose:
            child_node.print()

        # add the new child node to the list of MTCS nodes
        self.nodes[child_state.hash()] = child_node
        # return the new child node
        return child_node

    def simulate(self, node, verbose=False):
        '''
        Phase 3: Simulation

        The specified node is a new child node created during expansion.
        We use the state of this node as starting point of our simulation,
        looping though the following steps:
            - get list of legal plays for the current state.
            - randomly select one of these plays.
            - apply selected play to the current state to get the next state.
            - check if the next state has winner or a tie.

        :param node:    starting node for simulation
        :type node:     MonteCarloNode
        :param verbose: True => print each play/state.
        :type verbose:  bool
        :return:        name of shithead or None(turn count overflow)
                        and the number of simulated turns.
        :rtype:         tuple
        '''
        turns = 0   # turn counter
        # make a copy of the state of node, where we start the simulation
        # (= node from expansion)
        state = node.state.copy()
        # get loser of this state (i.e. it's possible that there's no need for
        # additional simulation)
        loser = self.game.loser(state)

        # loop till we have found a loser (Shithead)
        while loser is None and turns < MAX_SIMULATION_TURNS:
            turns += 1
            # get the current player in this state
            player = state.players[state.player]
            # get list of legal plays for this player in this state
            plays = player.get_legal_plays(state)
            # randomly select a play from this list
            play = plays[randrange(len(plays))]
            if verbose:
                print(f'\nPlay: {str(play)}')
            # apply the selected play to the current state to get the next
            # state
            state = self.game.next_state(state, play)
            if verbose:
                state.print()
            # check if we have found the Shithead
            loser = self.game.loser(state)

        # return the name of the shithead
        return (loser, turns)

    def backpropagate(self, node, loser, top, verbose=False):
        '''
        Phase 4: Backpropagation.

        Update the ancestor statistics.
        Follow the search path back to the top node (the node where the current
        player evaluates his next play, i.e. the node from where the search
        tree is expanded).
        Increment the number of plays in each of these nodes.
        The number of wins is only incremented in nodes which have a parent
        node with the winning player as current player, since each node uses
        the play/win counters in its children to decide what's the best play.
        E.g. If we are in a Tree-Node where Player1 is the current player, we
        use the plays/wins counters in its children's nodes (where maybe
        Player2 is the current player, note that in Shithead players are not
        strictly alternating as in connect-4) to calculate the UCB1 to select
        the next node in the selection phase. Thus, if Player1 wins a simulated
        game, we have to increment the number of wins in the nodes where
        Player1 is the current player in the parent nodes.
        The top node is not updated, since its statistic counters are no longer
        used for UCB1 calculation or decision making.
        If loser is None (i.e. the simulation was aborted because the maximum
        number of turns was exceeded), we only increment the number of plays.

        :param node:        node where we ran the simulation.
        :type node:         MonteCarloNode
        :param loser:       Name of Shithead found in the simulation.
        :type loser:        str
        :param top:         top node, where the current player has to decide.
        :type top:          MonteCarloNode
        :param verbose:     True => print updated nodes
        :type verbose:      bool
        '''
        while node is not top.parent:
            # increment number of plays in every visited node.
            node.n_plays += 1
            # the statistics in the parent nodes is responsible for selecting
            # the node, where the winning player is the current player.
            if (loser is not None
                    and node.parent_player is not None
                    and node.parent_player != loser):
                # increment the number of wins in all nodes with the winner as
                # current player of the parent node, because the parent node,
                # where the winner is the current player uses this counter to
                # select the path through the tree.
                node.n_wins += 1
            if verbose:
                # print node with updated stats
                # parent-plays + 1 for UCB1 calculation,
                # since child is updated before parent.
                node.print(True)

            # move up to the parent node.
            node = node.parent

    def run_search(self, state, timeout=3, verbose=False):
        '''
        From given state, repeatedly run MCTS to build statistics.

        Use the specified state to create the root node of a new search tree.
        During the specified interval, build the search tree by looping through
        the following 4 phases:
            - selection:
              move down the tree selecting at each node the child node with the
              best UCB1 value, until we have reached a not fully expanded node,
              or a leaf (no more legal plays, this is not possible in
              Shithead).
            - expansion:
              add a new child to a found node with unexpanded plays.
            - simulation:
              from the state of the new child randomly select legal plays until
              a loser has been found or a leaf has been reached
              (not in Shithead).
            - backpropagation
              Update the statistics of all nodes in the path from the root to
              the found node with the found loser (either loser in a leaf
              (n.a.) or loser found through expansion/simulation).

        :param state:       starting state for tree search.
        :type state:        State
        :param timeout:     time interval [s] spent building the search tree.
        :type timeout:      float
        :param verbose:     True => print details during search.
        :type verbose:      bool
        '''
        # If this is the the 1st call of run_search() we create the root node
        # of the search tree for the initial state.
        # Later calls will use the hash (play history) of the state to find the
        # corresponding node in the existing tree and expand the existing tree
        # below the found node.
        self.make_node(state)

        # get the start node of the search
        start_node = self.nodes[state.hash()]

        # if there's only one legal play in the start state, there's no need to
        #  run a search, since the only play is always the best play.
        if len(start_node.children) == 1:
            if not start_node.is_fully_expanded():
                # create the only child of the start node and add it to the
                # tree, but skip simulate() and backpropagate()
                node = self.expand(start_node, verbose)
                # increment n_plays in child and parent
                node.n_plays += 1
                start_node.n_plays += 1
                self.single_children += 1
                self.simulations += 1  # just to avoid division by zero
            return

        # counter for consecutive loops without expansion
        # it should grow larger, if the tree nears completion,
        # i.e. it gets harder to find an unexpanded play.
        no_exp_loops = 0

        # get the start time
        start = time.time()
        # loop until timeout has expired
        # and each play from start node has been expanded.
        while (time.time() < start + timeout
               or not start_node.is_fully_expanded()):
            # find node which is not fully expanded moving along a path
            # following the child nodes with the best UCB1 value.
            selected = self.select(state)
            # check if this node has only one unexpanded play
            # and no children yet # e.g. ('END', -1) to end a turn
            # or ('TaKE', -1) if nothing else is # possible.
            if verbose:
                print(f'\n### Select: {selected.state.hash()}  ###')
                selected.print()
            # check if found node already has a loser
            loser = self.game.loser(selected.state)
            if not selected.is_leaf() and loser is None:
                # not a leaf and no loser found yet
                # => add one new child node using an unexpanded play  of this
                #    node.
                node = self.expand(selected, verbose)
                if len(selected.children) == 1:
                    # only 1 play from parent node => no need to simulate
                    # we just copy n_plays and n_wins from the parent.
                    node.n_plays = selected.n_plays
                    node.n_wins = selected.n_wins
                    self.single_children += 1
                else:
                    # from this new node randomly select plays until a loser
                    # has been found or no legal plays are left.
                    loser, turns = self.simulate(node)
                    if loser is not None:
                        self.simulation_turns += turns
                        self.simulations += 1
                        if verbose:
                            print(f"\n### Shithead: {loser} after {turns}"
                                  " turns")
                    else:
                        self.aborts += 1
                        if verbose:
                            print("\n### No Shithead found, simulation aborted"
                                  f" after {turns} turns!")
                    # backpropagate the loser found by the simulation.
                    # => update n_plays and n_wins in all nodes on the path to
                    #    the new node.
                    self.backpropagate(node, loser, start_node, False)
                # reset 'no expansion loops' counter
                no_exp_loops = 0
            else:
                # Shithead already found => no expansion/simulation
                no_exp_loops += 1   # increment counter
                if no_exp_loops > self.max_no_exp_loops:
                    self.max_no_exp_loops = no_exp_loops
                if verbose:
                    print(f'\n### no expansion: {selected.state.hash()}')
                    selected.print()
                    print(f"\n### Shithead: {loser}"
                          f" no_exp_loops: {no_exp_loops} ")
                # backpropagate the loser of the selected node
                self.backpropagate(selected, loser, start_node, False)

    def best_play(self, state, policy='robust'):
        '''
        Get the best play from available statistics.

        Get a list of all possible plays from this node.
        Loop through this list to find either the most visited child (robust
        child) or the child with the best win/play ratio (max child).
        Return the play which leads to the found child.

        :param state:   game state for which we search the best play.
        :type state:    State_C4
        :param policy:  'robust' => find robust child, 'max' => find max child.
        :type policy:   str
        :return:        best play for this state according to policy.
        :rtype:         Play
        '''
        # create the root node of the search tree for this state
        # but only if there's not already an entry in dictionary self.nodes for
        # this state's play history.
        # if a new root node is generated we will get an error next then
        # checking if it's fully expanded!
        self.make_node(state)

        # check if all possible plays for the root node identified by this
        # state's play history have been expanded.
        if not self.nodes[state.hash()].is_fully_expanded():
            raise ValueError('Not enough information!')

        # get the root node identified by this state's play history.
        node = self.nodes[state.hash()]
        # initialize best play
        best_play = None
        # get a list of all possible plays from this node.
        all_plays = node.all_plays()

        # find the child with the most visits (robust child)
        if policy == 'robust':
            vmax = float('-inf')   # initialize max value
            for play in all_plays:
                child_node = node.child_node(play)
                if child_node.n_plays > vmax:
                    best_play = play
                    vmax = child_node.n_plays

        # find the child with the highest win rate (max child)
        if policy == 'max':
            vmax = float('-inf')   # initialize max value
            for play in all_plays:
                child_node = node.child_node(play)
                ratio = child_node.n_wins / child_node.n_plays
                if ratio > vmax:
                    best_play = play
                    vmax = ratio

        return best_play

    def get_stats(self, state):
        '''
        Return MCTS statistics this state.

        Returns the number of plays and the number of wins for the node
        identified by the play history of this state and a list with the number
        of plays and wins for each of its children, plus the total over all
        children.

        :param state: game state identifying node for which we want the stats.
        :type state: State
        :return: stats for node and its children.
        :rtype: dict.
        '''
        node = self.nodes[state.hash()]
        stats = {'n_plays': node.n_plays,
                 'n_wins': node.n_wins,
                 'children': [],
                 'total': {'n_plays': 0, 'n_wins': 0}}
        for child in node.children.values():
            if child['node'] is None:
                stats['children'].append({'play': child['play'],
                                          'n_plays': None,
                                          'n_wins': None})
            else:
                stats['children'].append({'play': child['play'],
                                          'n_plays': child['node'].n_plays,
                                          'n_wins': child['node'].n_wins})
                # sum up plays and wins of children
                stats['total']['n_plays'] += child['node'].n_plays
                stats['total']['n_wins'] += child['node'].n_wins
        return stats

    def check_stats(self, state):
        '''
        Check MCTS statistics for selected node.

        Gets the n_plays and n_wins counts for the node with the selected game
        state and all its child nodes.
        !!! IMPORTENT !!!
        Since each node below the root node immediately gets 1 play after
        creation the number of plays in the selected node must be the sum of
        plays in its children +1. In order to make this also valid for the root
        node, we initialize the root node with n_plays=1.
        The number of wins in the selected node are belonging to the current
        player in the parent node (who selected the play leading to this node),
        while the wins in its children are belonging to the current player in
        the selected node itself. I.e. if the same player was current player in
        selected and parent node (always in case of the root node), the wins in
        the children will sum up to the number of wins in the selected node
        (+1 if the current player won the simulation when this node was
        created), or otherwise could be completely different.

        :param state:   game state specifying the selected node.
        :type state:    State.
        '''
        # get the statistics for the node of the specified game state
        stats = self.get_stats(state)

        # check statistics if selected node has >1 children
        if len(stats['children']) > 1:
            current_player = state.players[state.player].name
            node = self.nodes[state.hash()]
            # check total number of plays
            if stats['n_plays'] != stats['total']['n_plays'] + 1:
                print(f"### Warning: selected node visits: {stats['n_plays']}",
                      f"don't match total visits: {stats['total']['n_plays']}",
                      " + 1!")
            # check total number of wins (only if selected and parent
            # have same current player)
            if node.parent_player == current_player:
                # same current player in selected and parent node
                if (stats['n_wins'] != stats['total']['n_wins']
                        and stats['n_wins'] != stats['total']['n_wins'] + 1):
                    print(
                        f"### Warning: selected node wins: {stats['n_wins']}",
                        f" don't match total wins: {stats['total']['n_wins']}",
                        " (+1)!")

    def print_stats(self, state):
        '''
        Print MCTS statistics for selected node.

        Prints number of plays, number of wins, and wins to plays ratio for
        each of the children of the node specified by this state, as well as
        the total number of plays and wins over all children.

        :param state:   game state specifying the selected node.
        :type state:    State.
        '''
        stats = self.get_stats(state)
        for entry in stats['children']:
            if entry['n_plays']:
                # n_plays not None => play has been expanded
                # and n_plays > 0  => ratio without division by zero
                print(f"play:{str(entry['play']):>8} ",
                      f"visits:{entry['n_plays']:>6} ",
                      f"wins:{entry['n_wins']:>6} ",
                      f"ratio: {entry['n_wins'] / entry['n_plays']:.2f}")
        print(f"total:         visits:{stats['total']['n_plays']:>6} ",
              f"wins:{stats['total']['n_wins']:>6}")


def restore_end_game_state(filename, verbose=False, first='ShitHappens',
                           second='ShitHappens', timeout=1.0, policy='max'):
    """
    Restores end game state from json-file.

    Loads state info from the provided json-file.
    Checks if it's an end game state (2 players, empty talon).
    Creates list of 2 players and uses it to create the initial game state.
    Uses the loaded end game state info to transform this state into the end
    game state.

    :param filename:    name of json-file containing end game state.
    :type filename:     str
    :param verbose:     True => print loaded json-string
    :type verbose:      bool
    :param first:       AI type of 1st player in player list.
    :type first:        str
    :param second:      AI type of 2nd player in player list.
    :type second:       str
    :param timeout:     timeout of tree search [s].
    :type timeout:      float
    :param policy:      MCTS best play policy ('robust', 'max').
    :type policy:       str
    :return:            end game state.
    :rtype:             State
    """
    state_file = filename

    # map name of AI to class
    ai_map = {'ShitHappens': plr.ShitHappens,
              'CheapShit': plr.CheapShit,
              'TakeShit': plr.TakeShit,
              'BullShit': plr.BullShit,
              'DeepShit': plr.DeepShit,
              'DeeperShit': plr.DeeperShit}

    try:
        # load end game state from json-file
        with open(state_file, 'r') as json_file:
            state_info = json.load(json_file)
    except OSError as exception:
        print(f"### Error: couldn't load file {state_file}")
        return

    # print the loaded game state
    if verbose:
        print(f'\n### End game state info loaded from {filename}')
        state_info_str = json.dumps(state_info, indent=4)
        print(state_info_str)

    # create face up table (needed in player createion)
    fup_table = FupTable()

    # load face up table from file (in package)
    fup_table.load(FUP_TABLE_FILE, True)

    # get number of remaining players from loaded state
    n_players = len(state_info['players'])

    # make sure the loaded state is an end game state
    # => only 2 players left
    # => empty talon
    if n_players != 2 or len(state_info['talon']) != 0:
        raise Exception("This is not an end game state!")

    # create list of remaining player
    # Note, that the AI type is not in the status (but in the config).
    # We use DeeperShit although this is not relevant for most of the tests.
    players = []
    if first == 'DeeperShit':
        players.append(
            ai_map[first]('', fup_table, True, timeout, policy, verbose))
    else:
        players.append(ai_map[first]('', fup_table))
    if second == 'DeeperShit':
        players.append(
            ai_map[second]('', fup_table, True, timeout, policy, verbose))
    else:
        players.append(ai_map[second]('', fup_table))

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


def run_first_step(filename):
    '''
    run a single step of the MCTS run_search() method.

    Creates end game state loaded from specified json-file.
    Creates an empty MCTS-object for the shithead game.
    Creates a root node for the loaded end game state.
    Selects an unexpanded play of the root node.
    Expands the corresponding child node for the selected play.
    Simulates the outcome of the remaining game after the selected play.
    Backpropagates the result to the expanded node.

    :param filename:    name of json-file containing end game state.
    :type filename:     str
    '''
    # restore the end game state from json-file
    state = restore_end_game_state(filename, True)

    # print state overview
    print(f'\n### End game state loaded from {filename}')
    state.print()

    legal_plays = state.players[state.player].get_legal_plays(state)
    print('\n### Legal plays from this state:')
    for play in legal_plays:
        print(f'\t{str(play)}')

    # create the shithead game.
    # this is actually not necessary since all its methods are class methods.
    # But the MonteCarlo class expets a Game object as input parameter.
    game = Game()

    # create the MonteCarlo object
    mcts = MonteCarlo(game)

    # create the root node in the MonteCarlo tree from this end game state.
    print('\n### Root node ###')
    mcts.make_node(state)
    mcts.nodes[''].print()

    # get the start node of the search (= root node)
    start_node = mcts.nodes[state.hash()]

    # select the next node to expand
    # since the root node still has unexpanded plays, it's the root node
    print('\n### select ###')
    node = mcts.select(state, True)

    # expand this node by randomly selecting one of the unexpanded plays and
    # create the corresponding child.
    node = mcts.expand(node, True)

    # simulate the outcome of the game by making random plays
    loser, turns = mcts.simulate(node, True)
    print(f'### Shithead: {loser} after {turns} turns')

    # backpropagate the simulation result
    print(f'\n### Backpropagate simulation result: Shithead={loser}')
    mcts.backpropagate(node, loser, start_node, True)


def test_mcts(filename, timeout=3.0):
    '''
    Find best play for loaded end game state.

    Creates end game state loaded from specified json-file.
    Creates an empty MCTS-object for the shithead game.
    Executes run_search() method several times to build the search tree.
    Use the search tree to find the best play in this state.

    :param filename:    name of json-file containing end game state.
    :type filename:     str
    :param timeout:     timeout for run_search().
    :type timeout:      float
    '''

    # restore the end game state from json-file
    state = restore_end_game_state(filename, True)

    # print state overview
    print(f'\n### End game state loaded from {filename}')
    state.print()

    # list the legal plays available in this state
    legal_plays = state.players[state.player].get_legal_plays(state)
    print('\n### Legal plays from this state:')
    for play in legal_plays:
        print(f'\t{str(play)}')

    # create the shithead game.
    # this is actually not necessary since all its methods are class methods.
    # But the MonteCarlo class expets a Game object as input parameter.
    game = Game()

    # create the MonteCarlo object
    mcts = MonteCarlo(game)

    # build the search tree with this state as root
    mcts.run_search(state, timeout, verbose=True)
    best_robust = mcts.best_play(state, 'robust')
    best_max = mcts.best_play(state, 'max')

    # print state overview
    print(f'\n### End game state loaded from {filename}')
    state.print()

    # list the legal plays available in this state
    legal_plays = state.players[state.player].get_legal_plays(state)
    print('\n### Legal plays from this state:')
    for play in legal_plays:
        print(f'\t{str(play)}')

    # print statistics
    print('\n### Statistics:')
    print(f'Nodes: {len(mcts.nodes)}')
    print(f'Single children: {mcts.single_children}')
    print(f'Finished simulations: {mcts.simulations}')
    print(f'Aborted simulations: {mcts.aborts}')
    if mcts.simulations > 0:
        print("Turns/Simulation:"
              f" {mcts.simulation_turns / mcts.simulations:.1f}")
    print(f'Maximum no-expansion loops: {mcts.max_no_exp_loops}')
    mcts.check_stats(state)
    mcts.print_stats(state)
    print(f'\nBest robust play:  {str(best_robust)}')
    print(f'Best maximum play: {str(best_max)}')


def play_end_game_with_open_cards(filename, timeout=3.0, policy='robust'):
    '''
    Play end game using MCTS with open cards.

    Creates end game state loaded from specified json-file.
    Uses MCTS to select best plays for both players.
    Executes these plays until shithead is found.
    Note, that to simplify things all cards of both players are known
    (i.e. also the face down table cards). This allows us to use a single
    search tree for the whole end game.
    We start with the root node (dangling node with no parent).
    From there each following game state should already have a node in the
    search tree identified by the play history. Therefore, the search tree
    grows with every turn unless, the selected node cannont be expanded,
    because in its state the shithread has already been found.

    :param filename:    name of json-file containing end game state.
    :type filename:     str
    :param timeout:     timeout for run_search().
    :type timeout:      float
    :param policy:      'robust' => find robust child, 'max' => find max child.
    :type policy:       str
    '''

    # restore the end game state from json-file
    state = restore_end_game_state(filename, False)

    # print state overview
    print(f'\n### End game state loaded from {filename}')
    state.print()

    # create the shithead game.
    # this is actually not necessary since all its methods are class methods.
    # But the MonteCarlo class expets a Game object as input parameter.
    game = Game()

    # create the MonteCarlo object
    mcts = MonteCarlo(game)

    while len(state.players) > 1:
        # build the search tree with this state as root
        mcts.run_search(state, timeout)

        # check statistics
        mcts.check_stats(state)
        # print statistics
        mcts.print_stats(state)

        # select best play according to specified policy
        best_play = mcts.best_play(state, policy)

        # apply best_play to state
        state = mcts.game.next_state(state, best_play)

        # print new state
        state.print()


def get_number_of_unknown_cards(state):
    '''
    Get number of cards unknown to the current player.

    Get the list of unknown cards from this state.
    From the number of cards in this list subtract the number of cards in the
    hand of the current player, which have never been face up during the game.

    :param state:   game state.
    :type state:    State
    :return:        number of cards unknown to current player
    :rtype:         int
    '''

    unknown_overall = state.get_unknown_cards()   # get all unknown cards
    current = state.players[state.player]
    # get all unknown cards in current  player's hand
    unknown_in_hand = [card for card in current.hand if not card.seen]

    return len(unknown_overall) - len(unknown_in_hand)


def play_end_game(filename, timeout=3.0, policy='robust'):
    '''
    Play end game using MCTS.

    Creates end game state loaded from specified json-file.
    Uses MCTS to select best plays for both players.
    Executes these plays until shithead is found.
    In a normal game of shithead even a player with perfect memory only knows
    his own hand and face up table cards and every card which was once face up
    (e.g. in the discard pile).
    I.e. each player has to build his own search tree using propability based
    assumptions for all cards unknown to him. As soon as one of the unknown
    cards is uncovered we have to start a new search tree. To keep things
    simple, we will do this even if the uncovered card matches our assumption.

    :param filename:    name of json-file containing end game state.
    :type filename:     str
    :param timeout:     timeout for run_search().
    :type timeout:      float
    :param policy:      'robust' => find robust child, 'max' => find max child.
    :type policy:       str
    '''

    # create the shithead game.
    # this is actually not necessary since all its methods are class methods.
    # But the MonteCarlo class expets a Game object as input parameter.
    game = Game()

    # restore the end game state from json-file
    state = restore_end_game_state(filename, False)

    # print state overview
    print(f'\n### End game state loaded from {filename}')
    state.print()

    # Create a dictionary with assumed state and search tree per player.
    assumed = defaultdict(dict)
    for player in state.players:
        plr = player.name
        assumed[plr]['state'] = state.simulation_state(state, plr)
        assumed[plr]['mcts'] = MonteCarlo(game)

    # loop until the shithead has been found
    while len(state.players) > 1:
        print('\n================================'
              '==============================================\n')

        # store the number of unknown cards
        nof_unknown = len(state.get_unknown_cards())

        # get the current player's name
        current = state.players[state.player].name

        print(f"### {current}: assumed state")
        assumed[current]['state'].print()

        # get the other player's name
        for player in state.players:
            if player.name != current:
                other = player.name

        # use the search tree to find the best play for the current player
        sim_state = assumed[current]['state']
        mcts = assumed[current]['mcts']

        # expand the search tree
        mcts.run_search(sim_state, timeout)

        # check statistics
        mcts.check_stats(sim_state)
        # print statistics
        mcts.print_stats(sim_state)

        # select best play according to specified policy
        best_play = mcts.best_play(sim_state, policy)
        print(f"\n### {current}: {str(best_play)}")
        if best_play.action == 'HAND':
            # get card to be played from hand
            # we may need it to update the assumed state of the other player.
            card = sim_state.players[sim_state.player].hand[best_play.index]

        # apply best_play to the !!!ACTUAL!!! game state
        state = game.next_state(state, best_play)
        print('### new real game state')
        state.print()

        # check if number of unknown cards has changed
        if len(state.get_unknown_cards()) < nof_unknown:
            # a previously unknown card has been uncovered
            # => make new assumptions, start new search tree
            print(f"### Number of unknown cards: before: {nof_unknown} now:"
                  f" {len(state.get_unknown_cards())}")
            for player in state.players:
                plr = player.name
                assumed[plr]['state'] = state.simulation_state(state, plr)
                assumed[plr]['mcts'] = MonteCarlo(game)
        else:
            # no new info => continue with the assumed states
            # apply best_play to assumed state of current player
            sim_state = game.next_state(sim_state, best_play)
            assumed[current]['state'] = sim_state
            print(f'### assumed state of {current}')
            sim_state.print()

            # apply best play to opponent player's assumed state.
            # !!!Note!!!
            # If the current player has played a hand card, this card could be
            # at a different index due to changed sorting because of assumed
            # unknown cards.
            sim_state = assumed[other]['state']
            if best_play.action == 'HAND':
                print(f"### {current}: played {str(card)} from hand")
                # find the played card  in the other assumed state.
                idx = sim_state.players[sim_state.player].hand.find(card)
                if idx < 0:
                    # something went wrong, this should be a known card
                    # and therefore also in be found in this assumed state
                    raise Exception("Known hand card not found in"
                                    " opponent's state!")
                else:
                    # create best_play as 'HAND' play with found index
                    best_play = Play('HAND', idx)
            # apply best_play to other assumed state
            print(f"### {current}: {str(best_play)}")
            sim_state = game.next_state(sim_state, best_play)
            assumed[other]['state'] = sim_state
            print(f'### assumed state of {other}')
            sim_state.print()


def deeper_shit_test(filename, opponent='DeepShit', timeout=1.0, policy='max'):
    '''
    Play end game using DeeperShit player.

    :param filename:    name of json-file containing end game state.
    :type filename:     str
    :param opponent:    AI type of DeeperShit's opponent.
    :type opponent:     str
    :param timeout:     timeout of tree search [s].
    :type timeout:      float
    :param policy:      MCTS best play policy ('robust', 'max').
    :type policy:       str
    '''
    # restore the end game state from json-file
    state = restore_end_game_state(filename, True, 'DeeperShit', opponent,
                                   timeout, policy)

    # print state overview
    print(f'\n### End game state loaded from {filename}')
    state.print()

    # loop until the shithead has been found
    while len(state.players) > 1:
        print('\n=================================='
              '============================================\n')
        # let the current player play one action
        player = state.players[state.player]
        while (True):
            play = player.play(state)
            if play is not None:
                break
            # player not ready => wait 100 ms
            sleep(0.1)

        # apply this  action to the current state to get to the next state
        state = Game.next_state(state, play, None, None)
        state.print()


def deeper_shit_performance_test(filename, opponent='DeepShit', timeout=1.0,
                                 policy='max', n_games=10):
    '''
    Check win ratio of DeeperShit player.

    Restore the specified end game state and finish the game n_games times with
    DeeperShit as 1st player and also as 2nd player against the specified
    opponent AI.
    Calculate the win ratio of DeeperShit against this opponent.

    :param filename:    name of json-file containing end game state.
    :type filename:     str
    :param opponent:    AI type of DeeperShit's opponent.
    :type opponent:     str
    :param timeout:     timeout of tree search [s].
    :type timeout:      float
    :param policy:      MCTS best play policy ('robust', 'max').
    :type policy:       str
    :param n_games:     number of games played (2x).
    :type n_games:      int
    '''
    n_wins = 0      # number of games won by DeeperShit
    ratio = 0
    n_aborted = 0   # number of aborted games
    name = ''       # name of player using DeeperShit

    # finish this game 2x for the specified number of times
    for i in range(2 * n_games):
        # calculate win ratio [%]
        if i > 0:
            ratio = int(n_wins / (i - n_aborted) * 100)

        if i % 2 > 0:
            # odd games =>  2nd player uses DeeperShit AI
            state = restore_end_game_state(filename, False, opponent,
                                           'DeeperShit', timeout, policy)
            name = state.players[1].name    # name of DeeperShit player
        else:
            # even games => 1st player uses DeeperShit AI
            state = restore_end_game_state(filename, False, 'DeeperShit',
                                           opponent, timeout, policy)
            name = state.players[0].name    # name of DeeperShit player
            if i == 0:
                # very 1st game => print end game state overview
                print(f'\n### End game state loaded from {filename}')
                state.print()

        # play until Shithead has been found
        while len(state.players) > 1:
            # update statistics line
            print(f"Turn:{state.turn_count:>3} Games:{i:>3}"
                  f" Aborted:{n_aborted:>3} Wins:{n_wins:>3}"
                  f" ({ratio}%)", end='\r')
            # let the current player play one action
            player = state.players[state.player]
            while (True):
                play = player.play(state)
                if play is not None:
                    break
                # player not ready => wait 100 ms
                sleep(0.1)

            # check if player has aborted game
            # => max number of turns has been exceeded.
            if play.action == 'ABORT':
                break   # exit game

            # apply this  action to the current state to get to the next state
            state = Game.next_state(state, play, None, None)

        # check if game has been aborted
        if len(state.players) > 1:
            n_aborted += 1
        else:
            print()
            # check if DeeperShit player is not Shithead
            if state.players[0].name != name:
                n_wins += 1

    ratio = int(n_wins / (i + 1 - n_aborted) * 100)
    print(f"\n         Games:{i+1:>3} Aborted:{n_aborted:>3} Wins:{n_wins:>3}"
          f" ({ratio}%)")


def main():
    """
    Test for Monte Carlo Tree Search (MCTS).

    We use a Shithead end game state (only 2 players left) to test our MCTS
    implementation for Shithead.
    We first load the end game status information from one of the endgame
    json-files. To generate a proper game state from this, we first have to
    create an initial state from the list of players, the dealer, the number
    of used decks, and the log-info.
    """
#    filename = 'shithead/end_games/end_game_state_0.json'
    filename = 'shithead/end_games/end_game_state_1.json'
#    filename = 'shithead/end_games/end_game_state_2.json'
#    filename = 'shithead/end_games/end_game_state_3.json'
#    filename = 'shithead/end_games/end_game_state_4.json'
#    filename = 'shithead/end_games/end_game_state_5.json'
#    filename = 'shithead/end_games/end_game_state_6.json'
#    filename = 'shithead/end_games/end_game_state_7.json'
#    filename = 'shithead/end_games/end_game_state_8.json'
#    filename = 'shithead/end_games/end_game_state_9.json'

    # load end game state and expand 1st node showing details of select,
    # expand, simulate, and backpropagate phases.
    run_first_step(filename)

    # load end game state and build search tree with run_search() for 0.5 s.
    # print status and simulation result for each node.
    # print the final statistics and the the found best play (robust and max).
    test_mcts(filename, 0.1)

    # load end game state and finish the game from this state using a single
    # search tree to find the best plays for both players.
    # All cards in the game are open, i.e. known to both players.
    play_end_game_with_open_cards(filename, timeout=1.0, policy='max')

    # load end game state and finish the game from this state using individual
    # search trees for both players to find the best plays.
    # Each player has a perfect memory and knows all cards which were face up
    # once during the game and all cards in his hand.
    # Each time a previously unknown card is played, players have to make a new
    # assumption about the remaining unknown cards and start a new search tree.
    play_end_game(filename, timeout=1.0, policy='max')

    # load end game state and finish the game from this state using MCTS for
    # the 1st player and the specified AI type for the 2nd player.
    # print MCTS stats and game state in each turn.
    deeper_shit_test(filename, 'DeepShit', 1.0, 'max')

    # load end game state and finish the game with DeeperShit for the 1st
    # player and the specified opponent AI for the 2nd player. Do the same with
    # switched roles and repeat the whole cycle for the specified number of
    # times. Print statistics with win ratio of DeeperShit.
    deeper_shit_performance_test(filename, 'DeepShit', 1.0, 'max', 100)


if __name__ == '__main__':
    # !!!NOTE!!!
    # Trying to call this with
    #     $ python game.py
    # results in an ImportError because I used relative imports for the local
    # modules (pyinstaller is to blame for that).
    # Therefore we have to go one directory up and call it with
    #     $ python -m shithead.monte_carlo
    main()
