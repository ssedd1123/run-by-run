# run-by-run
New run-by-run QA program. Confirmed to work on linux and Windows 10 (with miniconda)

If you are using linux, you need to install enter the following command to install all required packages.

$> pip3 install --user matplotlib ruptures pandas numpy scipy pyfiglet uproot scikit-learn

If you know how to use virtualenv/anaconda/miniconda, you are welcome to use a virtual environment 

After that, simply type 

$> python3 QA.py -h

To read the instructions.

An example ROOT file and QA_variable.list is provided in this repository. You can run them with,

$>python3 QA.py -i qahist.root -v QA_variable.list -e Au+Au -s 9.8 -o badrun.list

It will generate the text file badrun.list which contains the final result.
