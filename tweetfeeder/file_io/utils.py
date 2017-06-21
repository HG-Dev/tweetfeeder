''' Compile-time configuration data for hg_tweetfeeder.bot '''

import json

class FileIO:
    ''' Collection of static methods for getting stuff out of files. '''
    @staticmethod
    def get_json_dict(filepath):
        ''' Returns the entire JSON dict in a given file. '''
        with open(filepath, encoding="utf8") as infile:
            return json.load(infile)

    @staticmethod
    def save_json_dict(filepath, dictionary):
        ''' Saves a JSON dict, overwriting or creating a given file. '''
        with open(filepath, 'w', encoding="utf8") as outfile:
            json.dump(dictionary, outfile, ensure_ascii=False, indent=4)
