from Segmentation2 import segmentation, plotSegmentationAndRejection
from readFromROOT import getVarNames, readFromROOT
from outlinerDetector import outlinerDetector
from plotRejection import plotOutliner, appendRunInfo

import matplotlib.pyplot as plt
import argparse
import numpy as np
from multiprocessing.pool import Pool
from functools import partial
import argparse
import pyfiglet

def segmentAndReject(runs, x, xerr, pen=1, min_size=10, gamma=None, stdRange=5, **kwargs):
    print('Execution with pen = %g' % pen)
    runs_copy = np.copy(runs)
    x_copy = np.copy(x)
    xerr_copy = np.copy(xerr)

    runsRejected = []
    reasonsRejected = []

    while True:
        result = segmentation(pen=pen, min_size=min_size, signal=x_copy, gamma=gamma, removeLastRun=True, **kwargs)
        runRj, reasonRj, mean, std = outlinerDetector(runs_copy, x_copy, xerr_copy, result, stdRange=stdRange)
        edgeRuns = runs_copy[result]

        if runRj.shape[0] == 0:
            break
        runsRejected.append(runRj)
        reasonsRejected.append(reasonRj)

        idRejected = np.searchsorted(runs_copy, runRj)

        runs_copy  = np.delete(runs_copy, idRejected)
        x_copy     = np.delete(x_copy, idRejected, axis=0)
        xerr_copy  = np.delete(xerr_copy, idRejected, axis=0)


    if len(runsRejected) > 0:
        runsRejected = np.concatenate(runsRejected)
        reasonsRejected = np.vstack(reasonsRejected)
    else:
        runsRejected = np.array(runsRejected)
        reasonsRejected = np.array([[False]*x.shape[1]])

    return runsRejected, reasonsRejected, mean, std, edgeRuns

def writeBadRuns(runsRejected, reasonsRejected, varNames, filename):
    varNames = np.array(varNames)
    with open(filename, 'w') as f:
        for run, reason in zip(runsRejected, reasonsRejected):
            f.write('%d %s\n' % (run, ' '.join(varNames[reason].tolist())))

def printBanner():
    print(u'\u2500' * 100)
    print(pyfiglet.figlet_format('RUN BY RUN QA'))
    print(u'\u2500' * 100)
    print('Run-by-Run QA script for STAR data analysis')
    print('Version 3.0')
    print('Contact: <ctsang@bnl.gov>, <yuhu@bnl.gov>, <ptribedy@bnl.gov>')
    print(u'\u2500' * 100)

#varNames = ['test1', 'test2']
#runs = np.arange(20)
##x = np.concatenate([np.zeros((10, len(varNames))), np.ones((10, len(varNames)))])
#x = np.zeros((runs.shape[0], len(varNames)))
#xerr = np.zeros((runs.shape[0], len(varNames)))
##x[15, 0] = 5

if __name__ == '__main__':
    printBanner()
    parser = argparse.ArgumentParser(description='run-by-run QA program')
    parser.add_argument('-i', '--input', required=True, help='ROOT files that contains all the QA TProfile')
    parser.add_argument('-o', '--output', required=True, help='Filename for the output text file with all the bad runs')
    parser.add_argument('-v', '--varNames', required=True, help='Txt files with all the variable names for QA')
    parser.add_argument('-e', '--element', required=True, help='Element of your reaction')
    parser.add_argument('-s', '--sNN', required=True, help='Beam energy')
    parser.add_argument('-rr', '--rejectionRange', type=float, default=5, help='The factor of SD range beyon which a run is rejected (default: %(default)s)')
    parser.add_argument('-pr', '--plotRange', type=float, default=10, help='The factor of SD of all good runs in the QA plot (default: %(default)s)')
    parser.add_argument('-ms', '--minSize', type=int, default=5, help='Minimum number of runs in a segment (default: %(default)s)')
    parser.add_argument('--genPDF', action='store_true', help='When used, QA plots will be stored with name <varName>.pdf')
    parser.add_argument('--allRunID', action='store_true', help='When used, Run ID of EVERY SINGLE RUN is shown on QA plots. May not be suitable if you have tones of runs.')
    args = parser.parse_args()

    # read data from file
    print('Reading TProfile from %s and variable names from %s' % (args.input, args.varNames))
    varNames = getVarNames(args.varNames)
    runs, x, xerr, x_mean, x_std = readFromROOT(args.input, varNames)

    # begin run segmentation and rejection
    print('Executing run QA')
    runsRejected = reasonsRejected = mean = std = edgeRuns = None
    with Pool(5) as pool:
        # run different penalty setting on different cores
        for ruj, rej, me, st, ed in pool.imap_unordered(partial(segmentAndReject, runs, x, xerr, 
                                                                min_size=args.minSize, stdRange=args.rejectionRange), 
                                                        [0.5, 1, 2, 5, 9]): 
            # choose penalty that rejectes the most number of runs
            if runsRejected is None or len(ruj) > len(runsRejected):
                runsRejected, reasonsRejected, mean, std, edgeRuns = ruj, rej, me, st, ed

    # write result to text file
    print('Writing bad runs to %s' % args.output)
    writeBadRuns(runsRejected, reasonsRejected, varNames, args.output)

    # plot every observable
    print('Plot QA result.')
    for xcol, errcol, highlight, mcol, stdcol, globalMean, globalStd, ytitle in zip(x.T, xerr.T, reasonsRejected.T, mean.T, std.T, x_mean, x_std, varNames):
        fig, ax = plt.subplots(figsize=(15, 5))
        plotOutliner(ax, fig, runs, xcol*globalStd + globalMean, #convert normalized values to real values 
                     errcol*globalStd, runsRejected, edgeRuns, highlight, 
                     mcol*globalStd + globalMean, stdcol*globalStd, ytitle, args.allRunID,
                     args.plotRange, args.rejectionRange)
        appendRunInfo(ax, fig, args.element, args.sNN)
        plt.tight_layout()
        if args.genPDF:
            plt.savefig(ytitle + '.pdf')
        plt.show()


