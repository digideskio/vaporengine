#!/usr/bin/env python

import argparse
import codecs

from lib.database import init_dbconn
from settings import settings
from vaporgasp.queries import find_pseudoterms

parser = argparse.ArgumentParser()
parser.add_argument("backup_file")
args = parser.parse_args()

db = init_dbconn(name=settings['DB_NAME'], host=settings['DB_HOST'])

backup_file = codecs.open(args.backup_file, "w", encoding="utf-8")

for pseudoterm in find_pseudoterms(db, annotated=True):
    print pseudoterm
    backup_file.write("%s\t%s\n" % (pseudoterm['native_display'], pseudoterm['eng_display']))

backup_file.close()
