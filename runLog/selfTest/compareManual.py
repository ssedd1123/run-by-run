from prettytable import PrettyTable
import pandas as pd
import numpy as np

def main(result, ref, txt=None):
    refData = pd.read_csv(ref)
    resFullData = pd.read_csv(result, sep='$', header=None, names=['runID', 'reason'], dtype={0: int})
    resData = set(resFullData[resFullData['reason'].isnull() | (resFullData['reason'].str.strip() != '')]['runID'])

    # bad run with critical errors
    # must be listed in desending order of serverity
    # runs that are already critical won't be re-classified as sub-critical.
    groupClassification = [['Critical errors', ['critical error', 'anode cathod trip', 'beam lost']],
                           ['Sub-critical errors', ['tpc sector', 'etof', 'tof']]]


    selectedID = set([])
    for errType, reasons in groupClassification:
        refData[errType] = 'No'
        refData.loc[(refData['Reason1'].isin(reasons)) | (refData['Reason2'].isin(reasons)), errType] = 'Yes'
        refData.loc[refData['runID'].isin(selectedID), errType] = 'No'
        selectedID.update(refData[refData[errType] == 'Yes']['runID'].tolist())

    # there will always be two more implicit classification: Ohter errors and good run
    # good run means nothing note worthy in the shift log
    # other errors mean any error not listed in groupClassification
    refData['Other errors'] = 'No'

    # labels that are still considered good runs
    goodReasons = ['laser', 'cosmic runs']
    # don't classify as bad run if either notnull or reasons are just part of goodReasons
    refData.loc[(refData['Reason1'].notnull() & ~refData['Reason1'].isin(goodReasons)) |  (refData['Reason2'].notnull() & ~refData['Reason2'].isin(goodReasons)), 'Other errors'] = 'Yes'
    refData.loc[refData['runID'].isin(selectedID), 'Other errors'] = 'No'

    # good run if devoid of reasons to be bad
    refData['Good run'] = 'No'
    refData.loc[(refData['Reason1'].isnull()) & (refData['Reason2'].isnull()), 'Good run'] = 'Yes'
    refData.loc[(refData['Reason1'].isin(goodReasons)) | (refData['Reason2'].isin(goodReasons)), 'Good run'] = 'Yes'
    refData.loc[refData['runID'].isin(selectedID), 'Good run'] = 'No'

    # compare with new result
    refData['newBad'] = 'No'
    refData.loc[refData['runID'].isin(resData), 'newBad'] = 'Yes'

    # summarize agreement of each type of errors
    table = PrettyTable()
    table.field_names = ['Error type', 'Manual', 'Program result', 'Official result']
    for errType, _ in groupClassification + [['Other errors', None]]:
        selectedData = refData[refData[errType] == 'Yes']
        NOManual = selectedData.shape[0]
        NONewResult = selectedData[selectedData['newBad'] == 'Yes'].shape[0]
        NOOfficial = selectedData[selectedData['OfficialBad'] == 'Yes'].shape[0]
        table.add_row([errType, NOManual, '%d (%.1f%%)' % (NONewResult, 100*float(NONewResult)/NOManual), '%d (%.1f%%)' % (NOOfficial, 100*float(NOOfficial)/NOManual)])

    print(table)
        
    # print good run statistics
    table = PrettyTable()
    table.field_names = ['', 'Manual', 'Program result', 'Official result']
    selectedData = refData[refData['Good run'] == 'Yes']
    NOManual = selectedData.shape[0]
    NONewResult = selectedData[selectedData['newBad'] == 'No'].shape[0]
    NOOfficial = selectedData[selectedData['OfficialBad'] == 'No'].shape[0]
    table.add_row(['Good runs', NOManual, '%d (%.1f%%)' % (NONewResult, 100*float(NONewResult)/NOManual), '%d (%.1f%%)' % (NOOfficial, 100*float(NOOfficial)/NOManual)])

    print(table)
    if txt is not None:
        resFullData.rename(columns={'reason': 'AI response'}, inplace=True)
        refData = pd.merge(refData, resFullData, on='runID', how='outer')
        refData.to_csv(txt)
 

if __name__ == '__main__':
    main('../newBadrun_default.list', 'manualResult.txt')
