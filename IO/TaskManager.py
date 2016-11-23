from Task import *


class TaskManager():

    def __init__(self, input_task, output_task):
        self.t_ai = input_task  # analog input task
        self.t_ao = output_task  # analog output task

    def prepare(self):
        # init callbacks

        # fill up AO buffer

        # Connect AO start to AI start
        self.t_ao.CfgDigEdgeStartTrig("ai/StartTrigger", DAQmx_Val_Rising)
        # Arm the AO task: It won't start until the start trigger signal arrives from the AI task
        self.t_ao.StartTask()

    def start(self):
        # Start the AI task: This generates the AI start trigger signal and triggers the AO task
        self.t_ai.StartTask()

    def stop(self):
        self.t_ao.StopTask()
        self.t_ai.StopTask()
        # properly close callbacks (e.g. flush data to disk and close file)
        self.t_ao.stop()
        self.t_ai.stop()

    def __del__(self):
        self.stop()
        self.t_ao.ClearTask()
        self.t_ai.ClearTask()


if __name__ == "__main__":
    t_ao = Task(cha_name=["ao0", "ao1"])
    t_ai = Task(cha_name=["ai0", "ai1", "ai2", "ai3"])
    num_input_chan = 4
    num_output_chan = 2

    # register all callbacks
    t_ai.data_rec = [plot(), save("../test/test.h5", channels=num_input_chan), log("../test/log.txt")]  # sould be iterable...

    stim, stim_order_random = load_stim(num_output_chan)
    t_ao.data_gen = data(stim)  # generator function that yields data upon request

    task_man = TaskManager(input_task=t_ai, output_task=t_ao)
    task_man.prepare()
    task_man.start()

    # run acquisition
    print("Presenting/Acquiring 10 * 10000 samples in continuous mode.")
    time.sleep(10.1)
