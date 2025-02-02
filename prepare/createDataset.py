'''
This script loads the raw data, clean them and prepare for training. 

It convertes each amino acid sequence into a list of idexes. 
The indexes indicate the amino acid. such as [ARNDCA] -> [0,1,2,3,4,0] 

Same, it converts the go notations into a list of indexes. 
[GO1, GO2, GO3] -> [0,1,2] 

Then, it discards the examples that don't meet the criteria (max sequence length, Go notation)

Finally, it creates train and test datasets in tfrecord format.
'''
import numpy as np
import pickle
import sys
from absl import flags
import yaml
from sklearn.model_selection import train_test_split

import prepare.tfapiConverter as tfconv

FLAGS = flags.FLAGS
file_batch_size=200000

#save processed data on disk
def prepareDataset(inputData, labelData, filename):
    print('Saving', filename)

    X_train, X_test, y_train, y_test = train_test_split(inputData, labelData, test_size=0.2, random_state=0)

    tfconv.generateTFRecord(X_train, y_train, 'prepare/data/train/'+filename+'.tfrecords')
    tfconv.generateTFRecord(X_test, y_test, 'prepare/data/test/'+filename+'.tfrecords')

def applyMask(dirtyData, dirty_idxs):
    if (type(dirtyData)!=type(np.asarray([]))):
        dirtyData=np.asarray(dirtyData)

    returnData= dirtyData[np.logical_not(dirty_idxs)]

    return returnData

def preprocessLabels(goes_seqs, unique_goes, mapped_goes):
    '''
    This function index the go notations for each sequence

    Args:
        goes_seques (list): each element is a list of go notations for a protein
        unique_goes (list): list of unique goes
        mapped_goes (dictionary): a dictionary where the key is a go subterm and the value is a list of 
                                  labels. The labels are the parents GOs of the key GO
    
    Return:
        hot_cats_seqs (list): each element is a list of indexed go notations
        mask (list): list of bools, if True the example must be discarded
    '''
    #get GO's category and retrieve category hot encode
    hot_cats_seqs=[]
    mask=[]
    for i, goes_list in enumerate(goes_seqs):
        hot_cat_seq=[]
        for go in goes_list:
            if go in unique_goes:
                hot_cat_seq.append(unique_goes.index(go))
            elif go in mapped_goes:
                #the go is a subterm, retrieve the labels
                labels=mapped_goes[go]
                for label in labels:
                    hot_cat_seq.append(unique_goes.index(label))
            else:
                #go not identified, discard it
                print('go not available in the GO ontology')

        if hot_cat_seq==[]:
            mask.append(True)
        else:
            mask.append(False)

        hot_cats_seqs.append(hot_cat_seq)

    #return [goes_idxs_lists], [bools]
    return hot_cats_seqs, mask

def preprocessInpuData(seqs_str, unique_aminos): 
    '''
    This function index the amino acids for each sequence
    Args:
        seqs_str(list): each element is a string of amino acids
        unique_aminos(list): list of unique ami42no acids

    Return:
        hot_aminos_seqs (list): each element is a list of indexed amino acids
        mask (list): list of bools, if True the example must be discarded
    ''' 

    hot_aminos_seqs=[]
    mask=[]
    for i, seq_str in enumerate(seqs_str):
        hot_amino_seq=[]
        #discard sequences shorter and longer than given thresholds
        l_seq=len(seq_str)
        if ((l_seq>=FLAGS.min_length_aminos) and (l_seq<=FLAGS.max_length_aminos)):
            enumerator=enumerate(seq_str)
            mask.append(False)
        else:
            enumerator=enumerate(seq_str[:FLAGS.max_length_aminos])
            mask.append(True)

        for j, amino in enumerator:
            idx=unique_aminos.index(amino)
            hot_amino_seq.append(idx)

        hot_aminos_seqs.append(hot_amino_seq)

    #assign hot_amino to each seq's amino
    return hot_aminos_seqs, mask

def createDataset():
    print('Importing files..')
    with open("extract/proteins_goes", "rb") as fp:
        proteins_goes=pickle.load(fp)

    with open("extract/proteins_seqs", "rb") as fp:
        proteins_seqs=pickle.load(fp)

    with open("hyperparams.yaml", 'r') as stream:
        hyperparams = yaml.safe_load(stream)

    #get unique goes as list
    unique_goes=hyperparams['available_gos']

    #get mapped gos subterms as dictionary subterm: [labels]
    mapped_goes=hyperparams['mapped_gos']

    #get the unique aminos
    unique_aminos=hyperparams['unique_aminos']

    tot_examples=0
    print('Creating dataset..')
    for startBatch in range(0, len(proteins_goes), file_batch_size):
        endBatch=startBatch+file_batch_size

        batch_proteins_goes=proteins_goes[startBatch:endBatch]
        batch_proteins_seqs=proteins_seqs[startBatch:endBatch]

        #Labels: return [seqs, hot_vec]
        print('Preprocessing labels..')
        dirty_labelData, mask_empty_examples=preprocessLabels(batch_proteins_goes, unique_goes, mapped_goes)

        #Inputs: return [seqs, num_aminos, hot_vec]
        print('Preprocessing input data..')
        dirty_inputData, mask_too_long_examples=preprocessInpuData(batch_proteins_seqs, unique_aminos)

        #merge the two masks (or operator)
        dirty_idxs=np.logical_or(mask_empty_examples,mask_too_long_examples)

        #remove dirty examples
        print('Removing dirty examples..')
        batch_inputData=applyMask(dirty_inputData, dirty_idxs)
        batch_labelData=applyMask(dirty_labelData, dirty_idxs)
        print('Ready input data:', batch_inputData.shape, 'values type', batch_inputData.dtype, 'size:', sys.getsizeof(batch_inputData)*1e-6,'MB')
        print('Ready label data:', batch_labelData.shape, 'values type', batch_labelData.dtype, 'size:', sys.getsizeof(batch_labelData)*1e-6,'MB')

        tot_examples+=batch_inputData.shape[0]

        filename='dataset-'+str(startBatch//file_batch_size)
        prepareDataset(batch_inputData, batch_labelData, filename)

    print('Total number of examples', tot_examples)
    hyperparams['examples']=tot_examples

    with open('hyperparams.yaml', 'w') as outfile:
        yaml.dump(hyperparams, outfile)