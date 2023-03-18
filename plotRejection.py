import warnings
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.font_manager as font_manager
font_dir = ['ttf']
for font in font_manager.findSystemFonts(font_dir):
    font_manager.fontManager.addfont(font)

plt.rcParams['font.family'] = 'Helvetica'

SMALL_SIZE = 18#15
MEDIUM_SIZE = 21#18
BIGGER_SIZE = 24#20

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

def plotOutlier(ax, fig, runs, values, uncert, 
                runsRejected, edgeRuns, highlight,
                means, ranges, ytitle, showAllRunID,
                plotRange, rejectionRange, showPseudoID, 
                showEdgeRuns, devName='RMS', counts=None):
    # edges cover the first and last run
    idEdges = [0] + np.searchsorted(runs, edgeRuns).tolist() + [runs.shape[0]]
    x = np.arange(values.shape[0])

    # rejected data
    # convert run numbers to array id
    idRejected = np.searchsorted(runs, runsRejected)

    # plot ranges
    onlyGoodRuns = np.delete(values, idRejected)
    onlyGoodMean = onlyGoodRuns.mean()
    onlyGoodStd = onlyGoodRuns.std()
    upperBound = onlyGoodMean + plotRange*onlyGoodStd
    lowerBound = onlyGoodMean - plotRange*onlyGoodStd


    ax.fill_between(idEdges, (means-ranges).tolist() + [0], (means+ranges).tolist() + [0], step='post', color='green', alpha=0.5,
                    label='%g-%s  ' % (rejectionRange, devName))
    # 10 SD ranges
    ax.fill_between(idEdges, (means-2*ranges).tolist() + [0], (means+2*ranges).tolist() + [0], step='post', color='yellow', alpha=0.5,
                    label='%s-%s' % (2*rejectionRange, devName))
    # mean of each segment
    ax.step(idEdges, means.tolist() + [0], where='post', linestyle='--')
    if showEdgeRuns:
        xpad = 0.005*x.shape[0]
        ypad = 0.03*(upperBound - lowerBound)
        for edge in idEdges[:-1]:
            ax.annotate(str(runs[edge]) + ' ', xy=(edge, upperBound - ypad), xytext=(edge + xpad, upperBound - ypad), 
                        bbox=dict(boxstyle='square', alpha=0, pad=0),
                        rotation=90, horizontalalignment='left', verticalalignment='top', 
                        size=int(0.8*SMALL_SIZE), arrowprops=dict(arrowstyle='->', ec='black', relpos=(1.01, 1)), zorder=100)
        # label the last edge from the other side
        ax.annotate(str(runs[-1]) + ' ', xy=(idEdges[-1] - 1, upperBound - ypad), xytext=(idEdges[-1] - 1 - xpad, upperBound - ypad), 
                    bbox=dict(boxstyle='square', alpha=0, pad=0),
                    rotation=90, horizontalalignment='right', verticalalignment='top', 
                    size=int(0.8*SMALL_SIZE), arrowprops=dict(arrowstyle='->', ec='black', relpos=(-0.8, 1)), zorder=100)


    # data itself
    ax.errorbar(x, values, yerr=uncert, color='blue', fmt='o', zorder=5)
    if len(runsRejected) > 0:
        ax.errorbar(x[idRejected], values[idRejected], yerr=uncert[idRejected], color='red', markerfacecolor='blue', zorder=6, fmt='o', label='%d badruns' % idRejected.shape[0])
        # highlight rejected data due to THIS condition
        ax.scatter(x[idRejected][highlight], values[idRejected][highlight], color='red', zorder=7, label='%d %s bad' % (np.sum(highlight), ytitle))
        # segment boundaries
    for id in idEdges:
        ax.axvline(id, linestyle='--', color='b')
    # out of bound runs
    idBelow = x[values < lowerBound]
    meanBelow = means[np.searchsorted(edgeRuns, runs[idBelow])]
    for xarr, m in zip(idBelow, meanBelow):
        if lowerBound <= m and m <= upperBound:
            ax.annotate('', xytext=(xarr, m), xycoords='data', 
                        xy=(xarr, lowerBound), textcoords='data', arrowprops=dict(arrowstyle='->', ec='r'), zorder=10)
        else:
            warnings.warn('Mean of a segment lies beyond the plotting region. This can happen if the weighting factor strongly skew the mean/median. You should widen the plot range with -pr <NO STD>')

    idAbove = x[values > upperBound]
    meanAbove = means[np.searchsorted(edgeRuns, runs[idAbove])]
    for xarr, m in zip(idAbove, meanAbove):
        if lowerBound <= m and m <= upperBound:
            ax.annotate('', xytext=(xarr, m), xycoords='data', 
                        xy=(xarr, upperBound), textcoords='data', arrowprops=dict(arrowstyle='->', ec='r'), zorder=10)
        else:
            warnings.warn('Mean of a segment lies beyond the plotting region. This can happen if the weighting factor strongly skew the mean/median. You should widen the plot range with -pr <NO STD>')


    # convert x-axis into run id
    ax.set_ylim(lowerBound, upperBound)
    ax.set_xlim(0, x.shape[0]-1)
    ax.set_ylabel(ytitle)
    ax.set_xlabel('Run ID')
    stat = '%d total runs' % values.shape[0]
    if counts is not None:
        totStats = np.sum(counts)
        rejectedStats = np.sum(counts[idRejected])
        stat = stat + '\nTot events = %d' % totStats
        stat = stat + '\nRejected events = %d' % rejectedStats
        stat = stat + '\nRejection rate = %.2f%%' % (rejectedStats*100/float(totStats))
    ax.text(0.7, 0.01, stat, transform=ax.transAxes)


    if showAllRunID:
        plt.xticks(x)
        ax.set_xticklabels(runs, rotation=90)
    elif not showPseudoID:
        import matplotlib.ticker as ticker
        fig.canvas.draw()
        xLabelID = [int(item.get_text()) for item in ax.get_xticklabels()]
        ax.xaxis.set_major_locator(ticker.FixedLocator(xLabelID)) # can't zoom in due to limitations of matplotlib
        xLabel = [str(runs[id]) if id < runs.shape[0] else id for id in xLabelID]
        ax.set_xticklabels(xLabel, rotation=30, ha='right')
    return stat


def appendRunInfo(ax, fig, ele, energy):
    ax.text(0.1, 0.9, 'STAR', weight='bold', transform=fig.transFigure)
    ax.text(0.15, 0.9, '%s $\sqrt{s_{NN}}$ = %s GeV' % (ele, energy), transform=fig.transFigure)
    ax.legend(bbox_to_anchor=(0.35, 1.0), loc='lower left', ncol=4, frameon=False, columnspacing=0.01, borderpad=0, handletextpad=0.1) 
