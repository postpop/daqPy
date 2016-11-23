import h5py
import numpy as np
import matplotlib
from tools import *
matplotlib.use('tkagg')
import matplotlib.pyplot as plt


def coroutine(func):
    """ decorator that auto-initializes (calls `next(None)`) coroutines"""
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.next()
        return cr
    return start


@coroutine
def plot_rt():
    '''coroutine for plotting
    fast, realtime as per: https://gist.github.com/pklaus/62e649be55681961f6c4
    '''
    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.show(False)
    plt.draw()
    fig.canvas.start_event_loop(0.001)  # otherwise plot freezes after 3-4 iterations
    bgrd = fig.canvas.copy_from_bbox(ax.bbox)  # cache the background
    points = ax.plot(np.arange(10000), np.zeros((10000, 1)))[0]  # init plot content
    while True:
        data = (yield)  # gets sent variables
        print("plotting {0}".format(data.shape))
        fig.canvas.restore_region(bgrd)  # restore background
        for chn in range(data.shape[1]):
            points.set_data(np.arange(10000), data[:10000, chn])
            ax.draw_artist(points)           # redraw just the points
        fig.canvas.blit(ax.bbox)         # fill in the axes rectangle
        ax.relim()
        ax.autoscale_view()                 # rescale the y-axis


@coroutine
def plot():
    '''coroutine for plotting - simple'''
    plt.ion()
    fig = plt.figure()
    fig.canvas.start_event_loop(0.001)  # otherwise plot freezes after 3-4 iterations
    ax = fig.add_subplot(111)
    while True:
        data = (yield)  # gets sent variables
        print("plotting {0}".format(data.shape))
        ax.clear()
        ax.plot(data[:1000, :])
        plt.pause(0.001)


@coroutine
def save(file_name, channels=1):
    '''coroutine for saving'''
    f = h5py.File(file_name, "w")  # open file
    dset = f.create_dataset("mydataset", shape=(10000, channels), maxshape=(None, channels), dtype=np.float64)
    print(file_name)
    try:
        while True:
            data = (yield)  # gets sent variables
            print("saving {0} to {1}".format(data.shape, file_name))
            dset.resize(dset.shape[0] + data.shape[0], axis=0)
            dset[-data.shape[0]:, :] = data  # save data
            f.flush()  # flush data to disk so we don't lose it all during a crash
    except GeneratorExit:
        print("   closing file \"{0}\".".format(file_name))
        f.flush()  # final flush before we close
        f.close()


def log(file_name):
    f = open(file_name, 'r')      # open file
    try:
        while True:
            message = (yield)  # gets sent variables
            f.write(message)  # write log to file
    except GeneratorExit:
        print("   closing file \"{0}\".".format(file_name))
        f.close()  # close file


def data(stim=None, stim_order=None):
    '''generator yield next chunk of data for output'''
    # generate all stimuli
    count = 0  # init counter
    try:
        while True:
            count += 1
            print("{0}: generating {1}".format(count, stim[(count - 1) % len(stim)].shape))
            yield stim[(count - 1) % len(stim)]
    except GeneratorExit:
        print("   cleaning up dategen.")
