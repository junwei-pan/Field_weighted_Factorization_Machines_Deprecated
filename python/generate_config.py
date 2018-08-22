import configparser

# CTR Yahoo
config = configparser.ConfigParser()
config['setup'] = {'path_train': '',
                   'path_validation': '',
                   'path_test': '',
                   'path_feature_index': '',
                   'num_field': 15
                   }

with open('conf/project/ctr.ini', 'w') as configfile:
    config.write(configfile)

