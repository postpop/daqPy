import scipy.io as scio
import numpy as np
import pandas as pd
import os.path
import h5py


def load_ctrl(path):
    return pd.read_table(path,
                         sep='\t',  # tab-delimited
                         header=0)  # coumns names from first row (header)


def save_prot(path, prot):
    prot.to_csv(path,
                sep='\t',     # tab-delimited
                header=0,     # column names as header
                index=False)  # omit row numbers


def load_stim_from_mat(path):
    stim = None
    try:
        f = scio.loadmat(path)
        stim = f["stim"]
    except:
        f = h5py.File(path)
        for name in f:
            print(name)
        stim = f["stim"][0]
    return stim


def load_stim(num_output_chan=1):
    stim = list()
    for ii in range(2):
        t = np.arange(0, 1, 1.0 / max(100.0 ** ii, 10))
        tmp = np.tile(0.2 * np.sin(5000 * t).astype(np.float64), (num_output_chan, 1)).T
        stim.append(np.ascontiguousarray(tmp))  # `ascont...` necessary since `.T` messes up internal array format
    stim_order_random = False
    return stim, stim_order_random


def load_stim_from_ctrl(ctrl, stim_dir=''):
    stim_names = ctrl['stimFileName'].unique()# find unique stim names
    stim = [load_stim_from_mat(os.path.join(stim_dir, stim_name + '.mat')) for stim_name in stim_names]
    return stim, stim_names


if __name__ == "__main__":
    print("TESTING LOAD/SAVE CTRL/PROT FILES")
    ctrl = load_ctrl("../test/ctrl.txt")
    print("field names:")
    print(ctrl.columns)
    print("stim file names:")
    print(ctrl['stimFileName'])
    print(ctrl['stimFileName'].unique())
    print("first row:")
    print(ctrl.iloc[[0]])
    save_prot("../test/ctrl_save.txt", ctrl)

    print("TESTING LOAD STIM FILES")
    stim_dir = os.path.join("..", "test", "stim")
    print(os.path.join(stim_dir, ctrl['stimFileName'][0]))
    stim = load_stim_from_mat(os.path.join(stim_dir, ctrl['stimFileName'][0] + '.mat'))
    print(stim)

    stim_list, stim_names = load_stim_from_ctrl(ctrl, stim_dir)
    print(stim_list)
    print("loaded {0} stimuli.".format(len(stim_list)))
    print(stim_names)
