# daq
- uses [PyDAQmx](https://github.com/clade/PyDAQmx) to interact with cards
- currently supports analog input and output
- uses generator/coroutines for 
    - generating data for output 
    - processing recorded data

# test output buffering
- what happens if I don't fill up to buffer in the callback? does the callback get called until the buffer is full? 

# TODO
[x] add saving data
[x] make multi channel
[-] properly implement data generation
[ ] add logging
[ ] add camera 

## useful links
[PyDAQmx docs](https://pythonhosted.org/PyDAQmx/index.html)
[DAQmx C API reference](http://zone.ni.com/reference/en-XX/help/370471W-01/TOC3.htm)
[phy - possible GUI](https://github.com/kwikteam/phy)
[useful wrapper](https://github.com/sjfleming/MultiChannelAnalogIO/blob/master/MultiChannelAnalogIO.py)
[another (not so) useful wrapper](https://github.com/frejanordsiek/pynidaqutils)
[examples from scipy cookbook](http://scipy-cookbook.readthedocs.io/items/Data_Acquisition_with_NIDAQmx.html)