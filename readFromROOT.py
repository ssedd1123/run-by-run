import uproot
import numpy as np

def getVarNames(varList='QA_variable.list'):
    with open(varList, 'r') as file_:
        qaList = file_.read().rstrip('\n').split('\n')
    return [var.rstrip(' ') for var in qaList]


def readFromROOT(filename, varNames):
    file_ = uproot.open(filename)
    runs = None
    x_normal = []
    x_err_normal = []
    counts = []

    for var in varNames:
        hist = file_[var]
        runs = np.floor(hist.axis(0).centers()).astype(int)
        x = hist.values()
        x_err = hist.errors()#error_mode="s")
        x_counts = hist.counts(False)

        #id = (x_counts > 0) & (x_err > 0)
        #x = x[id]
        #x_err = x_err[id]
        #runs = runs[id]
        #x_counts = x_counts[id]

        x_normal.append(x)
        x_err_normal.append(x_err)
        counts.append(x_counts)

    x_normal = np.array(x_normal).T
    x_err_normal = np.array(x_err_normal).T
    counts = np.array(counts).T

    id = np.all(counts > 0, axis=1) & np.all(x_err_normal > 0, axis=1)
    x_normal = x_normal[id]
    x_err_normal = x_err_normal[id]
    counts = counts[id]
    runs = runs[id]

    std = x_normal.std(axis=0)
    x_mean = x_normal.mean(axis=0)
    x_normal = (x_normal - x_normal.mean(axis=0)) / std
    x_err_normal = x_err_normal/std
    return runs, x_normal, x_err_normal, x_mean, std, counts


if __name__ == '__main__':
    qaList = getVarNames()
    print(qaList)
    print(readFromROOT('qahist.root', qaList))


    

