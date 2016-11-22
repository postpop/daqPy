# -*- coding: utf-8 -*-
import PyDAQmx as daq
from PyDAQmx.DAQmxCallBack import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxFunctions import *

import threading
import time
import numpy as np

from callbacks import *


class Task(daq.Task):
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
            self.num_samples_per_event = 10000  # self.num_samples_per_chan*self.num_channels
            self.CreateAIVoltageChan(self.cha_string, "", DAQmx_Val_RSE, -limits, limits, DAQmx_Val_Volts, None)
            self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, self.num_samples_per_event, 0)
            self.CfgInputBuffer(self.num_samples_per_chan * self.num_channels * 4)
        elif self.cha_type[0] is "output":
            self.num_samples_per_chan = 5000
            self.num_samples_per_event = 5  # determines shortest interval at which new data can be generated
            self.CreateAOVoltageChan(self.cha_string, "", -limits, limits, DAQmx_Val_Volts, None)
            self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Transferred_From_Buffer, self.num_samples_per_event, 0)
            self.CfgOutputBuffer(self.num_samples_per_chan * self.num_channels * 2)
            # ensures continuous output and avoids collision of old and new data in buffer
            self.SetWriteRegenMode(DAQmx_Val_DoNotAllowRegen)
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
                                   self._data, self.num_samples_per_chan * self.num_channels, daq.byref(self.read), None)
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

    def __del__(self):
        self.stop()


if __name__ == "__main__":
    print('test')
    t_ao = Task(cha_name=["ao0", "ao1"])
    t_ai = Task(cha_name=["ai0", "ai1", "ai2", "ai3"])
    num_input_chan = 4
    num_output_chan = 2

    t_ai.data_rec = [plot(), save("../test/test.h5", channels=num_input_chan)]  # sould be iterable...

    # init stim - should be a list of nparrays,
    # assert that:
    #   size is multiple of min_event_samples
    #   right number of channels
    stim = list()
    for ii in range(2):
        t = np.arange(0, 1, 1.0 / max(100.0 ** ii, 10))
        tmp = np.tile(0.2 * np.sin(5000 * t).astype(np.float64), (num_output_chan, 1)).T
        stim.append(np.ascontiguousarray(tmp))  # `ascont...` necessary since `.T` messes up internal array format
    stim_order = False
    t_ao.data_gen = data(stim)  # generator function that yields data upon request

    # Connect AO start to AI start
    t_ao.CfgDigEdgeStartTrig("ai/StartTrigger", DAQmx_Val_Rising)
    # Arm the AO task: It won't start until the start trigger signal arrives from the AI task
    t_ao.StartTask()
    # Start the AI task: This generates the AI start trigger signal and triggers the AO task
    t_ai.StartTask()

    # run acquisition
    print("Presenting/Acquiring 10 * 10000 samples in continuous mode.")
    time.sleep(10.1)

    # for _ in range(10):
    #     data = t_ai.get_data(timeout=2)
    #     ax.plot(data[:1000])
    #     plt.pause(0.0001)
    t_ao.StopTask()
    t_ai.StopTask()
    # properly close callbacks (e.g. flush data to disk and close file)
    t_ao.stop()
    t_ai.stop()
    t_ao.ClearTask()
    t_ai.ClearTask()
