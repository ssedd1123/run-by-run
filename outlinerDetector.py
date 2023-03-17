import numpy as np

def outlinerSegment(runs, values, uncert, stdRange=3):
    std = values.std(axis=0)
    mean = values.mean(axis=0)
    idRejectedReason = np.abs(values - mean) > stdRange*std + uncert
    idRejected = np.any(idRejectedReason, axis=1)
    return runs[idRejected], idRejectedReason[idRejected], mean, stdRange*std

def outlinerSegmentMAD(runs, values, uncert, stdRange=3):
    stdRange = stdRange/0.683
    median = np.median(values, axis=0)
    absDev = np.abs(values - median)
    MAD = np.median(absDev, axis=0)
    idRejectedReason = np.abs(values - median) > stdRange*MAD + uncert
    idRejected = np.any(idRejectedReason, axis=1)
    return runs[idRejected], idRejectedReason[idRejected], median, stdRange*MAD

def outlinerDetector(runs, values, uncert, idSegments, useMAD, **kwargs):
    runsRejected = np.array([])
    idRejected = []
    stdRange = []
    mean = []
    if useMAD:
        outSeg = outlinerSegmentMAD
    else:
        outSeg = outlinerSegment

    for lowEdge, upEdge in zip([0] + idSegments, idSegments + [runs.shape[0]]):
        runsRejectedSeg, idRejectedSeg, meanSeg, stdRangeSeg = outSeg(runs[lowEdge:upEdge], values[lowEdge:upEdge], uncert[lowEdge:upEdge], **kwargs)
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


