import csv
import json
import math
import os
import string
import numpy as np
from collections import OrderedDict 
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory


def test_append(text):
    result = " ".join(('hello', text, ", my name is ibnu"))
    
    return result


def preprocess(abstract):

    with open('./data/stop-words.json') as f:
        stop_words = json.load(f)

    stemmer_factory = StemmerFactory()
    stemmer = stemmer_factory.create_stemmer()

    remove_digits = str.maketrans(string.digits, ' '*len(string.digits))
    remove_punctuations = str.maketrans(string.punctuation, ' '*len(string.punctuation))

    abstract_lower_case = abstract.lower()
    abstract_white_spaces_removed = abstract_lower_case.strip()
    abstract_numbers_removed =  abstract_white_spaces_removed.translate(remove_digits)
    abstract_punctuation_removed = abstract_numbers_removed.translate(remove_punctuations)
    abstract_punctuation_removed_list = abstract_punctuation_removed.split()
    abstract_sw_removed_list = [word for word in abstract_punctuation_removed_list if word not in stop_words]
    abstract_sw_removed = " ".join(abstract_sw_removed_list)    
    abstract_stemmed = stemmer.stem(abstract_sw_removed)
    abstract_tokens = abstract_stemmed.split()

    tokens_digits_removed = []

    for token in abstract_tokens:
        token_digits_removed = ''.join([i for i in token if not i.isdigit()])
        tokens_digits_removed.append(token_digits_removed)
    
    final_token = []

    for token in tokens_digits_removed:
        if token not in final_token:
            final_token.append(token)

    return final_token


def calculate_tf(word_dict, token_list):
    tf_dict = {}
    token_list_length = len(token_list)

    for word, value in word_dict.items():
        word_count = token_list.count(word)
        tf = word_count / token_list_length
        tf_dict[word] = tf 
    
    return tf_dict


def calculate_tf_idf(tf):
    tf_idf_dict = {}

    for word, val in tf.items():
        if val == 0:
            tf_idf = val
        else:
            tf_idf = val * math.log10(1/2)

        tf_idf_dict[word] = tf_idf
            
    return tf_idf_dict


def predict(abstract, model, model_version):

    ABSTRACT_TOKEN_SAVE_DIR = os.environ.get('ABSTRACT_TOKEN_SAVE_DIR', None) 
    TF_IDF_SAVE_DIR = os.environ.get('TF_IDF_SAVE_DIR', None) 
    FV_TOKENS_OPEN_DIR = os.environ.get('FV_TOKENS_OPEN_DIR', None) 
    JOURNAL_DATA_OPEN_DIR = os.environ.get('JOURNAL_DATA_OPEN_DIR', None) 

    abstract_token_list = preprocess(abstract)

    with open(ABSTRACT_TOKEN_SAVE_DIR, 'w+') as f:
        json.dump(abstract_token_list , f, indent=4)

    if model_version == 'final':
        FV_TOKENS_OPEN_DIR += '/final-fv-tokens-data-23.json'
    elif model_version == 'similar':
        FV_TOKENS_OPEN_DIR += '/fv-tokens-3-journals-similar.json'
    else:
        FV_TOKENS_OPEN_DIR += '/fv-tokens-3-journals-mixed.json'


    with open(FV_TOKENS_OPEN_DIR) as f:
        fv_token_list = json.load(f)
    
    fv_token_dict = OrderedDict({ i : 0 for i in fv_token_list})
    tfs = calculate_tf(fv_token_dict, abstract_token_list)
    tfidfs = calculate_tf_idf(tfs)

    tf_idf_list = []

    for tfidf in tfidfs.values():
        tf_idf_list.append(tfidf) 

    with open(TF_IDF_SAVE_DIR, 'w+') as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_NONE)
        wr.writerow(tf_idf_list)

    tf_idf_list_np = np.array([tf_idf_list])

    probabilities = model.predict_proba(tf_idf_list_np)
    print("probabilities: ", probabilities)

    predict = model.predict(tf_idf_list_np)
    print("predict: ", predict)

    if model_version == 'final':
        JOURNAL_DATA_OPEN_DIR += '/final-journal-info.json'
    elif model_version == 'similar':
        JOURNAL_DATA_OPEN_DIR += '/similar-journal-info.json'
    else:
        JOURNAL_DATA_OPEN_DIR += '/mixed-journal-info.json'

    with open(JOURNAL_DATA_OPEN_DIR) as f:
        journal_datas = json.load(f)

    journal_data = journal_datas[str(predict[0])]
    probabilities_data = []
    index = 0

    for probability in probabilities[0]:
        temp_dict = {
            'JOURNAL_ID': index,
            'JOURNAL_NAME': journal_datas[str(index)]['JOURNAL_NAME'],
            'JOURNAL_PROBABILITY': round(probability * 100, 2),
        }

        probabilities_data.append(temp_dict)
        index += 1

    return journal_data, probabilities_data