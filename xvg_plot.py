#!/usr/bin/env python

"""

xvg_plot.py

Python script to plot XVG line charts produced by GROMACS analysis tools.

Requires:
    * python2.7+
    * matplotlib
    * numpy
"""

from __future__ import print_function

__author__ = 'Joao Rodrigues'
__email__ = 'j.p.g.l.m.rodrigues@gmail.com'

import os
import re
import shlex
import sys

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError as e:
    print('[!] The required Python libraries could not be imported:', file=sys.stderr)
    print('\t{0}'.format(e))
    sys.exit(1)

##      

def parse_xvg(fname):
    """Parses XVG file legends and data"""
    
    _ignored = set(('legend', 'view'))
    _re_series = re.compile('s[0-9]+$')
    _re_xyaxis = re.compile('[xy]axis$')

    metadata = {}
    num_data = []
    
    metadata['labels'] = {}
    metadata['labels']['series'] = []

    ff_path = os.path.abspath(fname)
    if not os.path.isfile(ff_path):
        raise IOError('File not readable: {0}'.format(ff_path))
    
    with open(ff_path, 'r') as fhandle:
        for line in fhandle:
            line = line.strip()
            if line.startswith('@'):
                tokens = shlex.split(line[1:])
                if tokens[0] in _ignored:
                    continue
                elif tokens[0] == 'TYPE':
                    if tokens[1] != 'xy':
                        raise ValueError('Chart type unsupported: \'{0}\'. Must be \'xy\''.format(tokens[1]))
                elif _re_series.match(tokens[0]):
                    metadata['labels']['series'].append(tokens[-1])
                elif _re_xyaxis.match(tokens[0]):
                    metadata['labels'][tokens[0]] = tokens[-1]
                elif len(tokens) == 2:
                    metadata[tokens[0]] = tokens[1]
                else:
                    print('Unsupported entry: {0} - ignoring'.format(tokens[0]), file=sys.stderr)
            elif line[0].isdigit():
                num_data.append(map(float, line.split()))
    
    num_data = zip(*num_data)
    
    n_labels = len(metadata['labels']['series'])
    n_series = len(num_data[1:])
    if n_labels != n_series:
        print('[!] Some series are not labelled. DO NO TRUST THE PLOT LABELS')
        for missing in range(n_series - n_labels):
            metadata['labels']['series'].append('Missing')
    
    return metadata, num_data

def running_average(data, metadata, window=10):
    """
    Performs a running average calculation over all series in data.
    Assumes the first series is the x-axis.
    Appends the series and a new label to the original data and label arrays.
    """

    weights = np.repeat(1.0, window)/window
    s_labels = metadata['labels']['series']
    for n_series, series in enumerate(data[1:]):
        series_rav = np.convolve(series, weights, 'valid')
        s_labels.append('{0} (Av)'.format(s_labels[n_series]))
        data.append(series_rav)

    return metadata, data

def plot_data(data, metadata, window=1, interactive=True, outfile=None, 
              colormap='Set1', bg_color='lightgray'):
    """
    Plotting function.
    """
    
    n_series = len(data) - 1
    
    f = plt.figure()
    ax = plt.gca()
    
    color_map = getattr(plt.cm, colormap)
    color_list = color_map(np.linspace(0, 1, n_series))

    for i, series in enumerate(data[1:]):
        try:
            label = metadata['labels']['series'][i]
        except IndexError as e:
            label = ''
        
        # Adjust x-axis for running average series
        if label.endswith('(Av)'):
            x_data = data[0][window - 1:]
        else:
            x_data = data[0]
        
        ax.plot(x_data, series, c=color_list[i], label=label)

    # Formatting Labels & Appearance
    ax.set_xlabel(metadata['labels'].get('xaxis', ''))
    ax.set_ylabel(metadata['labels'].get('yaxis', ''))
    ax.set_title(metadata.get('title', ''))
    
    ax.set_axis_bgcolor(bg_color)
    ax.grid('on')
    
    legend = ax.legend()
    frame = legend.get_frame()
    frame.set_facecolor(bg_color)
    
    if outfile:
        plt.savefig(outfile)
        
    if interactive:
        plt.show()
    
    return
##

if __name__ == '__main__':

    import argparse
    from argparse import RawDescriptionHelpFormatter
    
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)

    ap.add_argument('xvg_f', type=str, help='XVG input file', metavar='XVG input file')

    io_group = ap.add_mutually_exclusive_group(required=True)
    io_group.add_argument('-o', '--output', type=str, help='PDF output file')
    io_group.add_argument('-i', '--interactive', action='store_true', 
                    help='Launches an interactive matplotlib session')

    ana_group = ap.add_argument_group('Data Analysis')
    ana_group.add_argument('-a', '--average', action='store_true', 
                    help='Smoothes each series using a running average')
    ana_group.add_argument('-w', '--window', type=int, default=10, 
                    help='Window size for the running average calculation [Default: 10]')
    
    ot_group = ap.add_argument_group('Other Options')
    ot_group.add_argument('-c', '--colormap', default='Set1',
                          help='Range of colors used for each series in the plot. For a list of all\
                                available colormaps refer to \
                                matplotlib.org/examples/color/colormaps_reference.html')

    ot_group.add_argument('-b', '--background-color', default='lightgray',
                          help='Background color used in the plot. For a list of all available \
                                colors refer to \
                                matplotlib.org/examples/color/named_colors.html')
    cmd = ap.parse_args()
    
    metadata, data = parse_xvg(cmd.xvg_f)
    n_series = len(data[1:])
    n_elements = sum(map(len, data[1:]))
    print('[+] Read {0} series of data ({1} elements)'.format(n_series, n_elements))

    if cmd.average:
        print('[+] Calculating Running Averages (window size = {0})'.format(cmd.window))
        metadata, data = running_average(data, metadata, window=cmd.window)

    plot_data(data, metadata, 
              window=cmd.window, 
              interactive=cmd.interactive, outfile=cmd.output,
              colormap=cmd.colormap, bg_color=cmd.background_color)
    