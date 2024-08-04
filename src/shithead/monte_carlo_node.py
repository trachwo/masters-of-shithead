"""
Monte Carlo Tree Search (MCTS) Node.

Used to implement MCTS for the the end game, i.e. when the stack is empty and
only 2 players are left in the game.

30.05.2024 Wolfgang Trachsler
"""

import numpy as np
from .state import State
from .play import Play


# Class representing a node in the search tree.
class MonteCarloNode():
    """
    Class representing a node in the search tree.

    """
    def __init__(self, parent, play, state, unexpandedPlays):
        '''
        Create a new node of the search tree.

        :param parent: parent node.
        :type parent: MonteCarloNode
        :param play: the play which brought us here from the parent node.
        :type play: Play
        :param state: the current state of the game.
        :type state: State
        :param unexpandedPlays: list of plays not yet taken from this state.
        :type unexpandedPlays: list
        '''
        # the action which brought us from the parent node to this node
        self.play = play
        # the current state of the game (each node needs its own copy)
        # deepcopy causes problems in case of multithreading,
        # therefore we use copy method of the State class.
        self.state = state.copy()

        # Monte Carlo stuff
        self.n_plays = 0    # number of plays with this node
        self.n_wins = 0     # number of wins with this node

        # Tree stuff
        self.parent = parent    # the parent node
        # create the list of children nodes
        # as dictionary using the play string '<action>:<index>' as key.
        # each entry is a dictionary with a 'play' and a 'node' (not yet
        # created) entry.
        self.children = {}
        for unexp_play in unexpandedPlays:
            self.children[str(unexp_play)] = {'play': unexp_play, 'node':None}

    def childNode(self, play):
        '''
        Returns child reached with specified play.

        Uses the string '<action>:<index>' of this play to get the corresponding
        entry in the children list.
        Throws an exception if the play does not exist, or if the corresponding
        child has not been expanded.

        :param play: a legal play available in the current state.
        :type play: Play
        :return: the child node reached with this play.
        :rtype: MonteCarloNode
        '''
        try:
            child = self.children[str(play)]
        except KeyError:
            raise Exception('No such play!')
        if child['node'] is None:
            raise Exception('Child is not expanded!')
        return child['node']

    def expand(self, play, childState, unexpandedPlays):
        '''
        Create a new child node for a legal play from this state.

        Check if specified play is legal, i.e. it has a corresponding key in
        the children list of this node.
        Create a new node using this node as parent.
        Update the corresponding entry in the children list with the new node.

        :param play: play which leads from parent to child node.
        :type play: Play
        :param childState: game state after play has been applied to the
                           current state.
        :type childState: State
        :param unexpandedPlays: list of legal plays available in the child state.
        :type unexpandedPlays: list
        :return: new child node
        :rtype: MontecarloNode
        '''
        # check if specified play is a key for the childrens list
        if str(play) not in self.children.keys():
            raise Exception('No such play!')
        # create a new node
        childNode = MonteCarloNode(self, play, childState, unexpandedPlays)
        # update the children list entry with the new node
        self.children[str(play)].update({'node': childNode})
        return childNode

    def allPlays(self):
        '''
        Extract all plays from the children list.

        :return: list of plays extracted from children list.
        :rtype: list
        '''
        ret = []
        for child in self.children.values():
            ret.append(child['play'])
        return ret

    def unexpandedPlays(self):
        '''
        Extract all plays leading to an unexpanded node from the children list.

        :return: plays in children list with unexpanded nodes.
        :rtype: list
        '''
        ret = []
        for child in self.children.values():
            if child['node'] is None:
                ret.append(child['play'])
        return ret

    def isFullyExpanded(self):
        '''
        Check if this node has been fully expanded.

        :return: True => no unexpanded children left.
        :rtype: bool
        '''
        for child in self.children.values():
            if child['node'] is None:
                return False
        else:
            return True

    def isLeaf(self):
        '''
        Check if this is a terminal node.

        A terminal node in this context is a node from which no more legal
        plays are possible, It does not include nodes, there one of the players
        has won the game.
        !!! NOTE !!!
        This is not possible in a game of Shithead.
        There are no patts in Shithead.

        :return: True => no more legal plays possible.
        :rtype: bool
        '''
        if self.children:
            return False
        else:
            return True     # not possible !!! TODO Exception ???

    def getUCB1(self, biasParam):
        '''
        Calculate Upper Confidence Bound 1 for this node.

        This provides the heuristics for finding optimal paths through the
        search tree.
        The exploitation term makes nodes preferable which have already been
        used in a lot of wins, while the exploration term makes nodes
        preferable which have not been used a lot.

        :param biasParam: usually sqrt(2).
        :type biasParam: float.
        :return: Upper Confidence Bound 1.
        :rtype: float.
        '''
        # exploitation term: grows the more this node has been involved in wins
        exploitation = self.n_wins / self.n_plays
        # exploration term: grows the less a node has been selected
        exploration = np.sqrt(biasParam * np.log(self.parent.n_plays) / self.n_plays)
        # return the upper confidence bound 1
        return exploitation + exploration