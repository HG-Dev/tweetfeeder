''' Compile-time configuration data for hg_tweetfeeder.bot '''

import json

class LoadFromFile:
    ''' Collection of static methods for getting stuff out of files. '''
    @staticmethod
    def get_json_dict(filepath):
        ''' Returns the entire JSON dict in a given file. '''
        with open(filepath, encoding="utf8") as infile:
            return json.load(infile)
