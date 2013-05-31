
"""
See http://stackoverflow.com/questions/2879856/get-system-language-in-iso-639-3-letter-codes-in-python
"""

import os
import codecs

def getisocodes_dict(data_path):
    # Provide a map from ISO code (both bibliographic and terminologic)
    # in ISO 639-2 to a dict with the two letter ISO 639-2 codes (alpha2)
    # English and french names
    #
    # "bibliographic" iso codes are derived from English word for the language
    # "terminologic" iso codes are derived from the pronunciation in the target 
    # language (if different to the bibliographic code)

    map = {}
    fp = codecs.open(os.path.join(os.path.dirname(__file__), data_path), 'rb', 'utf-8')
    for line in fp:
        fields = line.split('|')
        if len(fields[2]) > 0:
            map[fields[2]] = fields[0]
    fp.close()
    return map

ISO_UTF_MAP =  getisocodes_dict('ISO-639-2_utf-8.txt')

