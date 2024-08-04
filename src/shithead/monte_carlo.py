"""
Monte Carlo Tree Search (MCTS).

Used by AI players for the the end game, i.e. when the stack is empty and
only 2 players are left in the game.

31.05.2024 Wolfgang Trachsler
"""

import time
import json
from random import randrange

from .game import Game
from .monte_carlo_node import MonteCarloNode
from .fup_table import FupTable, FUP_TABLE_FILE, TEXT_FILE
from .stats import Statistics
from . import player as plr # to avoid confusion with 'player' used as variable name

# Class representing the Monte Carlo search tree.
class MonteCarlo:
    def __init__(self, game, UCB1ExploreParam=2):
        '''
        Constructor.

        :param game: Shithead game (=> game rules).
        :type game: Game
        :param UCB1ExploreParam: Explore parameter used for Upper Confidence
                                 Bound 1.
        :type UCB1ExploreParam: float
        '''
        self.game = game
        self.UCB1ExploreParam = UCB1ExploreParam
        # dictionary mapping State.hash() to MonteCarloNode
        # => a node is unambiguously identified by the play history leading up to its state.
        self.nodes = {}

    def makeNode(self, state):
        '''
        Create dangling node.

        If the specified state does not exist (i.e. there's no key
        corresponding to its play history in the nodes dictionary yet),
        We create a new root node (no parent) and add it to nodes.

        :param state:   Shithead game state.
        :type state:    State
        '''
        if state.hash() not in self.nodes.keys():
            # get the current player in this state
            player = state.players[state.player]
            # get list of legal plays for this player in this state
            unexpandedPlays = player.get_legal_plays(state)
            # create a new node for this state (no parent, no play)
            # and add it to the nodes list
            self.nodes[state.hash()] = MonteCarloNode(None, None, state, unexpandedPlays)

    def select(self, state):
        '''
        Phase 1: Selection.

        Find not fully expanded node or leaf (no more legal plays).
        In Shithead there are no leafs, i.e. there's always a legal play until
        one of the players has lost the game (Shithead = last player with
        cards).

        :param state: Shithead game state.
        :type state: State.
        '''
        # get the root node belonging to this state (play history)
        node = self.nodes[state.hash()]
        # search through tree to find a not fully expanded or leaf node.
        while node.isFullyExpanded() and not node.isLeaf():
            # go to child node which yields the best UCB1
            bestPlay = None             # initialize best play
            bestUCB1 = float('-inf')    # initialize best upper confidence bound 1
            plays = node.allPlays()     # all legal plays from this node
            for play in plays:
                # calculate UCB1 for all children of current node
                childUCB1 = node.childNode(play).getUCB1(self.UCB1ExploreParam)
                if childUCB1 > bestUCB1:
                    bestPlay = play
                    bestUCB1 = childUCB1
            # select the child with the best UCB1 as next node
            node = node.childNode(bestPlay)
        return node

    def expand(self, node):
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
        :param node: node with unexpanded plays
        :type node: MonteCarloNode
        :return: new child of this node.
        :rtype: MonteCarloNode
        '''
        # get a list of unexpanded plays for this node
        plays = node.unexpandedPlays()
        # select one play randomly from this list
        play = plays[randrange(len(plays))]
        # create the child's game state by applying this play to state of this
        # node (= parent).
        childState = self.game.nextState(node.state, play)
        # get the current player in child's state
        player = childState.players[childState.player]
        # get list of legal plays for this player in child's state
        childUnexpandedPlays = player.get_legal_plays(childState)
        # create the child node
        childNode = node.expand(play, childState, childUnexpandedPlays)
        # add the new child node to this node's children
        self.nodes[childState.hash()] = childNode
        # return the new child node
        return childNode

    def simulate(self, node):
        '''
        Phase 3: Simulation

        The specified node is a new child node created during expansion.
        We use the state of this node as starting point of our simulation,
        looping though the following steps:
            - get list of legal plays for the current state.
            - randomly select one of these plays.
            - apply the selected play to the current state to get the next state.
            - check if the next state has winner or a tie.

        :param node: starting node for simulation
        :type node: MonteCarloNode
        :return: 1 => Player1 won, -1 => Player2 won, 0 => Tie.
        :rtype: int
        '''
        # get game state of node, where we start the simulation (= node from
        # expansion)
        state = node.state
        # get loser of this state (i.e. it's possible that there's no need for
        # additional simulation)
        loser = self.game.loser(state)

        # loop till we have found a loser (Shithead)
        while loser is None:
            # get the current player in this state
            player = state.players[state.player]
            # get list of legal plays for this player in this state
            plays = player.get_legal_plays(state)
            # randomly select a play from this list
            play = plays[randrange(len(plays))]
            # apply the selected play to the current state to get the next
            # state
            state = self.game.next_state(state, play)
            # check if we have found the Shithead
            loser = self.game.loser(state)

        return loser

    def backpropagate(self, node, loser):
        '''
        Phase 4: Backpropagation.

        Update the ancestor statistics.
        Follow the search path back to the root node.
        Increment the number of plays in each of these nodes.
        Since the choices made in the parent nodes of the nodes, where the
        winning player is also the current player, the number of wins is only
        incremented in nodes where the opponent of the winning player is the
        current player.
        E.g. If we are in a Tree-Node where Player1 is the current player, we
        use the plays/wins counters in its children's nodes (where Player2 is
        the current player) to calculate the UCB1 to select the next node in
        the selection phase. Thus, if Player1 wins a simulated game, we have to
        contradictorily increment the number of wins in the nodes where Player2
        is the current player.
        Since simulate() returns the name of the loser (Shithead), we just have
        to increment the number of wins in each node of the selected path,
        where the name of the current player matches the name of the loser.
        '''
        if loser is None:
            raise Exception("There's no winner to backpropagate!")

        while node is not None:
            # increment number of plays in every visited node.
            node.n_plays += 1
            # the statistics in the parent nodes is responsible for selecting
            # the node, where the winning player is the current player.
            if node.state.is_player(loser):
                # increment the number of wins in the loser's node
                # because the parent node, where the winner is the current
                # player uses this counter to select the path through the tree.
                node.n_wins += 1
            # move up to the parent node.
            node = node.parent

    def runSearch(self, state, timeout=3):
        '''
        From given state, repeatedly run MCTS to build statistics.

        Use the specified state to create the root node of a new search tree.
        During the specified interval, build the search tree by looping through
        the following 4 phases:
            - selection:
              move down the tree selecting at each node the child node with the
              best UCB1 value, until we have reached a not fully expanded node,
              or a leaf (no more legal plays, this is not possible in Shithead).
            - expansion:
              add a new child to a found node with unexpanded plays.
            - simulation:
              from the state of the new child randomly select legal plays until
              a loser has been found or a leaf has been reached
              (not in Shithead).
            - backpropagation
              Update the statistics of all nodes in the path from the root to
              the found node with the found loser (either loser in a leaf (n.a.)
              or loser found through expansion/simulation).
        '''
        # create the root node of the search tree for this state
        self.makeNode(state)
        print(f"### Number of nodes: {len(self.nodes)}")

        # calculate the end time
        end = time.time() + timeout

        while time.time() < end:
            # find node which is not fully expanded moving along a path
            # following the child nodes with the best UCB1 value.
            node = self.select(state)
            # check if found node already has a loser
            loser = self.game.loser(node.state)
            if not node.isLeaf() and loser is None:
                # not a leaf and no loser found yet
                # => add one new child node using an unexpanded play  of this
                #    node.
                node = self.expand(node)
                # from this new node randomly select plays until a loser has
                # been found or no legal plays are left.
                loser = self.simulate(node)
            # backpropagate the loser of the found node or the loser found by
            # simulation => update n_plays and n_wins counter in all nodes
            #               on the path to the found node.
            #               n_wins is only incremented in nodes where the loser
            #               is the current player.
            self.backpropagate(node, loser)

    def bestPlay(self, state, policy='robust'):
        '''
        Get the best play from available statistics.

        Get a list of all possible plays from this node.
        Loop through this list to find either the most visited child (robust
        child) or the child with the best win/play ratio (max child).
        Return the play which leads to the found child.

        :param state: game state for which we search the best play.
        :type state: State_C4
        :param policy: 'robust' => find robust child, 'max' => find max child.
        :type policy: str
        '''
        # create the root node of the search tree for this state
        # but only if there's not already an entry in dictionary self.nodes for
        # this state's play history.
        # if a new root node is generated we will get an error next then
        # checking if it's fully expanded!
        self.makeNode(state)

        # check if all possible plays for the root node identified by this
        # state's play history have been expanded.
        if self.nodes[state.hash()].isFullyExpanded() == False:
            raise Exception('Not enough information!')

        # get the root node identified by this state's play history.
        node = self.nodes[state.hash()]
        # initialize best play
        bestPlay = None
        # get a list of all possible plays from this node.
        allPlays = node.allPlays()

        # find the child with the most visits (robust child)
        if policy == 'robust':
            max = float('-inf')   # initialize max value
            for play in allPlays:
                childNode = node.childNode(play)
                if childNode.n_plays > max:
                    bestPlay = play
                    max = childNode.n_plays

        # find the child with the highest win rate (max child)
        if policy == 'max':
            max = float('-inf')   # initialize max value
            for play in allPlays:
                childNode = node.childNode(play)
                ratio = childNode.n_wins / childNode.n_plays
                if ratio > max:
                    bestPlay = play
                    max = ratio

        return bestPlay

    def getStats(self, state):
        '''
        Return MCTS statistics this state.

        Returns the number of plays and the number of wins for node identified
        by the play history of this state and a list with the number of plays
        and wins for each of its children.

        :param state: game state identifying the node for which we want the stats.
        :type state: State
        :return: stats for node and its children.
        :rtype: dict.
        '''
        node = self.nodes[state.hash()]
        stats = {'n_plays': node.n_plays,
                 'n_wins': node.n_wins,
                 'children': [] }
        for child in node.children.values():
            if child['node'] is None:
                stats['children'].append({'play': child['play'],
                                          'n_plays': None,
                                          'n_wins': None})
            else:
                stats['children'].append({'play': child['play'],
                                          'n_plays': child['node'].n_plays,
                                          'n_wins': child['node'].n_wins})
        return stats

    def printStats(self, state):
        stats = self.getStats(state)
        for entry in stats['children']:
            if entry['n_plays']:
                print('play:{} visits:{:>6} wins:{:>6}'.format(
                       entry['play'].hash(), entry['n_plays'], entry['n_wins']))
        print('total:   visits:{:>6} wins:{:>6}'.format(stats['n_plays'], stats['n_wins']))

def main():
    """
    Test for Monte Carlo Tree Search (MCTS).

    We use a Shithead end game state (only 2 players left) to test our MCTS
    implementation for Shithead.
    """
    state_file = 'shithead/end_games/end_game_state_1.json'
    try:
        # load end game state from json-file
        with open(state_file, 'r') as json_file:
            state_info = json.load(json_file)
    except OSError as exception:
        print(f"### Error: couldn't load file {filename}")
        return

    # print the loaded game state
    state_info_str = json.dumps(state_info, indent=4)
    print(state_info_str)

    # statistic counters
    n_finished = 0  # number of finished games
    n_aborted = 0   # number of aborted games
    n_turns = 0     # number of turns played
    n_talon = 0     # number of talon cards
    n_refills = 0   # number of refill turns

    # get index of the dealer from state info
    dealer = state_info['dealer']

    # get the number of necessary card decks from state info
    n_decks = state_info['n_decks']

    # create the logging info from the state info
    # => we can change it by editing the JSON string
    log_info = state_info['log_info']

    # create face up table
    fup_table = FupTable()

    # create statistics
    stats = Statistics()

    # load face up table from file (in package)
    fup_table.load(FUP_TABLE_FILE, True)


    # get number of remaining players from loaded state (should be 2)
    n_players = len(state_info['players'])

    # create list of remaining players with type='ShitHappens' => random play
    players = []
    for j in range(n_players):
        players.append(plr.ShitHappens('', fup_table))

if __name__ == '__main__':
    """
    !!!NOTE!!!
    Trying to call this with 
        $ python game.py
    results in an ImportError because I used relative imports for the local
    modules (pyinstaller is to blame for that).
    Therefore we have to go one directory up and call it with
        $ python -m shithead.game
    """
    main()