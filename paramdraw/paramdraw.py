import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.text
#import matplotlib.artist as artist
#import matplotlib.colors as colors
#import matplotlib.patches as patches
#import matplotlib.mathtext as mathtext
#import matplotlib.image as image
from matplotlib.lines import Line2D
#from matplotlib.widgets import Button

class ParamSpec(object):
    """A specification for a parameter curve."""
    
    @property
    def x(self):
        return [x for (x,y) in self.targets]
 
    @property
    def xfmt(self):
        return self._xfmt

    @xfmt.setter
    def xfmt(self, fmt):
        self._xfmt =  "{:" + fmt + "}"

    @property
    def y(self):
        return [y for (x,y) in self.targets]

    @property
    def yfmt(self):
        return self._yfmt

    @yfmt.setter
    def yfmt(self, fmt):
        self._yfmt =  "{:" + fmt + "}"

    @property
    def interp_y(self):
        """Return an interpolated y value for every x in grid_x.
        """
        interp_y = np.empty(self.grid_x.shape)
        interp_y[:] = np.nan
        for tgt1,tgt2 in zip(self.targets[:], self.targets[1:]):
            idx1 = np.nonzero(self.grid_x == tgt1[0])[0][0]
            idx2 = np.nonzero(self.grid_x == tgt2[0])[0][0]
            # snap_to_grid() doesn't snap if len(grid_y) == 2
            interp_y[idx1:idx2+1] = self.snap_to_grid(y=np.linspace(tgt1[1], tgt2[1], idx2 - idx1 + 1))
            #if len(self.grid_y) == 2:
            #    interp_y[idx1:idx2+1] = np.linspace(tgt1[1], tgt2[1], idx2 - idx1 + 1)
            #else:
                #interp_y[idx1:idx2+1] = self.snap_to_grid(y=np.linspace(tgt1[1], tgt2[1], idx2 - idx1 + 1))
                #interp_y[idx1:idx2+1] = np.round(np.linspace(tgt1[1], tgt2[1], idx2 - idx1 + 1))
        return interp_y
    
    @property
    def norm_interp_y(self):
        y = self.interp_y
        scale = np.max(self.grid_y) - np.min(self.grid_y)
        if scale != 0:
            #norm_y = (y - y.min())/max(abs(self.grid_y))
            y = (y - np.min(y)) / scale
        return y

    def __init__(self, name, grid_x, grid_y, default_y=None, xfmt="0.3f", yfmt="0.3f", targets=[], manager=None, lineprops={}):
        """Constructor."""

        self.name = name
        self.grid_x = np.array(grid_x)
        self.grid_y = np.array(grid_y)
        if default_y == None:
            self.default_y = self.snap_to_grid(y=np.mean(grid_y))
        else:
            self.default_y = self.snap_to_grid(y=default_y)
        self.targets = targets
        self.manager = manager
        self.xfmt = xfmt
        self.yfmt = yfmt
        self.lineprops = lineprops
 
    def add_target(self, add_x, add_y):
        add_x = self.snap_to_grid(x=add_x)
        add_y = self.snap_to_grid(y=add_y)
        
        try:
            # Find the first existing x >= the x to be added and insert before it if >, or
            # overwrite it if they are ==.
            idx = [x >= add_x for x in self.x].index(True)
            if self.targets[idx][0] == add_x:
                self.targets[idx] = (add_x, add_y)
            else:
                self.targets.insert(idx, (add_x, add_y))
        except ValueError:                   # Couldn't find one.
            if self.targets == []:           # There are no existing x.
                self.targets = [(add_x, add_y)]
            else:                            # x to be added > all existing x.
                self.targets.append((add_x, add_y))
        except:
            raise("Unexpected error:", sys.exc_info()[0])
            raise
        self.manager({'event': 'data_changed', 'paramspec': self})

    def del_target(self, del_x):
        del_x = self.snap_to_grid(x=del_x)
        if del_x != self.grid_x[0] and del_x != self.grid_x[-1]:
            idx = [x == del_x for x in self.x].index(True)
            del self.targets[idx]
            self.manager({'event': 'data_changed', 'paramspec': self})

    def del_target_by_idx(self, idx):
        """Delete a target by its index in self.targets."""
        if idx != 0 and idx != (len(self.targets) - 1):
            del self.targets[idx]
            self.manager({'event': 'data_changed', 'paramspec': self})


    # Parameters are 'x' and 'y'. We use **kwargs to force you to specify them
    # as a keyword argument, e.g.
    # snap_to_grid(y=2.9)
    # snap_to_grid(x=1.5)
    # If we didn't do this, you might accidentally try to snap a y value to grid_x.
    def snap_to_grid(self, **kwargs):
        """Snap coordinates to allowed values."""
        if len(kwargs.keys()) != 1:
            raise("Wrong number of arguments for snap_to_grid(). Must be one of 'x=' or 'y=' only.")
            
        retval = None
        if 'x' in kwargs.keys():
            if len(self.grid_x) == 2:
                retval = kwargs['x']
            else:
                grid_diff = abs(self.grid_x - kwargs['x'])
                snapidx = grid_diff.tolist().index(min(grid_diff))
                retval = self.grid_x[snapidx]
        elif 'y' in kwargs.keys():
            if len(self.grid_y) == 2:
                retval = kwargs['y']     # don't snap to grid
            else:
# TODO: this could probably be made more elegant/vectorized
# TODO: handle an array of x as well
                try:    # array of y values
                    grid_diff = [np.abs(self.grid_y - y) for y in kwargs['y']]
                    snapidx = [arr.tolist().index(min(arr)) for arr in grid_diff]
                    retval = self.grid_y[snapidx]
                except TypeError:  # whoops, must have been a single y value
                    grid_diff = abs(self.grid_y - kwargs['y'])
                    snapidx = grid_diff.tolist().index(min(grid_diff))
                    retval = self.grid_y[snapidx]

        return retval

class ParamDrawAxes(object):
    """Axes for interactively drawing a parameter curve.
 
    """

    @property
    def paramspec(self):
        return self._paramspec
    
    @paramspec.setter
    def paramspec(self, value):
        self._paramspec = value
        self.style_axes()
        self.line.set_data(self.paramspec.x, self.paramspec.y)
        self.interp_line.set_data(self.paramspec.grid_x, self.paramspec.interp_y)
        self._update_param()
    
    def __init__(self, ax, motion_callback=None):
        """Constructor.
 
        Add the parameter line to a figure.
 
        """
        self._paramspec = None
        self.ax = ax
        self.ax.set_xticklabels([])
    
        # Empty line
        line = Line2D([], [], ls='--', c='#666666',
                  marker='x', mew=2, mec='#204a87', picker=5)
        ax.add_line(line)
        interp_line = Line2D([], [], c='#333333', alpha=0.5)
        ax.add_line(interp_line)
        self.style_axes()
        self.line = line
        self.position_text = matplotlib.text.Text()
        self.ax.add_artist(self.position_text)
        self.position_marker = matplotlib.text.Text(text='+', color='red', horizontalalignment='center', verticalalignment='center')
        self.ax.add_artist(self.position_marker)
        self.interp_line = interp_line
        self.canvas = line.figure.canvas
        self._deleting_marker = False
 
        # Event handler for mouse clicking in axes.
        self.cid = self.canvas.mpl_connect('button_release_event', self)
         
        # Callback for mouse clicking on markers.
        self.canvas.callbacks.connect('pick_event', self.on_marker_pick)

        # Callback to keep statusbar up to date with position
        if motion_callback != None:
            self.canvas.callbacks.connect('motion_notify_event', motion_callback)

    def style_axes(self):
        self.ax.xaxis.grid(color='gray')
        try:
            assert(len(self.paramspec.grid_y) > 2)
            self.ax.yaxis.grid(color='gray')
        except AttributeError, AssertionError:    # self.paramspec == None or grid_y !> 2
            self.ax.yaxis.grid(False)
        try:
            self.ax.set_ylim(self.paramspec.grid_y[0], self.paramspec.grid_y[-1])
            self.ax.set_xticks(self.paramspec.grid_x)
            self.ax.set_yticks(self.paramspec.grid_y)
            self.ax.set_title("Drawing parameter: {:s}".format(self.paramspec.name))
        except AttributeError:                    # self.paramspec == None
            pass

    def __call__(self, event):
        if event.inaxes != self.line.axes:
            return

        if self._deleting_marker:
            self._deleting_marker = False
        else:
            self.paramspec.add_target(event.xdata, event.ydata)
            self.line.set_data(self.paramspec.x, self.paramspec.y)
            self.interp_line.set_data(self.paramspec.grid_x, self.paramspec.interp_y)
            self._update_param()
 
    def _update_param(self):
        self.canvas.draw()
 

    def on_marker_pick(self, event):
        self._deleting_marker = True
        self.paramspec.del_target_by_idx(event.ind)
        self.line.set_data(self.paramspec.x, self.paramspec.y)
        self.interp_line.set_data(self.paramspec.grid_x, self.paramspec.interp_y)
        self._update_param()

    def on_mouse_motion(self, event):
        self.position_text.set_text(event['msg'])
        self.position_text.set_position((event['x'], event['y']))
        if event['x'] >= np.mean(self.paramspec.grid_x):
            self.position_text.set_horizontalalignment('right')
        else:
            self.position_text.set_horizontalalignment('left')
        if event['y'] >= np.mean(self.paramspec.grid_y):
            self.position_text.set_verticalalignment('top')
        else:
            self.position_text.set_verticalalignment('bottom')
        self.position_marker.set_position((event['x'], event['y']))
        self._update_param()

class ParamShowAxes(object):
    """Axes showing parameter curves.
 
    """

    def __init__(self, ax):
        """Constructor.
 
        Add the parameter line to a figure.
 
        """
        self.ax = ax
        self.ax.set_yticklabels([])
        self._paramspecs = {}
        self.canvas = ax.figure.canvas
        
    def add_paramspec(self, paramspec):
        """Add a ParamSpec to the axes."""
        line = Line2D(paramspec.grid_x, paramspec.norm_interp_y, **paramspec.lineprops)
        self.ax.add_line(line)
        self.canvas.draw()
        self._paramspecs[paramspec.name] = {'paramspec': paramspec, 'line': line}
        
    def redraw(self):
        for pspec in self._paramspecs.values():
            pspec['line'].set_data(pspec['paramspec'].grid_x, pspec['paramspec'].norm_interp_y)
        self.canvas.draw()

class ParamSpecManager(object):
    def __init__(self, paramspecs, draw_axes, show_axes, motion_callback=None):
        #fig, ax = plt.subplots(2, 1, sharex=True, sharey=False, figsize=(24,12))
        self.figure = draw_axes.figure
        self.draw_axes = draw_axes
        self.show_axes = show_axes
        min_x = np.min([x.grid_x[0] for x in paramspecs.values()])
        max_x = np.max([x.grid_x[-1] for x in paramspecs.values()])
        self.draw_axes.set_xlim([min_x, max_x])
        self.show_axes.set_xlim([min_x, max_x])
        self.paramspecs = paramspecs
        pdx = ParamDrawAxes(self.draw_axes, motion_callback=motion_callback)
        self.pdx = pdx
        psx = ParamShowAxes(self.show_axes)
        self.psx = psx
        for pspec in paramspecs.values():
            pspec.manager = self
            self.add_target_to(pspec.name, pspec.grid_x[0], pspec.default_y)
            self.add_target_to(pspec.name, pspec.grid_x[-1], pspec.default_y)
            psx.add_paramspec(pspec)
        
    def __call__(self, event):
        if event['event'] == 'data_changed':
            self.psx.redraw()
    
    def add_target_to(self, name, add_x, add_y):
        """Add a target to ParamSpec identified by name."""
        self.paramspecs[name].add_target(add_x, add_y)

    def show(self):
        plt.show()

    def select_paramspec(self, name):
        if name in self.paramspecs.keys():
            self.pdx.paramspec = self.paramspecs[name]
