import os
from bs4 import BeautifulSoup
import requests
import pandas as pd
from pyspark.ml import Pipeline
from sklearn.naive_bayes import MultinomialNB
from pyspark.ml.classification import NaiveBayes
from sklearn.model_selection import cross_val_score
import numpy as np
#from sklearn.feature_extraction.text import CountVectorizer
from pyspark.ml.feature import CountVectorizer
import io
from sklearn.cross_validation import KFold
from sklearn.metrics import f1_score, confusion_matrix
import sys
from pyspark import SparkContext, SparkConf
from pyspark.sql import SparkSession



new_line = '\n'

conf = SparkConf().setAppName("test").setMaster("local")
spark = SparkSession.builder.master("local").appName("Word Count").config("spark.some.config.option", "some-value").getOrCreate()
#sc = SparkContext(conf=conf)
sc = spark.sparkContext


def read_email_files(path):
    email_files = []
    for root, dirnames, filenames in os.walk(path):
        email_files.extend([os.path.join(root, f) for f in filenames])
    
    for email_file in email_files:
        #with io.open(email_file, encoding="latin-1") as f:
        email = sc.textFile(email_file)
        email_index = email.zipWithIndex()
        body_start = email_index.filter(lambda kv: kv[0] == u'').first()[1]
        body = email_index.filter(lambda kv: kv[1] > body_start).map(lambda kv: kv[0])
        yield email_file, body

def download_unzip(email_type, urls):
    if not os.path.exists(email_type):
        os.mkdir(email_type)
    cwd = os.getcwd()
    os.chdir(email_type)
    for url in urls:
        fname = url[url.rfind('/') + 1:]
        dirname = fname[:fname.find('.')]
        if os.path.exists(dirname):
            continue
        os.system('wget %s' % url)
        os.system('tar -xzvf %s && rm %s' % (fname, fname))
    os.chdir(cwd)

def read_enron_email_files():
    """
    url = 'http://www.aueb.gr/users/ion/data/enron-spam/'
    req = requests.get(url)
    soup = BeautifulSoup(req.content, 'html.parser')
    li_tags = soup.find_all('li')
    ham = filter(lambda s : s.strings.next().startswith('ham'), li_tags)[0]
    spam = filter(lambda s : s.strings.next().startswith('spam'), li_tags)[0]
    ham_urls = [t.a.attrs['href'] for t in ham.find_all('li')]
    spam_urls = [t.a.attrs['href'] for t in spam.find_all('li')]
    download_unzip('ham', ham_urls)
    download_unzip('spam', spam_urls)
    """
    index = []
    ham_emails = []
    for fname, body in read_email_files('ham'):
        index.append(fname)
        ham_emails.append(body)

   
    index = []
    spam_emails = []
    for fname, body in read_email_files('spam'):
        index.append(fname)
        spam_emails.append(body)

    all_emails = []
    all_emails.extend(zip(ham_emails, [False] * len(ham_emails)))
    all_emails.extend(zip(spam_emails, [True] * len(spam_emails)))
    all_emails_rdd = sc.parallelize(all_emails)
    #print(np.random.permutation(all_emails).tolist())
    #df = spark.createDataFrame(np.random.permutation(all_emails).tolist(), ['body', 'spam'])
    df = spark.createDataFrame(all_emails_rdd)

    #ham = pd.DataFrame({'body':emails, 'spam': False})
    #ham.index = index
    #spam = spark.createDataFrame(zip(emails, [True] * len(emails)), ['body', 'spam'])
    #spam = pd.DataFrame({'body':emails, 'spam': True})
    #spam.index = index


    #pd.options.display.expand_frame_repr = False
    #df = pd.concat([ham, spam])
    #return df.reindex(np.random.permutation(df.index))
    return df

def scorer(est, X, y):
     y_pred = est.predict(X)
     #ret = np.mean(y != y_pred), f1_score(y_true=y, y_pred=y_pred)
     #print(ret)
     return np.mean(y == y_pred)

if __name__ == '__main__':
    if not os.path.isfile('emails_df'):
        print('Reading emails...')
        df = read_enron_email_files()
        df.to_pickle('emails_df')
        print('Finished reading emails.')
    else:
        print('Loading emails...')
        df = pd.read_pickle('emails_df')
        print('Finished loading emails.')

    cv = CountVectorizer()
    nb = NaiveBayes()
    #pipeline = Pipeline([('cv', cv), ('nb', nb)])
    pipeline = Pipeline(stages = [cv, nb])

    #pl.fit(df.body.values[:1000], df.spam.values[:1000].astype(int))
    #X = df.select('body')
    #y = df.select('spam')

    pipeline.fit(df)
    #print(cross_val_score(pipeline, X, y, scoring=scorer))
    #print cross_val_score(pipeline, X.values[:1000], y.values[:1000], scoring=scorer)
