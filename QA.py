from Segmentation2 import segmentation, plotSegmentationAndRejection
from readFromROOT import getVarNames, readFromROOT, getNamesAllTProfile
from outlierDetector import outlierDetector
from plotRejection import plotOutlier, appendRunInfo

import matplotlib.pyplot as plt
import argparse
import numpy as np
from multiprocessing.pool import Pool
from functools import partial
import argparse
import pyfiglet

def segmentAndReject(runs, x, xerr, pen=1, min_size=10, gamma=None, stdRange=5, maxIter=100, useJMLR=False, useMAD=False, weights=None, segmentOnce=False, **kwargs):
    if useJMLR:
        print('Execution with JMLR')
    else:
        print('Execution with pen = %g' % pen)
    runs_copy = np.copy(runs)
    x_copy = np.copy(x)
    xerr_copy = np.copy(xerr)

    runsRejected = []
    reasonsRejected = []

    for i in range(maxIter):
        if i > 0 and segmentOnce:
            result = np.searchsorted(runs_copy, edgeRuns).tolist()
        else:
            result = segmentation(pen=pen, min_size=min_size, signal=x_copy, gamma=gamma, removeLastRun=True, useJMLR=useJMLR, **kwargs)
            edgeRuns = runs_copy[result]
        runRj, reasonRj, mean, std = outlierDetector(runs_copy, x_copy, xerr_copy, result, stdRange=stdRange, useMAD=useMAD, weights=weights)

        if runRj.shape[0] == 0:
            break
        runsRejected.append(runRj)
        reasonsRejected.append(reasonRj)

        idRejected = np.searchsorted(runs_copy, runRj)

        runs_copy  = np.delete(runs_copy, idRejected)
        x_copy     = np.delete(x_copy, idRejected, axis=0)
        xerr_copy  = np.delete(xerr_copy, idRejected, axis=0)
        weights = np.delete(weights, idRejected, axis=0)

    if len(runsRejected) > 0:
        runsRejected = np.concatenate(runsRejected)
        reasonsRejected = np.vstack(reasonsRejected)
    else:
        runsRejected = np.array(runsRejected)
        reasonsRejected = np.array([[False]*x.shape[1]])

    return runsRejected, reasonsRejected, mean, std, edgeRuns

def writeBadRuns(runsRejected, reasonsRejected, varNames, filename, noReasons):
    varNames = np.array(varNames)
    with open(filename, 'w') as f:
        # print runs in increasing order
        id = np.argsort(runsRejected)
        for run, reason in zip(runsRejected[id], reasonsRejected[id]):
            if noReasons:
                f.write('%d\n' % run)
            else:
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
    parser.add_argument('-v', '--varNames', help='Txt files with all the variable names for QA. If it is not set, it will read ALL TProfiles in the ROOT file.')
    parser.add_argument('-e', '--element', default='??+??', help='Element of your reaction')
    parser.add_argument('-s', '--sNN', default='??', help='Beam energy')
    parser.add_argument('-rr', '--rejectionRange', type=float, default=5, help='The factor of SD range beyon which a run is rejected (default: %(default)s)')
    parser.add_argument('-pr', '--plotRange', type=float, default=10, help='The factor of SD of all good runs in the QA plot (default: %(default)s)')
    parser.add_argument('-ms', '--minSize', type=int, default=10, help='Minimum number of runs in a segment (default: %(default)s)')
    parser.add_argument('--genPDF', action='store_true', help='When used, QA plots will be stored with name <varName>.pdf')
    parser.add_argument('--batch', action='store_true', help='Batch mode. Plots won\'t appear throught x-11 terminal')
    parser.add_argument('--allRunID', action='store_true', help='When used, Run ID of EVERY SINGLE RUN is shown on QA plots. May not be suitable if you have tones of runs.')
    parser.add_argument('--pseudoID', action='store_true', help='Show run ID in ascending order of apparence from 0 instead of the STAR formated run ID')
    parser.add_argument('-p', '--pen', nargs='+', type=float, default=[0.5, 1., 2., 5., 9.], help='(list of) penality for segmentation code to try. (default: %(default)s)')
    parser.add_argument('-c', '--cores', type=int, default=5, help='Number of available cores. (default: %(default)s)')
    parser.add_argument('-it', '--maxIter', type=int, default=5, help='Maximum iterations. (default: %(default)s)')
    parser.add_argument('--JMLR', action='store_true', help='Determine number of change points with heristics from JMLR paper (Section 3.3.2 of https://www.jmlr.org/papers/volume20/16-155/16-155.pdf). Enabling it will disable --cores and --pen flag as it only uses one core.')
    parser.add_argument('--MAD', action='store_true', help='Use Median Absolute Deviation instead of standard deviation. Formula follos that 1.48*MAD=STD assuming Normal distribution.')
    parser.add_argument('-he', '--hideEdgeRuns', action='store_true', help='Hide run numbers on segment edge')
    parser.add_argument('-w', '--weights', choices=['None', 'invErr', 'entries'], default='entries', help='Weighting factor for each run when segment statistics are calculated. (default: %(default)s)')
    parser.add_argument('-nr', '--noReasons', action='store_true', help='Do not print rejection reasons on output')
    parser.add_argument('-pg', '--plotGood', action='store_true', help='Plot QA plots again, but only with good runs')
    parser.add_argument('-m', '--mapping', help='If x-axis of TProfile does not corresponds to STAR run ID, you can supply a file that translate bin low edge to STAR ID')
    parser.add_argument('-so', '--segmentOnce', action='store_true', help='Only run segmentation algorithm once. You can still iterate, but the segment edges will remain unchanged in each iteration')


    args = parser.parse_args()
    if args.JMLR:
        print('Using JMLR to determine segmentation penality. Only use 1 core')
        args.cores = 1
        args.pen = [1]

    # read data from file
    print('Reading TProfile from %s' % (args.input))
    if args.varNames is None:
        varNames = getNamesAllTProfile(args.input)
    else:
        varNames = getVarNames(args.varNames)
    print('Name of the TProfile being read:')
    print('\n'.join(varNames))
    if args.varNames is None:
        print('If you want to exclude some TProfiles, copy the names of the required TProfiles, put them in a text file and put the name of the text file in the argument of this script as -v <filename>')
    else:
        print('Those are the names of TProfiles in %s' % args.varNames)
    print('*'*100)
    runs, x, xerr, x_mean, x_std, counts = readFromROOT(args.input, varNames, args.mapping)

    # calulate weights of each runs
    weights = None
    if args.weights == 'None':
        weights = np.ones(x.shape)
    elif args.weights == 'invErr':
        # check for zero uncertainty
        id = np.where(xerr==0)
        if id[0].shape[0] > 0:
            print('Errorbar size of 0 is found on')
            for i, j in zip(id[0], id[1]):
                print('Run %d on variable %s' % (runs[i], varNames[j]))
            raise Exception('Cannot use invErr as weight if any of the errorbar size is zero')
        weights = np.array(1/xerr)
    elif args.weights == 'entries':
        weights = counts
    else:
        raise Exception('Did not recognize weight option ' + args.weights)

    # begin run segmentation and rejection
    print('Executing run QA')
    runsRejected = reasonsRejected = mean = std = edgeRuns = None
    with Pool(args.cores) as pool:
        # run different penalty setting on different cores
        for ruj, rej, me, st, ed in pool.imap_unordered(partial(segmentAndReject, runs, x, xerr, useJMLR=args.JMLR, useMAD=args.MAD,
                                                                min_size=args.minSize, stdRange=args.rejectionRange, maxIter=args.maxIter,
                                                                weights=weights, segmentOnce=args.segmentOnce), 
                                                        args.pen): 
            # choose penalty that rejectes the most number of runs
            if runsRejected is None or len(ruj) > len(runsRejected):
                runsRejected, reasonsRejected, mean, std, edgeRuns = ruj, rej, me, st, ed

    # write result to text file
    print('Writing bad runs to %s' % args.output)
    writeBadRuns(runsRejected, reasonsRejected, varNames, args.output, args.noReasons)

    # plot every observable
    statSummary = ''
    print('Plot QA result.')
    for xcol, errcol, highlight, mcol, stdcol, globalMean, globalStd, ytitle, coun in zip(x.T, xerr.T, reasonsRejected.T, mean.T, std.T, x_mean, x_std, varNames, counts.T):
        fig, ax = plt.subplots(figsize=(15, 5))
        statSummary = plotOutlier(ax, fig, runs, xcol*globalStd + globalMean, #convert normalized values to real values 
                                   errcol*globalStd, runsRejected, edgeRuns, highlight, 
                                   mcol*globalStd + globalMean, stdcol*globalStd, ytitle, args.allRunID,
                                   args.plotRange, args.rejectionRange, args.pseudoID, 
                                   not args.hideEdgeRuns, 'MAD' if args.MAD else 'RMS', coun)
        appendRunInfo(ax, fig, args.element, args.sNN)
        plt.tight_layout()
        if args.genPDF:
            plt.savefig(ytitle + '.pdf')
    if not args.batch:
        print('Close all the plots to continue')
        plt.show()

    if args.plotGood:
        print('Plot QA result wight Just good runs.')
        idRejected = np.searchsorted(runs, runsRejected)
        for xcol, errcol, highlight, mcol, stdcol, globalMean, globalStd, ytitle in zip(x.T, xerr.T, reasonsRejected.T, mean.T, std.T, x_mean, x_std, varNames):
            fig, ax = plt.subplots(figsize=(15, 5))
            plotOutlier(ax, fig, np.delete(runs, idRejected), np.delete(xcol, idRejected)*globalStd + globalMean, #convert normalized values to real values 
                         np.delete(errcol, idRejected)*globalStd, [], edgeRuns, highlight, 
                         mcol*globalStd + globalMean, stdcol*globalStd, ytitle, args.allRunID,
                         args.plotRange, args.rejectionRange, args.pseudoID, not args.hideEdgeRuns, 'MAD' if args.MAD else 'RMS')
            appendRunInfo(ax, fig, args.element, args.sNN)
            plt.tight_layout()
            if args.genPDF:
                plt.savefig(ytitle + '.good.pdf')
        if not args.batch:
            print('Close all the plots to continue')
            plt.show()


    print('*'*100)
    print('%d runs rejected' % runsRejected.shape[0])
    print(statSummary)
    print('*'*100)

