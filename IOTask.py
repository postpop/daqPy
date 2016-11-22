# -*- coding: utf-8 -*-
import PyDAQmx as daq
from PyDAQmx.DAQmxCallBack import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

from tools import *
import threading
import time
import numpy as np

# callback specific imports
# import matplotlib
# matplotlib.use('tkagg')
import matplotlib.pyplot as plt
import h5py


class IOTask(daq.Task):
    def __init__(self, dev_name="Dev1", cha_name=["ai0"], data_len=1000, limits=10.0, rate=10000.0):
        # check inputs
        daq.Task.__init__(self)
        assert isinstance(cha_name, list)

        self.read = daq.int32()
        self.read_float64 = daq.float64()
        cha_types = {"i": "input", "o": "output"}
        self.cha_type = [cha_types[cha[1]] for cha in cha_name]
        self.cha_name = [dev_name + '/' + ch for ch in cha_name]  # append device name
        self.cha_string = ", ".join(self.cha_name)
        self.num_channels = len(cha_name)

        clock_source = None  # use internal clock
        # FIX: input and output tasks can have different sizes
        self.callback = None
        self.data_gen = None  # called at start of callback
        self.data_rec = None  # called at end of callback
        if self.cha_type[0] is "input":
            self.num_samples_per_chan = 10000
            self.num_samples_per_event = 10000#self.num_samples_per_chan*self.num_channels
            self.CreateAIVoltageChan(self.cha_string, "", DAQmx_Val_RSE, -limits, limits, DAQmx_Val_Volts, None)            
            self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, self.num_samples_per_event, 0)
            self.CfgInputBuffer(self.num_samples_per_chan*self.num_channels*4)
        elif self.cha_type[0] is "output":
            self.num_samples_per_chan = 5000
            self.num_samples_per_event = 50  # determines shortest interval at which new data can be generated
            self.CreateAOVoltageChan(self.cha_string, "", -limits, limits, DAQmx_Val_Volts, None)
            self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Transferred_From_Buffer, self.num_samples_per_event, 0)
            self.CfgOutputBuffer(self.num_samples_per_chan*self.num_channels*2)
            self.SetWriteRegenMode(DAQmx_Val_DoNotAllowRegen)  # ensures continuous output and avoids collision of old and new data in buffer            
        self._data = np.zeros((self.num_samples_per_chan, self.num_channels), dtype=np.float64)  # init empty data array
        self.CfgSampClkTiming(clock_source, rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, self.num_samples_per_chan)
        self.AutoRegisterDoneEvent(0)
        self._data_lock = threading.Lock()
        self._newdata_event = threading.Event()
        if self.cha_type[0] is "output":
            self.EveryNCallback()  # fill buffer on init

    def stop(self):
        if self.data_gen is not None:
            self._data = self.data_gen.close()  # get data from data generator
        if self.data_rec is not None:
            for data_rec in self.data_rec:
                data_rec.close()

    # FIX: different functions for AI and AO task types instead of in-function switching?
    #      or maybe pass function handle?
    def EveryNCallback(self):
        with self._data_lock:
            if self.data_gen is not None:
                self._data = self.data_gen.next()  # get data from data generator
            if self.cha_type[0] is "input":
                self.ReadAnalogF64(DAQmx_Val_Auto, 1.0, DAQmx_Val_GroupByScanNumber,
                                   self._data, self.num_samples_per_chan*self.num_channels, daq.byref(self.read), None)
            elif self.cha_type[0] is "output":
                self.WriteAnalogF64(self._data.shape[0], 0, DAQmx_Val_WaitInfinitely, DAQmx_Val_GroupByChannel,
                                    self._data, daq.byref(self.read), None)
            if self.data_rec is not None:
                for data_rec in self.data_rec:
                    data_rec.send(self._data)

            self._newdata_event.set()
        return 0  # The function should return an integer

    def DoneCallback(self, status):
        print("Done status", status)
        return 0  # The function should return an integer


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
    f = h5py.File(file_name, "w")# open file
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
            f.write(message)# write log to file
    except GeneratorExit:
        print("   closing file \"{0}\".".format(file_name))
        f.close()  # close file


def data(channels=1):
    '''generator yield next chunk of data for output'''
    # generate all stimuli
    data = list()
    for ii in range(3):
        t = np.arange(0, 1, 1.0 / max(1000.0 ** ii, 100))
        tmp = np.tile(0.2 * np.sin(5000 * t).astype(np.float64), (channels, 1)).T
        data.append(np.ascontiguousarray(tmp)) # `ascont...` necessary since `.T` messes up internal array format
    count = 0  # init counter
    try:
        while True:
            count += 1
            print("{0}: generating {1}".format(count, data[(count-1) % len(data)].shape))
            yield data[ (count-1) % len(data)]
    except GeneratorExit:
        print("   cleaning up dategen.")

if __name__ == "__main__":
    taskAO = IOTask(cha_name=["ao0", "ao1"])
    taskAI = IOTask(cha_name=["ai0", "ai1", "ai2", "ai3"])

    taskAI.data_rec = [plot(), save("test/test.h5", channels=4)]  # sould be iterable...

    taskAO.data_gen = data(channels=2)  # generator function that yields data upon request
    # Connect AO start to AI start
    taskAO.CfgDigEdgeStartTrig("ai/StartTrigger", DAQmx_Val_Rising)

    # Arm the AO task
    # It won't start until the start trigger signal arrives from the AI task
    taskAO.StartTask()

    # Start the AI task
    # This generates the AI start trigger signal and triggers the AO task
    taskAI.StartTask()

    print("Presenting/Acquiring 10 * 10000 samples in continuous mode.")
    time.sleep(7.1)
    # for _ in range(10):
    #     data = taskAI.get_data(timeout=2)
    #     ax.plot(data[:1000])
    #     plt.pause(0.0001)
    taskAO.StopTask()
    taskAI.StopTask()
    taskAO.ClearTask()
    taskAI.ClearTask()
    # properly close callbacks (e.g. flush data to disk and close file)
    taskAO.stop()
    taskAI.stop()
