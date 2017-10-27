import sys
import pickle as pkl
import numpy as np
import scipy
import math
from scipy.stats.stats import pearsonr
from scipy.stats import kendalltau

class statis:
    def __init__(self):
        self.M = 15 # Number of fields.
        self.k = 10 # Dimension of embedding vector.
        self.d = {}
        self.d_idx2embedding = {}
        self.d_idx2idxField = {}
        self.lst_fea = []
        self.lst_label = []
        self.d_indexField_feature = {} # key: fi, value: {feature: frequency}
        self.d_fieldPair_featurePair = {} # key: fi_fj, value: {fea_i_fea_j: frequency}
        self.cnt_sample = 0.0
        self.cnt_pos = 0.0
        self.cnt_neg = 0.0
        self.d_fieldPair_r = {}

    def load_model(self, path_model, model = 'fwfm'):
        self.d = pkl.load(open(path_model, 'rb'))
        self.idx2key = {}
        idx_last_field = 0
        name_last_field = '0'
        total_idx = 0
        if model == 'fwfm':
            for i in range(self.M):
                d_field_i = self.d['w0_' + str(i)]
                for j in range(len(d_field_i)):
                    self.d_idx2embedding[total_idx] = d_field_i[j]
                    total_idx += 1
            idx = 0
            for i in range(self.M):
                for j in range(i+1, self.M):
                    field_pair = str(i) + '_' + str(j)
                    self.d_fieldPair_r[field_pair] = self.d['w_p'][idx][0]
                    idx += 1
        elif model == 'ffm':
            for i in range(self.M):
                d_field_i = self.d['w0_' + str(i)]
                for j in range(len(d_field_i)):
                    self.d_idx2embedding[total_idx] = []
                    for l in range(self.M):
                        self.d_idx2embedding[total_idx].append(d_field_i[j][self.k * l : self.k * (l + 1)])
                    total_idx += 1
            print self.d_idx2embedding.keys()
        elif model == 'fm':
            for i in range(len(self.d['v'])):
                self.d_idx2embedding[i] = self.d['v'][i]
            
    def load_feature_index(self, path):
        for line in open(path):
            lst = line.strip('\n').split('\t')
            idx_field = int(lst[0].split(':')[0])
            idx = int(lst[1])
            self.d_idx2idxField[idx] = idx_field

    def load_data(self, path):
        bin = 100000
        for idx_line, line in enumerate(open(path)):
            self.cnt_sample += 1
            if idx_line % bin == bin - 1:
                print idx_line
                sys.stdout.flush()
            lst = line.strip('\n').split(' ')
            label = int(lst[0])
            if label == 1:
                self.cnt_pos += 1
            else:
                self.cnt_neg += 1
            lst_fea = [int(x.split(':')[0]) for x in lst[1:]]
            for i in range(len(lst_fea)):
                fea = lst_fea[i]
                self.d_indexField_feature.setdefault(i, {})
                self.d_indexField_feature[i].setdefault(fea, 0)
                self.d_indexField_feature[i][fea] += 1
                for j in range(i+1, len(lst_fea)):
                    fea_j = lst_fea[j]
                    field_pair = str(i) + '_' + str(j)
                    feature_pair = str(fea) + '_' + str(fea_j)
                    self.d_fieldPair_featurePair.setdefault(field_pair, {})
                    self.d_fieldPair_featurePair[field_pair].setdefault(feature_pair, {'cnt':0.01, 'pos':0.01, 'neg':0.01})
                    self.d_fieldPair_featurePair[field_pair][feature_pair]['cnt'] += 1
                    if label == 1:
                        self.d_fieldPair_featurePair[field_pair][feature_pair]['pos'] += 1

                    else:
                        self.d_fieldPair_featurePair[field_pair][feature_pair]['neg'] += 1
            self.lst_fea.append(lst_fea)
            self.lst_label.append(label)

    def get_feature_dot_product(self, i, j, fi, fj, model = 'fm'):
        if model == 'ffm':
            return np.dot(self.d_idx2embedding[i][fj], self.d_idx2embedding[j][fi])
        else:
            return np.dot(self.d_idx2embedding[i], self.d_idx2embedding[j])

    def get_field_corr(self, fi, fj):
        '''
        This will get a list, whose value is <v_i, v_j>, where i, j belongs to fi and fj respectively.
        '''
        res = []
        for lst_fea in self.lst_fea:
            i = lst_fea[fi]
            j = lst_fea[fj]
            res.append(self.get_feature_dot_product(i, j, fi, fj, model))
        return res

    def get_field_pair_pearson_corr_with_label(self, fi, fj):
        lst_score = self.get_field_corr(fi, fj)
        return pearsonr(lst_score, self.lst_label)
            
    def get_embedding(self, idx):
        '''
        Return the embedding vector for a feature with index idx
        '''
        pass

    def average_latent_vector_dot_product_for_field_pair(self, fi, fj, model ='fwfm'):
        sum = 0.0
        sum_abs = 0.0
        sum_cnt = 0.0
        uniq_fea_pair_cnt = 0.0
        field_pair = str(fi) + '_' + str(fj)
        for feature_pair in self.d_fieldPair_featurePair[field_pair]:
            cnt = self.d_fieldPair_featurePair[field_pair][feature_pair]['cnt']
            r = 1
            if model == 'fwfm':
                r = self.d_fieldPair_r[field_pair]
            fea_i, fea_j = map(int, feature_pair.split('_'))
            dot = self.get_feature_dot_product(fea_i, fea_j, fi, fj, model)
            sum += dot * cnt * r
            sum_abs += abs(dot * r) * cnt 
            sum_cnt += cnt
            uniq_fea_pair_cnt += 1
        return sum, sum_abs, sum_cnt, uniq_fea_pair_cnt
            
    def mutual_information(self, fi, fj):
        mi = 0.0
        field_pair = str(fi) + '_' + str(fj)
        for feature_pair in self.d_fieldPair_featurePair[field_pair]:
            p_fi_fj = self.d_fieldPair_featurePair[field_pair][feature_pair]['cnt'] / self.cnt_sample
            p_fi_fi_pos = self.d_fieldPair_featurePair[field_pair][feature_pair]['pos'] / self.cnt_sample
            p_fi_fi_neg = self.d_fieldPair_featurePair[field_pair][feature_pair]['neg'] / self.cnt_sample
            p_pos = self.cnt_pos / self.cnt_sample
            p_neg = self.cnt_neg / self.cnt_sample
            mi += p_fi_fi_pos * math.log(p_fi_fi_pos / (p_fi_fj * p_pos))
            mi += p_fi_fi_neg * math.log(p_fi_fi_neg / (p_fi_fj * p_neg))
        return mi
        
def load_list(path):
    lst = []
    for line in open(path):
        lst.append(float(line.strip('\n')))
    return lst

def main_field_interaction():

    statis = statis()
    #print 'load feature index'
    #sys.stdout.flush()
    #statis.load_feature_index('../data_yahoo/dataset2/featindex_25m_thres10.txt')
    print 'load data'
    sys.stdout.flush()
    #statis.load_data('../data_yahoo/dataset2/ctr_20170517_0530_0.015.txt.thres10.yx')
    statis.load_data('../data_yahoo/dataset2/ctr_20170517_0530_0.015.txt.thres10.yx.downsample_all.0.05')
    print 'load model'
    sys.stdout.flush()
    #statis.load_model('/homes/jwpan/Github/product-nets/python/model/fm_epoch_1', 'fm')
    #statis.load_model('model/yahoo_dataset2.2_fwfm_epoch_2', 'fwfm')
    statis.load_model('model/ffm_l2_v_1e-7_lr_1e-4_yahoo_epoch_2', 'ffm')
    for fi in range(15):
        for fj in range(fi+1, 15):
            res = statis.average_latent_vector_dot_product_for_field_pair(fi, fj, 'ffm')
            print "%f\t%f\t%f\t%f" % (res[0], res[1], res[2], res[3])
            sys.stdout.flush()
            #res = statis.mutual_information(fi, fj)
            #print res
            #res = statis.get_field_pair_pearson_corr_with_label(i,j)
            #print '%d\t%d\t%f\t%f' % (i, j, res[0], res[1])

def main_kendalltau():
    path_mi = 'data/yahoo_mi'
    path_fm = 'data/yahoo_fm'
    path_ffm = 'data/yahoo_ffm'
    path_fwfm = 'data/yahoo_fwfm'
    x_mi = load_list(path_mi)
    x_fm = load_list(path_fm)
    x_ffm = load_list(path_ffm)
    x_fwfm = load_list(path_fwfm)
    print 'mi v.s fm'
    print kendalltau(x_mi, x_fm)
    print 'mi v.s ffm'
    print kendalltau(x_mi, x_ffm)
    print 'mi v.s fwfm'
    print kendalltau(x_mi, x_fwfm)

main_kendalltau()
