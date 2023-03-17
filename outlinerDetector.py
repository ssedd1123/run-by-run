import numpy as np

def outlinerSegment(runs, values, uncert, stdRange=3, weights=None):
    mean = np.average(values, axis=0, weights=weights)
    variance = np.average((values - mean)**2, weights=weights, axis=0)
    std = np.sqrt(variance)
    idRejectedReason = np.abs(values - mean) > stdRange*std + uncert
    idRejected = np.any(idRejectedReason, axis=1)
    return runs[idRejected], idRejectedReason[idRejected], mean, stdRange*std

def weightedMedian(values, weights=None):
    if weights is None:
        return np.median(values, axis=0)
    iarr = np.argsort(values, axis=0)
    carr = np.cumsum(weights, axis=0)
    med = []
    for i, c, v in zip(iarr.T, carr.T, values.T):
        idm = i[np.searchsorted(c, 0.5*c[-1])]
        med.append(v[idm])
    return np.array(med)

def outlinerSegmentMAD(runs, values, uncert, weights=None, stdRange=3):
    stdRange = stdRange/0.683
    median = weightedMedian(values, weights)
    absDev = np.abs(values - median)
    MAD = weightedMedian(absDev, weights)
    idRejectedReason = np.abs(values - median) > stdRange*MAD + uncert
    idRejected = np.any(idRejectedReason, axis=1)
    return runs[idRejected], idRejectedReason[idRejected], median, stdRange*MAD

def outlinerDetector(runs, values, uncert, idSegments, useMAD, weights, **kwargs):
    runsRejected = np.array([])
    idRejected = []
    stdRange = []
    mean = []
    if useMAD:
        outSeg = outlinerSegmentMAD
    else:
        outSeg = outlinerSegment

    for lowEdge, upEdge in zip([0] + idSegments, idSegments + [runs.shape[0]]):
        runsRejectedSeg, idRejectedSeg, meanSeg, stdRangeSeg = outSeg(runs[lowEdge:upEdge], values[lowEdge:upEdge], uncert[lowEdge:upEdge], weights=weights[lowEdge:upEdge], **kwargs)
        stdRange.append(stdRangeSeg)
        mean.append(meanSeg)
        if runsRejectedSeg.shape[0] > 0:
            runsRejected = np.append(runsRejected, runsRejectedSeg)
            idRejected.append(idRejectedSeg)
    if runsRejected.shape[0] > 0:
        idRejected = np.vstack(idRejected)
    return runsRejected, idRejected, np.vstack(mean), np.vstack(stdRange)


if __name__ == '__main__':
    runs = np.arange(0, 3e3)
    values = np.array([[1,1]]*runs.shape[0])
    uncert = np.zeros(values.shape)
    print(outlinerDetector(runs, values, uncert, [0, 1000, 2000, runs.shape[0]-1]))
    values[1, 1] = 1e8
    values[1000, 0] = 1e8
    print(outlinerDetector(runs, values, uncert, [0, 1000, 2000, runs.shape[0]-1]))
    print(outlinerDetector(runs, values, uncert, [0, 2000, runs.shape[0]-1]))


