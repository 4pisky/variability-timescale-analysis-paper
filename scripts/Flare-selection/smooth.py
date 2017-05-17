import glob
import os

import numpy
import numpy as np
import pylab


def smooth(x,window_len=24,window='flat'):
    """smooth the data using a window with requested size.

    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal
    (with the window size) in both ends so that transient parts are minimized
    in the begining and end part of the output signal.

    input:
        x: the input signal
        window_len: the dimension of the smoothing window; should be an odd integer
        window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
            flat window will produce a moving average smoothing.

    output:
        the smoothed signal

    example:

    t=linspace(-2,2,0.1)
    x=sin(t)+randn(len(t))*0.1
    y=smooth(x)

    see also:

    numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
    scipy.signal.lfilter

    TODO: the window parameter could be the window itself if an array instead of a string
    NOTE: length(output) != length(input), to correct this: return y[(window_len/2-1):-(window_len/2)] instead of just y.
    """

    if x.ndim != 1:
        raise ValueError, "smooth only accepts 1 dimension arrays."

    if x.size < window_len:
        raise ValueError, "Input vector needs to be bigger than window size."


    if window_len<3:
        return x


    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"


    s=numpy.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
    #print(len(s))
    if window == 'flat': #moving average
        w=numpy.ones(window_len,'d')
    else:
        w=eval('numpy.'+window+'(window_len)')

    y=numpy.convolve(w/w.sum(),s,mode='valid')
#    return y
    return y[(window_len/2-1):-(window_len/2)]




files = glob.glob('*')
if not os.path.isdir('smoothed'):
    os.mkdir('smoothed')

for id in files:
    print id
    data = np.loadtxt('{}'.format(id), dtype=float, usecols=(0,3,6), unpack=True)
    time, flux, err = data
    smoothed = smooth(flux)
    pylab.plot(time, smoothed, 'ro')
    perc = np.percentile(smoothed, 3)
    print perc
    
    pylab.show()

    new = open('smoothed/{}.txt'.format(id),'w')
    for i in range(0, time.shape[0]-1):
        if smoothed[i]>perc: 
            data_new = []    
            data_new.append(str(np.float(time[i])))
            data_new.append(str(np.float(smoothed[i])))
            data_new.append(str(err[i]))
            new.write(' '.join(data_new) + '\n')
    new.close()
