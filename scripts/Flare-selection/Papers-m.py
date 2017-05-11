import pylab
import glob, os
import logging
from operator import not_
import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from astropy.stats.funcs import sigma_clip
from collections import namedtuple
import matplotlib.gridspec as gridspec
import math
import optparse
from scipy.optimize import curve_fit



class std_keys():
    """Standardized keys"""
    id='id'
    time='time'
    time_units='time_units'
    flux='flux'
    flux_err='flux_err'
    flux_units='flux_units'
    deltas='deltas'
    slopes='slopes'


class GBI_keys():
    mjd = 'MJD'
    flux_5ghz = 'Flux @ 5GHz'
    flux_5ghz_err = '10% flux error @ 5GHz '
 
    col_hdrs = (mjd, flux_5ghz,
                 flux_5ghz_err)


def read_gbi_datafile(path):
    """
    Loads GBI data from file at ``path``.

    Converts it to a dictionary of numpy arrays - one entry for each column.
    The dictionary keys are defined in class GBI_keys (see above).
    """
    logger.debug("Reading: " + path )
    with open(path) as f:
        rdr = csv.reader(f, delimiter=(' '), skipinitialspace='False')
        datarows = [row for row in rdr if len(row)]
	
    for i, p in enumerate(datarows):
        datarows[i] = [ float(j) for j in p]
	
    #remove data where flux is < 0 (from the added fake noise):
    #def is_bad_data(r):
	#if r[1]<0.0:
    #        return True
    #    else:
    #        return False

#    datarows = [r for r in datarows if not is_bad_data(r)]
     #Sort the data by x value:
    datarows = [r for r in datarows]
    #Sort the data by x value:
    datarows.sort(key = lambda pair: pair[0])
    data_vecs = zip(*datarows)
    data_vecs = [np.asarray(v) for v in data_vecs]

    if not (len(data_vecs) == len(GBI_keys.col_hdrs)):
        logging.warning("Datafile "+path+" has header / col mismatch")
    dataset = dict(zip(GBI_keys.col_hdrs, data_vecs))
    return dataset

def standardize_gbi_dataset(dset):
    """
    Change the keys of a dataset dictionary, to match what we've previously
    found in non-GBI files.
    Add 'time_units' and 'flux_units' entries, set these to 'MJD', 'Jy'
    then replace the keys 'MJD' -> `time`, 'Jy'->'flux'.
    """
    # NB, have chosen to use the 8GHz flux values.
    flux, err = GBI_keys.flux_5ghz, GBI_keys.flux_5ghz_err
    dset[std_keys.time_units]=GBI_keys.mjd
    dset[std_keys.time]=dset.pop(GBI_keys.mjd)
    dset[std_keys.flux_units]='Flux density (Jy)'
    dset[std_keys.flux]=dset.pop(flux)
    dset[std_keys.flux_err]=dset.pop(err)
    return dset

def plot_lightcurve(dset, ax):
    """Add a basic lightcurve errorbar-plot to a matplotlib axis"""
    id = dset[std_keys.id]
    ax.errorbar(dset[std_keys.time], dset[std_keys.flux],
                dset[std_keys.flux_err],
                fmt='o', color='#A4A4A4', markeredgecolor='None')
    ax.set_xlabel(dset[std_keys.time_units], fontsize=16)
    ax.set_ylabel(dset[std_keys.flux_units], fontsize=17)
    pylab.xticks(size=16,)
    pylab.yticks(size=16,)


##C6C6C6 grey1
def get_sigma_clipped_fluxes(raw_fluxes):
    """
    Uses the astropy sigma_clip function to try and get rid of outliers.

    ( https://astropy.readthedocs.org/en/stable/api/astropy.stats.sigma_clip.html )

    Returns a masked array where all outlier values are masked.
    """

    # First we try to run sigma clip with the defaults - hopefully this will
    # iterate until it converges:
    clipped_fluxes = sigma_clip(raw_fluxes, iters=None)
    # If it fails (number of unmasked values <3),
    # then we just accept the result from a single iteration:
    if len(clipped_fluxes.compressed())<3:
        logger.warning("Sigma clipping did not converge, "
                            "using single iteration")
        clipped_fluxes= sigma_clip(raw_fluxes, iters=1)
    return clipped_fluxes




#Create a namedtuple structure to hold timestamps marking flare begins / ends.
Flare = namedtuple('Flare', 'trigger rise peak fall')

def find_flares(dset, zeropoint, sigma):
    """
    Find flares in ``dset`` that peak more than 5*sigma above the zeropoint
    Returns a list of ``Flare`` namedtuple objects.
    """
    id_a = d[std_keys.id]
    id = id_a.split('.txt')[0]
    rise_threshold = zeropoint + 5*sigma
    fall_threshold = zeropoint + 1*sigma
    fluxes = dset[std_keys.flux]
    flux_errs = dset[std_keys.flux_err]
    assert flux_errs.shape == fluxes.shape
    print "Lengths:", len(flux_errs), len(fluxes)

    def find_next_trigger(start):
        for idx, flux in enumerate(fluxes[start:], start):
            if flux > rise_threshold:
                return idx
        return None

    def find_next_fall(start):
        for idx, flux in enumerate(fluxes[start:], start):
            err = flux_errs[idx]
            if (flux - err )< fall_threshold:
                return idx
        return None

    def find_rise_start(trigger):
        #step backwards until sunk
        for idx, flux in list(enumerate(fluxes[:trigger]))[::-1]:
            err = flux_errs[idx]
            if (flux - err )< fall_threshold:
                return idx
        return None
          
        
    markers = []   
    idx=0
    start_pos = find_next_fall(idx)
    # print "Found a start"
    times = dset[std_keys.time]
    if not os.path.isdir('results_MIN'):
	    os.mkdir('results_MIN')
    if not os.path.isdir('results_MIN/{}'.format(id)):
	    os.mkdir('results_MIN/{}'.format(id))   
    if not os.path.isdir('results_MIN/measurements'):
        os.mkdir('results_MIN/measurements')    
    R = open('results_MIN/measurements/{}_rise_parameters.txt'.format(id), 'w')
    D = open('results_MIN/measurements/{}_decline_parameters.txt'.format(id), 'w')
    D.write('#Name Slope(1/day) Slope_err(1/day) Chi2 Fmax(Jy) NegativePts CountR(NR) Match'+'\n')   
    R.write('#Name Slope(1/day) Slope_err(1/day) Chi2 Fmax(Jy) NegativePts CountD(ND) Match'+'\n')  
    
    countR = 0
    countD = 0
    match = 0
    while start_pos is not None:
        match = match + 1
        trigger = find_next_trigger(start_pos)
        #print "Triplet:", len(markers)
        #print "Trigger at time", times[trigger]
        if trigger is not None:
            fall = find_next_fall(trigger+1)
        else:
            fall = None
        start_pos = fall

        if fall is not None:
        #Generate a mask leaving only this trigger-->fall interval, to find peak
            mask = np.zeros_like(fluxes)
            mask[:trigger]=True
            mask[fall:]=True
            masked = np.ma.MaskedArray(fluxes)
            masked.mask = mask
            peak_val = masked.max()
            peak_idx = np.where(masked==peak_val)[0]
            #print peak_idx
            rise = find_rise_start(trigger)
            flare = Flare(trigger,rise, peak_idx[0], fall)
            
            f_all = dset[std_keys.flux]
            f_all_err = dset[std_keys.flux_err]
            t_all = dset[std_keys.time]

            # For each selected flare fit exponential function, save snapshots of each flare with the ID of a trigger time (SOURCE_TriggerTime.png)
            # Shift time values so that fmax is at t=0.
            t_all_shifted = t_all - t_all[peak_idx[0]]
            # set range of times for rise phase (tr) (to peak flux time) and
            # decline (td) (from peak flux time)
            rise_idx = np.where(np.logical_and(t_all_shifted<=0, t_all_shifted>= t_all_shifted[rise]))
            t_rise = t_all_shifted[rise_idx]
            f_rise = f_all[rise_idx]
            f_rise_err = f_all_err[rise_idx]
            
            decline_idx =  np.where(np.logical_and(t_all_shifted>=0, t_all_shifted<= t_all_shifted[fall])) 
            t_dec = t_all_shifted[decline_idx]
            f_dec = f_all[decline_idx]
            f_dec_err = f_all_err[decline_idx]

            # Estimate the base of the lightcurve as a 1st percentile of the flux measurements & subtract it from the data
            base = np.percentile(f_all,1)
            f_allx = f_all - base 
            min_all = abs(np.min(f_allx))
            f_risex = f_rise - base + min_all
            f_decx = f_dec - base + min_all
            f_allx = f_all - base  + min_all
            fmax = f_all[peak_idx[0]] - base + min_all

            ## Try to overplot median
            clipped_fluxes = get_sigma_clipped_fluxes(fluxes)
            clipped_median = np.percentile(fluxes, 10)
            med = clipped_median - base + min_all
            ###

            fig = plt.figure()
            ax  = fig.add_subplot(111)
            fig.set_size_inches(10.,6.)
            ax.errorbar(t_dec, np.log(f_decx), xerr=None, yerr=f_dec_err/f_decx,  linestyle='None', ecolor="Black", elinewidth=1)
            ax.errorbar(t_rise, np.log(f_risex), xerr=None, yerr=f_rise_err/f_risex,  linestyle='None', ecolor="Black", elinewidth=1)
            ax.plot(t_all_shifted, np.log(f_allx), 'ks') 
#color= '#EAEAF1', linestyle='None')
            ax.plot(t_dec, np.log(f_decx), marker='s', color= 'Gold', linestyle='None')
            ax.plot(t_rise, np.log(f_risex), marker='s', color= 'Lime', linestyle='None')
            line_pars = dict(linestyle='--', color='#33C03D', linewidth = 2)
            ax.axhline(np.log(med), **line_pars)

            values_rise = []
            values_decline = []

            try:
                
                t_min_idx = np.argmin(t_rise)
                t_min = t_rise[t_min_idx]
                f_t_min = f_rise[t_min_idx]
                #print "Rise params init", init_rise_pars
                f_rise = f_rise - base + min_all
                pos = f_rise>0
                neg = f_rise<=0
                f_neg = f_rise[neg] 
                negnb = f_neg.shape[0]
                f_rise = f_rise[pos]
                f_rise_err = f_rise_err[pos]
                t_rise = t_rise[pos]
           
                rise_fit_pars, rise_fit_cov = curve_fit(log_lin, t_rise, np.log(f_rise), sigma=f_rise_err/f_rise, maxfev=800)
                rise_fit_pars_err = np.sqrt(np.diag(rise_fit_cov))              
                
                #calc reduced chi squared chi2r for rise phase:
                chi2 = 0
                for i in range(0, t_rise.shape[0]):
                    R_i = log_lin(t_rise[i], rise_fit_pars[0], rise_fit_pars[1])
                    d_i = np.log(f_rise[i])
                    var_i = (f_rise_err[i]*f_rise_err[i])/(f_rise[i] * f_rise[i])
                    chi2_i = ((d_i - R_i)*(d_i - R_i))/var_i
                    chi2 += chi2_i
                N = t_rise.shape[0]-2.0-1.0    
                chi2r = chi2/N    

                countR = countR + 1     
                ax.plot(t_rise, log_lin(t_rise, *rise_fit_pars), 'b-', label='Rise: {:.6f}$\pm${:.6f},\nChi2: {:.6f}, \nNR: {}'.format(rise_fit_pars[0], rise_fit_pars_err[0], chi2r, countR))
                plt.legend(numpoints=2, loc=0, prop={'size':18})

                
                SR = rise_fit_pars[0]
                SRerr = rise_fit_pars_err[0]               
                SR = np.float(SR)
                values_rise.append(str(SR))
                SRerr = np.float(SRerr)
                values_rise.append(str(SRerr)) 
                chi2r = np.float(chi2r)
                values_rise.append(str(chi2r))
                fmax = np.float(fmax)
                values_rise.append(str(fmax))
                negnb = np.float(negnb)
                values_rise.append(str(negnb))
                values_rise.append(str(countR)) 
                values_rise.append(str(match))

                print "Rise params fit:", rise_fit_pars, 'Rise params fit err:', rise_fit_pars_err, 'Peak', fmax
                R.write(id.split('.txt')[0]+'\t'+'\t'.join(values_rise) + '\n')
                     

            except Exception as e:
                print "Rise fit failed:"
                print e
                pass
            
            
            try:
               
                t_max_idx = np.argmax(t_dec)
                t_max = t_dec[t_max_idx]
                f_t_max = f_dec[t_max_idx]
                f_dec = f_dec - base + min_all
                pos = f_dec>0
                neg = f_dec<=0
                f_neg = f_dec[neg] 
                negnb = f_neg.shape[0]
                f_dec = f_dec[pos]
                f_dec_err = f_dec_err[pos]
                t_dec = t_dec[pos]

                decline_fit_pars, decline_fit_cov = curve_fit(log_lin, t_dec, np.log(f_dec), sigma=f_dec_err/f_dec, maxfev=800)
                decline_fit_pars_err = np.sqrt(np.diag(decline_fit_cov))  
   
                #calc reduced chi squared chi2r for decline phase Dchi2r:
                chi2 = 0             
                for i in range(0, t_dec.shape[0]):
                    D_i = log_lin(t_dec[i], decline_fit_pars[0], decline_fit_pars[1])
                    d_i = np.log(f_dec[i])
                    var_i = (f_dec_err[i]*f_dec_err[i])/(f_dec[i]*f_dec[i])
                    chi2_i = ((d_i - D_i)*(d_i - D_i))/var_i
                    chi2 += chi2_i
                N = t_dec.shape[0]-2.0-1.0    
                chi2r = chi2/N 
                
                countD = countD + 1
                ax.plot(t_dec, log_lin(t_dec, *decline_fit_pars), 'r-', label='Dec: {:.6f}$\pm${:.6f},\nChi2: {:.6f}, \nND: {}'.format(decline_fit_pars[0], decline_fit_pars_err[0], chi2r, countD)) 
                plt.legend(numpoints=2, loc=0, prop={'size':18})
  
                SD = decline_fit_pars[0]
                SDerr = decline_fit_pars_err[0]
                SD = np.float(SD)
                values_decline.append(str(SD))
                SDerr = np.float(SDerr)
                values_decline.append(str(SDerr))
                chi2r = np.float(chi2r)
                values_decline.append(str(chi2r))                
                fmax = np.float(fmax)
                values_decline.append(str(fmax)) 
                negnb = np.float(negnb)
                values_decline.append(str(negnb))
                values_decline.append(str(countD))
                values_decline.append(str(match))

                D.write(id.split('.txt')[0]+'\t'+'\t'.join(values_decline) + '\n')  
                print "Dec params fit:", decline_fit_pars, 'Dec params fit err:', decline_fit_pars_err, 'Peak', fmax
                        
                                
            except Exception as e:
                print "Decline fit failed:"
                print e
                pass                  
                   
            plt.xlabel('Time [days]',fontsize=15)
            plt.ylabel('Flux [Jy]',fontsize=15)
            length = t_all_shifted.shape[0]
            plt.xlim([t_all_shifted[length/4.0], t_all_shifted[length*3.0/4.0]])
            plt.ylim([np.log(f_allx[length/4.0])-0.5, np.log(np.max(f_all))])
            plt.savefig('results_MIN/{}/{}_{}.png'.format(id, id, t_all[flare[0]] ))
            markers.append(flare)
    
    R.close()
    D.close()

    return markers
    

def log_lin(tdata, slope, b):
    return slope * tdata + b



def plot_dataset(d):
    id_a = d[std_keys.id]
    id = id_a.split('.txt')[0]
    times = d[std_keys.time]
    fluxes = d[std_keys.flux]
    flux_errs = d[std_keys.flux_err]
    logger.info('Plotting '+id)
    base = np.percentile(fluxes,1)
    fluxesx = fluxes - base 
    base = base + abs(np.min(fluxesx))


    fig = plt.figure()
    
    # Set up a 3 row plot-grid.
   
    # Use the top 2/3rds for the lightcurve axis
    lightcurve_ax = fig.add_subplot(111)
    # Use the bottom 1/3rd for the histogram axis
    #hist_ax = plt.subplot(gs[2])

    

    #Generate a histogram of the flux values
    hist, bin_edges = np.histogram(fluxes, bins=max(len(fluxes)/20,15), density=True)

    clipped_fluxes = get_sigma_clipped_fluxes(fluxes)

    # Get a mask for the histogram that only shows flux values that are inside
    # the sigma-clipped range
    clip_mask = (( bin_edges[:-1] > clipped_fluxes.min() ) *
                 (bin_edges[:-1] < clipped_fluxes.max() ))

    #Plot the hist of all flux values, in red:
  #  plt.bar(bin_edges[:-1], hist, width=bin_edges[1]-bin_edges[0],
    #        color='r')
    # The overplot the flux values that are inside the sigma-clip range,
    # using the mask
   # plt.bar(bin_edges[clip_mask], hist[clip_mask] , width=bin_edges[1]-bin_edges[0])
    #hist_ax.set_xlabel(dset[std_keys.flux_units])
    #hist_ax.set_ylabel("Relative prob")


    #Now, let's plot the lightcurv
    plot_lightcurve(d, lightcurve_ax)

    # Plot the median value
    median = np.median(fluxes)
    clipped_median = np.percentile(fluxes, 10)
    logger.debug( "Median diff: {}".format( clipped_median - median))
    line_pars = dict(linestyle='--', color='#33C03D', linewidth = 2, label='background')
    lightcurve_ax.axhline(clipped_median, **line_pars)
    #hist_ax.axvline(clipped_median, **line_pars)
    # On the histogram,
    # Overplot a gaussian curve with same median and std dev as clipped data,
    # for comparison. (In yellow)
    #x=np.linspace(hist_ax.get_xlim()[0], hist_ax.get_xlim()[1],1000)
    clipped_std = np.mean(flux_errs)
    logger.debug("Clipped std dev: {}".format(clipped_std))
    clip_pars_norm = norm(clipped_median, clipped_std)
    #hist_ax.plot(x, clip_pars_norm.pdf(x), color='y')

    # What size is a typical errorbar, according to the datafile?
    # (away from the outliers)
    unmasked_errors = flux_errs[~clipped_fluxes.mask]
    typical_error = np.median(unmasked_errors)
    logger.debug("Typical errorbar {}".format(typical_error))
    # Plot a gaussian with std. dev. equal to this errorbar size, for comparison.
    # (in Green)
   # hist_ax.plot(x, norm(clipped_median, typical_error).pdf(x), color='#33C03D')
   # hist_ax.set_xlim(hist_ax.get_xlim()[0], clipped_median+clipped_std*8)

    # Define a 'wobble factor' - how much the data seems to vary, compared to
    # how much we would expect from the formal errorbars:
    wobble_factor = np.ma.std(clipped_fluxes) / typical_error
    logger.debug("Wobble factor due to quiescent wobble / red noise: {}".format(wobble_factor))
    #hist_ax.annotate("Wobble factor: {}".format(wobble_factor),
                 #     xy=(0.7,0.8),
                  #    xycoords='axes fraction')

    wobble_max1 = clipped_median + clipped_std*3
    wobble_max2 = clipped_median + clipped_std*5
    line_pars = dict(linestyle='-', color='#6E7AFA', linewidth = 2, label='$b$+3$\sigma$')
    lightcurve_ax.axhline(wobble_max1, **line_pars)
   # hist_ax.axvline(wobble_max1, **line_pars)
    line_pars = dict(linestyle='-', color='#C40202', linewidth = 2, label='$b$+5$\sigma$')
    lightcurve_ax.axhline(wobble_max2, **line_pars)
    #hist_ax.axvline(wobble_max2, **line_pars)
    lightcurve_ax.legend(numpoints=1, loc=2, prop={'size':18})
   # lightcurve_ax.set_yticks((2.5,3.5, 4.5, 5.5, 6.5, 7.5))
#    lightcurve_ax.set_xticks((2000, 4000, 6000, 8000))
    # Finally, use the sigma-clipped median and std. dev. as
    # zeropoint and noise estimates,
    # and feed them to the flare-finding routine:
    flares = find_flares(d, clipped_median, clipped_std)
    for marker_set in flares:
        #trigger,rise,peak,fall
        marker_list = ('p','^','*','v')
        markerpars = dict(markersize = 8, color='Black')
        for i, m in enumerate(marker_set):
            if m is not None:
                lightcurve_ax.plot(times[m], fluxes[m],
                                   marker = marker_list[i], **markerpars)


    fig.tight_layout()
 #   plt.show()
    plt.close()

    if not os.path.isdir('results_MIN'):
           os.mkdir('results_MIN')
   # if not os.path.isdir('results_MIN/{}'.format(id)):
   #        os.mkdir('results_MIN/{}'.format(id))
    #
    fig.set_size_inches(18.5,10.5)
    fig.savefig('results_MIN/{}/{}_lin-lin.png'.format(id, id), dpi=200)

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG)
    logger = logging.getLogger()
    data_folder = os.path.expanduser('~/Desktop/code-test/data')
#    data_folder = os.path.expanduser('~/Dropbox/Classification/Gogo_Tim/GBI_flarefind')
    datafiles = glob.glob(data_folder+'/*')
    datasets = {}

    for path in datafiles:
        target_id = os.path.basename(path)
        dset = read_gbi_datafile(path)

        dset[std_keys.id]=target_id
        datasets[target_id] = standardize_gbi_dataset(dset)

    # for d in datasets.values()[-1:]:
    for d in datasets.values():
        plot_dataset(d)