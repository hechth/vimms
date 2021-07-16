import math
import random
from collections import OrderedDict
from abc import ABC, abstractmethod
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches

class RGBColour():
    def __init__(self, R, G, B): self.R, self.G, self.B = R, G, B
    def __repr__(self): return f"RGBColour({self.R}, {self.G}, {self.B})"
    def __add__(self, other): return RGBColour(self.R + other.R, self.G + other.G, self.B + other.B)
    def __mul__(self, scalar): return RGBColour(self.R * scalar, self.G * scalar, self.B * scalar)
    def __rmul__(self, scalar): return self.__mul__(self.scalar)
    def squash(self): return (self.R / 255.0, self.G / 255.0, self.B / 255.0)
    def interpolate(self, others, weights=None):
        colours = others + [self]
        weights = [1 / len(colours) for _ in colours] if weights is None else weights
        return sum((c * w for c, w in zip(colours, weights)), start=RGBColour(0, 0, 0))

class ColourMap():

    PURE_RED = RGBColour(255, 0, 0)
    PURE_GREEN = RGBColour(0, 255, 0)
    PURE_BLUE = RGBColour(0, 0, 255)
    
    RED = RGBColour(237, 28, 36)
    ORANGE = RGBColour(255, 127, 39)
    YELLOW = RGBColour(255, 242, 0)
    GREEN = RGBColour(34, 177, 76)
    LIGHT_BLUE = RGBColour(0, 162, 232)
    INDIGO = RGBColour(63, 72, 204)
    VIOLET = RGBColour(163, 73, 164)

    @abstractmethod
    def __init__(self): pass

    @abstractmethod
    def assign_colours(self, boxes, key): pass
    
    def add_to_subplot(self, ax, boxes, key):
        for box, colour in self.assign_colours(boxes, key):
            ax.add_patch(patches.Rectangle((box.pt1.x, box.pt1.y), box.pt2.x - box.pt1.x, box.pt2.y - box.pt1.y, linewidth=1, ec="black", fc=colour.squash()))

    def get_plot(self, boxes, key):
        fig, ax = plt.subplots(1)
        self.add_to_subplot(ax, boxes, key)
        ax.set_xlim([min(b.pt1.x for b in boxes), max(b.pt2.x for b in boxes)])
        ax.set_ylim([min(b.pt1.y for b in boxes), max(b.pt2.y for b in boxes)])
        return plt
        
class FixedMap(ColourMap):
    '''Allows specifying a mapping from an enumeration of some property of interest to some list of colours.'''
    def __init__(self, mapping): 
        self.mapping = mapping
        
    def assign_colours(self, boxes, key):
        return ((b, self.mapping[min(key(b), len(self.mapping) - 1)]) for b in boxes)
        
    def unique_colours(self, boxes):
        return ((b, self.mapping[min(i, len(self.mapping) - 1)]) for i, b in enumerate(boxes))
        
class InterpolationMap(ColourMap):
    '''Allows assigning colours by interpolating between pairs of n colours specified across a value range of some property of interest.'''
    def __init__(self, colours):
        self.colours = list(colours)
        
    def assign_colours(self, boxes, key):
        minm = min(key(b) for b in boxes)
        maxm = max(key(b) for b in boxes)
        intervals = [minm + i * (maxm - minm) / (len(self.colours) - 1) for i in range(len(self.colours))]
    
        def get_colour(box):
            if(math.isclose(minm, maxm)): return self.colours[0]
            i = next(i-1 for i, threshold in enumerate(intervals) if threshold >= key(box))
            weight = (key(box) - intervals[i]) / (intervals[i + 1] - intervals[i])
            return self.colours[i].interpolate([self.colours[i+1]], weights=[weight, 1-weight])
        
        return ((b, get_colour(b)) for b in boxes)
        
class AutoColourMap(ColourMap):
    
    def __init__(self, colour_picker, reuse_colours=False):
        self.colour_picker = colour_picker
        self.reuse_colours = reuse_colours
        
    @staticmethod
    def random_colours(boxes):
        return ((b, RGBColour(*(random.uniform(0, 255) for _ in range(3)))) for b in boxes)

    def assign_colours(self, boxes):
        #if there's no path from one box to another when we build a graph of their overlaps, we can re-use colours
        pairs = [(top, set()) for b in boxes for top in b.parents]
        top_level = OrderedDict(pairs) #need uniqueness and maintain ordering
        if(self.reuse_colours):
            for b in boxes:
                for top in b.parents: top_level[top].add(b) #note same set references in pairs and top_level
                
            components, indices = [], [-1 for _ in pairs]
            for i, (parent, children) in enumerate(top_level.items()):
                if(indices[i] == -1):
                    indices[i] = len(components)
                    components.append(OrderedDict([(parent, None)]))
                update = [(j, k) for j, (k, v) in enumerate(pairs[i:]) if children & v]
                for (j, k) in update:
                    indices[j] = indices[i]
                    components[indices[i]][k] = None
        else:
            components = [top_level]
                    
        top_level_colours = {top : colour for cs in components for top, colour in self.colour_picker(cs.keys())}
        def interpolate_lower(box): return top_level_colours[box.parents[0]].interpolate([top_level_colours[b] for b in box.parents[1:]])
        return ((b, interpolate_lower(b)) for b in boxes)
        
    def add_to_subplot(self, ax, boxes):
        for box, colour in self.assign_colours(boxes):
            ax.add_patch(patches.Rectangle((box.pt1.x, box.pt1.y), box.pt2.x - box.pt1.x, box.pt2.y - box.pt1.y, linewidth=1, ec="black", fc=colour.squash()))    
        
    def get_plot(self, boxes):
        fig, ax = plt.subplots(1)
        self.add_to_subplot(ax, boxes)
        ax.set_xlim([min(b.pt1.x for b in boxes), max(b.pt2.x for b in boxes)])
        ax.set_ylim([min(b.pt1.y for b in boxes), max(b.pt2.y for b in boxes)])
        return plt