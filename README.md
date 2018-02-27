# Variability Timescale Analysis
Supporting code and data for M. Pietka et al. 2017 (https://arxiv.org/abs/1707.04265).
The scripts select individual flaring events from light-curves, measure exponential rise/decline rates and create a set of diagnostic plots, including luminosity vs time-scale and time-scale probability distribution.


## Data 
Individual class directories contain radio light-curves collected from the literature. The column headings in the files are as follows:
- col. 1 - Time (days)
- col. 2 - Flux density (Jy)
- col. 3 - Flux density error (Jy)


Additionally, within some of the individual class directories, the 'GBI' directories contain light-curves downloaded from the GBI database and have the following column headings:

- col. 1 - Mod. Julian Date of observation (JD-2400000.5).
- col. 2 - Local Hour Angle of observation (hours).
- col. 3 - Flux Density in Janskys at  2.25 GHz
- col. 4 - Flux Density in Janskys at  8.3 GHz.
- col. 5 - Spectral index.
- col. 6 - Estimated 1-sigma error of col. 3.
- col. 7 - Estimated 1-sigma error of col. 4.


`target-distances-and-class.txt` gives a list of sources together with distances, observing frequencies and type of the light-curve. In the available sample there are four light-curve types (specified in the 'LC-type' column), each of them processed differently by the flare finder:

- Papers-s -- Pre-selected individual flares, with no information about the background emission.
- GBI-m -- Well sampled light-curves with good background emission information.
- Papers-m -- Light-curves consisting of single or multiple flares with very limited background information.
- GBI-s -- Light-curves with long time-scale flares (mostly AGN), very limited background information, and, some noisy datapoints which required smoothing.

A detailed description of the light-curve types, example plots and details of the processing can be found in Pietka et al. 2017. 

To add a new source to a sample copy the light-curve data into a corresponding class directory and add the source to the 'target-distances-and-class.txt' file with the appropriate 'LC-type' label.

## Automatic flare selection.
In the `scripts` directory run `run_flare_fits.py`. This script automatically selects flares from the light-curves and fits exponential function to rise/decline of each flare. 

Parameters of the fits and diagnostic plots are placed in the `results` directory.

## Scatter and probability distribution plots

```combine_flares_output.py``` processes individual `*.json` parameters files into 'complete_rise' and 'complete_decline' files containing information about the rise/decline rates, errors and peak radio luminosity for each flare.

```
optional arguments:
  -h, --help            show this help message and exit
  -j JSONFILESPATH, --jsonfilespath JSONFILESPATH
                        Directory in which output files (*_flares.json) from
                        flare finder are stored.
  -t TARGETSFILEPATH, --targetsfilepath TARGETSFILEPATH
                        Directory in which target-distances-and-class.txt file
                        is stored.
```

`Luminosity-timescale.py` - luminosity vs rise/decline time of the event figure, based on the 'complete_rise/decline' files.
```
optional arguments:
  -h, --help            show this help message and exit
  -p COMPLETE_MEASUREMENTS, --complete_measurements COMPLETE_MEASUREMENTS
                        Directory in which *complete_rise/decline* files are
                        stored.
```

`Probability-distribution.py` - probability distribution of rise/decline time-scale figure, corrected for the estimated areal densities.

Estimated areal densities, calculated to 0.1 mJy flux density limit, are stored in the `sky-densities.txt` file.

Output files `prob_distribution_table_averaged_X_rise/decline` contain probability distribution tables averaged over a chosen logarithmic time-step `X` (default 0.5)

```
optional arguments:
  -h, --help            show this help message and exit
  -p COMPLETE_MEASUREMENTS, --complete_measurements COMPLETE_MEASUREMENTS
                        Directory in which *complete_rise/decline* files are
                        stored.
  -r SKY_DENSITIES, --sky_densities SKY_DENSITIES
                        Directory in which sky-densities.txt file is stored.
  -s STEP, --step STEP  Logarithmic timestep over which to average the
                        probability tables.
```

